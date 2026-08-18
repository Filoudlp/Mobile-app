#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Charge de neige caractéristique au sol (sk) — France et Suisse.

Vérification unitaire indépendante (même principe que ``norme.EC3.elu.*``) :
chaque classe ne dépend que des grandeurs qui lui sont propres (zone/altitude
ou h/h0), pas d'un objet "site" composite.

France — NF EN 1991-1-3/NA (mai 2007), Annexe nationale :
    sk(zone, altitude) = sk0(zone) + Δs(zone, altitude)  pour altitude > 200 m
    Zones : A1, A2, B1, B2, C1, C2, D, E.
    sAd (charge exceptionnelle) donnée directement par zone, indépendante de
    l'altitude.

Suisse — SIA 261:2020, §5.2.2, éq. (10) :
    sk = [1 + (h/h0)²] − 0,4 kN/m² ,  sk ≥ 0,9 kN/m²
    h  : altitude du site [m]
    h0 : altitude de référence lue sur la carte SIA 261, Annexe D [m]

    ⚠ Cette formule a été relue depuis un PDF dont l'équation (10) est une
    image (OCR indisponible) — à confirmer contre le document source avant
    tout usage en production. Isolée ici pour être corrigée en un seul
    endroit si besoin.
"""

__all__ = ['GroundSnowLoadFR', 'GroundSnowLoadCH']

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.formula import FormulaResult, FormulaCollection

_RESSOURCE_DIR = Path(__file__).resolve().parents[3] / "ressource"

# ---------------------------------------------------------------------------
# France — Tableau des zones (NF EN 1991-1-3/NA, Annexe, page 9)
# ---------------------------------------------------------------------------

FR_ZONES: Dict[str, Dict[str, float]] = {
    #        sk0 [kN/m²] (altitude ≤ 200 m)   sAd [kN/m²] (None = non défini)
    "A1": {"sk0": 0.45, "sAd": None},
    "A2": {"sk0": 0.45, "sAd": 1.00},
    "B1": {"sk0": 0.55, "sAd": 1.00},
    "B2": {"sk0": 0.55, "sAd": 1.35},
    "C1": {"sk0": 0.65, "sAd": None},
    "C2": {"sk0": 0.65, "sAd": 1.35},
    "D":  {"sk0": 0.90, "sAd": 1.80},
    "E":  {"sk0": 1.40, "sAd": None},
}

# Zones utilisant la loi de variation Δs1 vs Δs2 (Annexe, page 9)
FR_ZONES_DS1 = {"A1", "A2", "B1", "B2", "C1", "C2"}
FR_ZONES_DS2 = {"D", "E"}


def _delta_s1(A: float) -> float:
    """Δs1(A) [kN/m²] — zones A1, A2, B1, B2, C1, C2. A en mètres."""
    if A <= 200:
        return 0.0
    if A <= 500:
        return A / 1000 - 0.20
    if A <= 1000:
        return 1.5 * A / 1000 - 0.45
    if A <= 2000:
        return 3.5 * A / 1000 - 2.45
    raise ValueError("NF EN 1991-1-3/NA applicable jusqu'à 2000 m d'altitude.")


def _delta_s2(A: float) -> float:
    """Δs2(A) [kN/m²] — zones D, E. A en mètres."""
    if A <= 200:
        return 0.0
    if A <= 500:
        return 1.5 * A / 1000 - 0.30
    if A <= 1000:
        return 3.5 * A / 1000 - 1.30
    if A <= 2000:
        return 7 * A / 1000 - 4.80
    raise ValueError("NF EN 1991-1-3/NA applicable jusqu'à 2000 m d'altitude.")


_ZONES_JSON_CACHE: Optional[dict] = None


def load_fr_zone_table() -> dict:
    """Charge ressource/neige_zones_fr.json (table des départements)."""
    global _ZONES_JSON_CACHE
    if _ZONES_JSON_CACHE is None:
        with open(_RESSOURCE_DIR / "neige_zones_fr.json", "r", encoding="utf-8") as f:
            _ZONES_JSON_CACHE = json.load(f)
    return _ZONES_JSON_CACHE


def zones_for_department(code: str) -> List[str]:
    """Liste des zones possibles pour un département (ex. '01' -> ['A2','C2'])."""
    data = load_fr_zone_table()
    dept = data["departements"].get(code.upper().zfill(2) if code.isdigit() else code.upper())
    if dept is None:
        raise ValueError(f"Département '{code}' inconnu.")
    return dept["zones"]


class GroundSnowLoadFR:
    """
    Charge de neige caractéristique au sol — France (NF EN 1991-1-3/NA).

    :param zone: Zone de neige ('A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'D', 'E').
    :param altitude: Altitude du site [m] (≤ 2000 m).
    """

    def __init__(self, zone: str, altitude: float) -> None:
        zone = zone.upper().strip()
        if zone not in FR_ZONES:
            raise ValueError(
                f"Zone '{zone}' inconnue. Zones valides : {sorted(FR_ZONES.keys())}"
            )
        if altitude < 0 or altitude > 2000:
            raise ValueError(
                f"Altitude {altitude} m hors du domaine d'application "
                f"(0 - 2000 m — NF EN 1991-1-3/NA)."
            )
        self.__zone = zone
        self.__altitude = altitude

    @property
    def zone(self) -> str:
        return self.__zone

    @property
    def altitude(self) -> float:
        return self.__altitude

    @property
    def sk0(self) -> float:
        """Valeur caractéristique à altitude ≤ 200 m [kN/m²]."""
        return FR_ZONES[self.__zone]["sk0"]

    @property
    def delta_s(self) -> float:
        """Supplément d'altitude Δs [kN/m²]."""
        if self.__zone in FR_ZONES_DS1:
            return _delta_s1(self.__altitude)
        return _delta_s2(self.__altitude)

    @property
    def sk(self) -> float:
        """Charge caractéristique de neige au sol sk [kN/m²]."""
        return round(self.sk0 + self.delta_s, 4)

    @property
    def sAd(self) -> Optional[float]:
        """Charge exceptionnelle de calcul sAd [kN/m²] (None si non définie
        pour cette zone — pas de condition exceptionnelle à considérer)."""
        return FR_ZONES[self.__zone]["sAd"]

    def get_sk(self, with_values: bool = False) -> FormulaResult:
        fv = ""
        if with_values:
            law = "Δs1" if self.__zone in FR_ZONES_DS1 else "Δs2"
            fv = (
                f"sk = sk0({self.__zone}) + {law}({self.__altitude:.0f} m) "
                f"= {self.sk0:.2f} + {self.delta_s:.4f} = {self.sk:.4f} kN/m²"
            )
        return FormulaResult(
            name="sk",
            formula="sk = sk0(zone) + Δs(zone, altitude)",
            formula_values=fv,
            result=self.sk,
            unit="kN/m²",
            ref="NF EN 1991-1-3/NA — Annexe",
        )

    def get_sAd(self, with_values: bool = False) -> FormulaResult:
        r = self.sAd if self.sAd is not None else 0.0
        fv = ""
        if with_values:
            fv = (
                f"sAd = {r:.2f} kN/m² (valeur directe, zone {self.__zone})"
                if self.sAd is not None
                else f"Non définie pour la zone {self.__zone} — pas de condition exceptionnelle"
            )
        return FormulaResult(
            name="sAd",
            formula="sAd — valeur directe par zone (indépendante de l'altitude)",
            formula_values=fv,
            result=r,
            unit="kN/m²",
            ref="NF EN 1991-1-3/NA — Annexe",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Charge de neige au sol — France, zone {self.__zone}",
            ref="NF EN 1991-1-3/NA",
        )
        fc.add(self.get_sk(with_values=with_values))
        fc.add(self.get_sAd(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"GroundSnowLoadFR(zone='{self.__zone}', altitude={self.__altitude:.0f}m, "
            f"sk={self.sk:.2f}kN/m²)"
        )


# ---------------------------------------------------------------------------
# Suisse — SIA 261:2020, §5.2.2
# ---------------------------------------------------------------------------

class GroundSnowLoadCH:
    """
    Charge de neige caractéristique au sol — Suisse (SIA 261:2020, §5.2.2).

    :param h: Altitude du site [m] (≤ 2000 m).
    :param h0: Altitude de référence [m], lue sur la carte SIA 261 — Annexe D
        (isolignes ; pas de table par commune — voir docstring du module).

    ⚠ Formule (10) relue depuis un PDF non-OCRisable — à confirmer.
    """

    #: Charge minimale absolue — SIA 261 §5.2.2, éq. (10).
    SK_MIN = 0.9

    def __init__(self, h: float, h0: float) -> None:
        if h < 0 or h > 2000:
            raise ValueError(
                f"Altitude {h} m hors du domaine d'application usuel de la "
                f"SIA 261 (0 - 2000 m ; au-delà, étude spécifique requise)."
            )
        if h0 <= 0:
            raise ValueError("h0 (altitude de référence, Annexe D) doit être > 0.")
        self.__h = h
        self.__h0 = h0

    @property
    def h(self) -> float:
        return self.__h

    @property
    def h0(self) -> float:
        return self.__h0

    @property
    def sk(self) -> float:
        """sk = [1 + (h/h0)²] − 0,4 kN/m² , borné à sk ≥ 0,9 kN/m²."""
        raw = (1.0 + (self.__h / self.__h0) ** 2) - 0.4
        return round(max(raw, self.SK_MIN), 4)

    def get_sk(self, with_values: bool = False) -> FormulaResult:
        fv = ""
        if with_values:
            raw = (1.0 + (self.__h / self.__h0) ** 2) - 0.4
            fv = (
                f"sk = [1 + ({self.__h:.0f}/{self.__h0:.0f})²] − 0,4 "
                f"= {raw:.4f} kN/m² → sk = max({raw:.4f} ; {self.SK_MIN}) "
                f"= {self.sk:.4f} kN/m²"
            )
        return FormulaResult(
            name="sk",
            formula="sk = [1 + (h/h0)²] − 0,4 kN/m² , sk ≥ 0,9 kN/m²",
            formula_values=fv,
            result=self.sk,
            unit="kN/m²",
            ref="SIA 261:2020 — §5.2.2, éq. (10) [à confirmer]",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Charge de neige au sol — Suisse (SIA 261)",
            ref="SIA 261:2020 — §5.2.2",
        )
        fc.add(self.get_sk(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return f"GroundSnowLoadCH(h={self.__h:.0f}m, h0={self.__h0:.0f}m, sk={self.sk:.2f}kN/m²)"


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    print("=== France ===")
    for zone, alt in [("A1", 150), ("A2", 350), ("C2", 800), ("E", 1500)]:
        g = GroundSnowLoadFR(zone=zone, altitude=alt)
        print(f"  {g!r}")
        print(f"  {g.report(with_values=True)}")

    print("\n=== Suisse ===")
    g_ch = GroundSnowLoadCH(h=600, h0=500)
    print(f"  {g_ch!r}")
    print(f"  {g_ch.report(with_values=True)}")
