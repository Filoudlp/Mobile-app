#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vitesse de référence du vent et pression dynamique de base — France et Suisse.

Vérification unitaire indépendante (même principe que ``norme.EC1.neige.*`` /
``norme.EC3.elu.*``) : chaque classe ne dépend que des grandeurs qui lui sont
propres, pas d'un objet "site" composite.

France — NF EN 1991-1-4/NA, éq. (4.1) + Tableau 4.2(NA) :
    vb = cdir · cseason · vb,0
    vb,0 donnée par région climatique (1 à 4 en métropole, valeur propre par
    DOM). cdir = cseason = 1,0 recommandé (valeurs plus favorables possibles,
    non retenues ici par simplification — cf. Figures 4.4(NA)/4.5(NA)).
    qb = 0,5 · ρ · vb²  (éq. 4.10, ρ = 1,25 kg/m³ recommandé)

Suisse — SIA 261:2020, §6.2.1.3 :
    La valeur de référence de la pression dynamique qp0 est lue directement
    sur la carte de l'Annexe E (isolignes, comme l'Annexe D pour la neige —
    pas de table par commune). qp0 correspond à z = 10 m, catégorie de
    terrain III, période de retour 50 ans.
    Valeur "zone générale" (plaine, hors crêtes/sommets et zones de
    transition) : qp0 = 0,9 kN/m².
"""

__all__ = [
    'BaseWindVelocityFR', 'ReferencePressureCH',
    'FR_VB0', 'zones_for_department', 'load_fr_region_table',
]

import json
from pathlib import Path
from typing import Dict, List, Optional

from core.formula import FormulaResult, FormulaCollection

_RESSOURCE_DIR = Path(__file__).resolve().parents[3] / "ressource"

#: Masse volumique de l'air recommandée — EN 1991-1-4 §4.5(1) NOTE 2.
RHO_AIR = 1.25

# ---------------------------------------------------------------------------
# France — Tableau 4.2(NA)
# ---------------------------------------------------------------------------

#: vb,0 [m/s] par région climatique — NF EN 1991-1-4/NA, Tableau 4.2(NA).
FR_VB0: Dict[str, float] = {
    "1": 22.0, "2": 24.0, "3": 26.0, "4": 28.0,
    "guadeloupe": 36.0, "guyane": 17.0, "martinique": 32.0, "reunion": 34.0,
}

_REGIONS_JSON_CACHE: Optional[dict] = None


def load_fr_region_table() -> dict:
    """Charge ressource/vent_zones_fr.json (table des départements)."""
    global _REGIONS_JSON_CACHE
    if _REGIONS_JSON_CACHE is None:
        with open(_RESSOURCE_DIR / "vent_zones_fr.json", "r", encoding="utf-8") as f:
            _REGIONS_JSON_CACHE = json.load(f)
    return _REGIONS_JSON_CACHE


def zones_for_department(code: str) -> List[int]:
    """Liste des régions climatiques possibles pour un département
    (ex. '01' -> [1, 2])."""
    data = load_fr_region_table()
    dept = data["departements"].get(code.upper())
    if dept is None:
        raise ValueError(f"Département '{code}' inconnu.")
    return dept["regions"]


class BaseWindVelocityFR:
    """
    Vitesse de référence et pression dynamique de base — France
    (NF EN 1991-1-4/NA).

    :param region: Région climatique — '1' à '4' (métropole) ou
        'guadeloupe' / 'guyane' / 'martinique' / 'reunion' (DOM).
    :param cdir: Coefficient de direction (1,0 par défaut — sécuritaire).
    :param cseason: Coefficient de saison (1,0 par défaut — situation de
        projet non limitée à avril-septembre).
    """

    def __init__(self, region: str, cdir: float = 1.0, cseason: float = 1.0) -> None:
        region = str(region).lower().strip()
        if region not in FR_VB0:
            raise ValueError(
                f"Région '{region}' inconnue. Valeurs valides : {sorted(FR_VB0.keys())}"
            )
        self.__region = region
        self.__cdir = cdir
        self.__cseason = cseason

    @property
    def region(self) -> str:
        return self.__region

    @property
    def cdir(self) -> float:
        return self.__cdir

    @property
    def cseason(self) -> float:
        return self.__cseason

    @property
    def vb0(self) -> float:
        """Valeur de base de la vitesse de référence [m/s]."""
        return FR_VB0[self.__region]

    @property
    def vb(self) -> float:
        """Vitesse de référence du vent vb [m/s] — éq. (4.1)."""
        return round(self.__cdir * self.__cseason * self.vb0, 4)

    @property
    def qb(self) -> float:
        """Pression dynamique de base qb [kN/m²] — éq. (4.10)."""
        return round(0.5 * RHO_AIR * self.vb ** 2 / 1000.0, 5)

    def get_vb(self, with_values: bool = False) -> FormulaResult:
        fv = ""
        if with_values:
            fv = (
                f"vb = {self.__cdir:.2f} × {self.__cseason:.2f} × {self.vb0:.1f} "
                f"= {self.vb:.2f} m/s"
            )
        return FormulaResult(
            name="vb",
            formula="vb = cdir · cseason · vb,0",
            formula_values=fv,
            result=self.vb,
            unit="m/s",
            ref="NF EN 1991-1-4 — éq. (4.1) / Annexe nationale Tableau 4.2(NA)",
        )

    def get_qb(self, with_values: bool = False) -> FormulaResult:
        fv = ""
        if with_values:
            fv = f"qb = 0,5 × {RHO_AIR} × {self.vb:.2f}² = {self.qb:.4f} kN/m²"
        return FormulaResult(
            name="qb",
            formula="qb = 0,5 · ρ · vb²",
            formula_values=fv,
            result=self.qb,
            unit="kN/m²",
            ref="NF EN 1991-1-4 — éq. (4.10)",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Vitesse et pression de base — France, région {self.__region}",
            ref="NF EN 1991-1-4/NA",
        )
        fc.add(self.get_vb(with_values=with_values))
        fc.add(self.get_qb(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"BaseWindVelocityFR(region='{self.__region}', vb0={self.vb0:.1f}m/s, "
            f"vb={self.vb:.2f}m/s, qb={self.qb:.3f}kN/m²)"
        )


# ---------------------------------------------------------------------------
# Suisse — SIA 261:2020, Annexe E
# ---------------------------------------------------------------------------

class ReferencePressureCH:
    """
    Valeur de référence de la pression dynamique — Suisse (SIA 261:2020,
    §6.2.1.3, Annexe E).

    :param qp0: Pression dynamique de référence [kN/m²], lue sur la carte de
        l'Annexe E (isolignes ; pas de table par commune — voir docstring du
        module). Valeur "zone générale" par défaut : 0,9 kN/m².
    """

    #: Valeur "zone générale" (plaine) — SIA 261, Annexe E.
    QP0_GENERAL = 0.9

    def __init__(self, qp0: float = QP0_GENERAL) -> None:
        if qp0 <= 0:
            raise ValueError("qp0 (Annexe E) doit être > 0.")
        self.__qp0 = qp0

    @property
    def qp0(self) -> float:
        return self.__qp0

    def get_qp0(self, with_values: bool = False) -> FormulaResult:
        fv = f"qp0 = {self.__qp0:.2f} kN/m² (lecture directe — Annexe E)" if with_values else ""
        return FormulaResult(
            name="qp0",
            formula="qp0 — valeur directe (carte, Annexe E)",
            formula_values=fv,
            result=self.__qp0,
            unit="kN/m²",
            ref="SIA 261:2020 — §6.2.1.3, Annexe E",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Pression dynamique de référence — Suisse (SIA 261)",
            ref="SIA 261:2020 — Annexe E",
        )
        fc.add(self.get_qp0(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return f"ReferencePressureCH(qp0={self.__qp0:.2f}kN/m²)"


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    print("=== France ===")
    for region in ["1", "2", "3", "4"]:
        v = BaseWindVelocityFR(region=region)
        print(f"  {v!r}")

    print("\n=== Suisse ===")
    v_ch = ReferencePressureCH(qp0=0.9)
    print(f"  {v_ch!r}")
    print(f"  {v_ch.report(with_values=True)}")
