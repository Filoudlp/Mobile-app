#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe orchestratrice pour la détermination de la pression du vent sur les
murs verticaux d'un bâtiment rectangulaire — France (NF EN 1991-1-4/NA) et
Suisse (SIA 261:2020).

WindLoad ne contient aucune logique de calcul : elle délègue tout aux
classes indépendantes de ``norme.EC1.vent.*`` (approche composition — même
principe que ``norme.EC1.element.snow_load.SnowLoad`` /
``norme.EC3.element.steel_column.SteelColumn``).

Périmètre (v1, volontairement limité — comme le module neige restreint aux
toitures à un/deux versants) :
    - Pression sur les murs verticaux d'un bâtiment à plan rectangulaire
      (zones A, B, C, D, E — EN 1991-1-4 §7.2.2 / Tableau 7.1).
    - Hauteur de référence ze = h (procédure simplifiée admise par la NOTE
      de l'EN 1991-1-4 §7.2.2(1) pour les zones latérales/sous le vent,
      étendue ici à la zone au vent D pour rester dans le périmètre v1).
    - cscd = 1,0 (facteur structural par défaut — admis pour les bâtiments
      courants de faible hauteur par EN 1991-1-4 §6.2(1) et SIA 261 §6.3).
    - co(z) = 1,0 (orographie neutre — terrain courant).

Hors périmètre (non traité) : pressions de toiture (Tableaux 7.2 à 7.4b),
pression intérieure cpi, éléments isolés, frottement, torsion, ponts,
cscd calculé (bâtiments élancés/sensibles au vent), effets de cyclone DOM.
"""

__all__ = ['WindLoad']

from typing import Dict, Optional
from core.formula import FormulaCollection

from norme.EC1.vent.base_velocity import BaseWindVelocityFR, ReferencePressureCH
from norme.EC1.vent.wind_profile import WindPressureFR, WindPressureCH, FR_TERRAIN_CATEGORIES, CH_TERRAIN_CATEGORIES
from norme.EC1.vent.pressure_coefficient import WallPressureCoefficients

_ZONES = ("A", "B", "C", "D", "E")


class WindLoad:
    """
    Orchestrateur de détermination de la pression du vent sur les murs
    verticaux d'un bâtiment rectangulaire.

    Parameters
    ----------
    country : str
        ``"FR"`` ou ``"CH"``.
    h, b, d : float
        Hauteur du bâtiment, largeur au vent, profondeur dans le sens du
        vent [m] (voir ``WallPressureCoefficients``).
    terrain_category : str
        France — ``"0"``, ``"II"``, ``"IIIa"``, ``"IIIb"``, ``"IV"`` ;
        Suisse — ``"II"``, ``"IIa"``, ``"III"``, ``"IV"``.
    cscd : float
        Facteur structural (1,0 par défaut).
    region : str, optional
        Région climatique française (requis si ``country="FR"`` — voir
        ``BaseWindVelocityFR``).
    cdir, cseason : float
        Coefficients de direction / saison (France, 1,0 par défaut).
    qp0 : float, optional
        Pression dynamique de référence [kN/m²] (requis si ``country="CH"``
        — voir ``ReferencePressureCH``).
    """

    def __init__(
        self,
        country: str,
        h: float,
        b: float,
        d: float,
        terrain_category: str,
        cscd: float = 1.0,
        # France
        region: Optional[str] = None,
        cdir: float = 1.0,
        cseason: float = 1.0,
        # Suisse
        qp0: Optional[float] = None,
    ) -> None:
        country = country.upper().strip()
        if country not in ("FR", "CH"):
            raise ValueError(f"country doit être 'FR' ou 'CH' (reçu : '{country}')")

        self.__country = country
        self.__cscd = cscd
        self.__region = region
        self.__qp0_input = qp0

        self.__walls = WallPressureCoefficients(h=h, b=b, d=d)

        if country == "FR":
            if region is None:
                raise ValueError("France : 'region' est requis.")
            if terrain_category not in FR_TERRAIN_CATEGORIES:
                raise ValueError(
                    f"Catégorie de terrain '{terrain_category}' invalide pour la France. "
                    f"Valeurs : {list(FR_TERRAIN_CATEGORIES.keys())}"
                )
            self.__velocity = BaseWindVelocityFR(region=region, cdir=cdir, cseason=cseason)
            self.__pressure = WindPressureFR(vb=self.__velocity.vb, category=terrain_category)
        else:
            if qp0 is None:
                raise ValueError("Suisse : 'qp0' est requis.")
            if terrain_category not in CH_TERRAIN_CATEGORIES:
                raise ValueError(
                    f"Catégorie de terrain '{terrain_category}' invalide pour la Suisse. "
                    f"Valeurs : {list(CH_TERRAIN_CATEGORIES.keys())}"
                )
            self.__velocity = ReferencePressureCH(qp0=qp0)
            self.__pressure = WindPressureCH(qp0=self.__velocity.qp0, category=terrain_category)

    # ------------------------------------------------------------------
    #  Propriétés
    # ------------------------------------------------------------------
    @property
    def country(self) -> str:
        return self.__country

    @property
    def walls(self) -> WallPressureCoefficients:
        return self.__walls

    @property
    def velocity(self):
        """Instance BaseWindVelocityFR / ReferencePressureCH sous-jacente."""
        return self.__velocity

    @property
    def pressure(self):
        """Instance WindPressureFR / WindPressureCH sous-jacente."""
        return self.__pressure

    @property
    def cscd(self) -> float:
        return self.__cscd

    @property
    def ze(self) -> float:
        """Hauteur de référence retenue (simplification v1 : ze = h)."""
        return self.__walls.h

    @property
    def qp(self) -> float:
        """Pression dynamique de pointe qp(ze) [kN/m²]."""
        return self.__pressure.qp(self.ze)

    # ------------------------------------------------------------------
    #  Pressions par zone
    # ------------------------------------------------------------------
    def we(self, zone: str) -> float:
        """Pression extérieure we [kN/m²] = cscd · qp(ze) · cpe,10(zone) —
        EN 1991-1-4 éq. (5.1) (cscd = 1,0 par défaut)."""
        cpe10, _ = self.__walls.cpe(zone)
        return round(self.__cscd * self.qp * cpe10, 5)

    def pressures(self) -> Dict[str, float]:
        """we [kN/m²] pour toutes les zones existantes (A, B, [C], D, E)."""
        zones = [z for z in _ZONES if z != "C" or self.__walls.has_zone_c]
        return {z: self.we(z) for z in zones}

    # ------------------------------------------------------------------
    #  Rapport complet
    # ------------------------------------------------------------------
    def full_check(self, with_values: bool = False) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Pression du vent — murs verticaux, {self.__country}",
            ref="NF EN 1991-1-4 / SIA 261",
        )
        for r in self.__velocity.report(with_values=with_values):
            fc.add(r)
        fc.add(self.__pressure.get_qp(self.ze, with_values=with_values))
        for r in self.__walls.report(with_values=with_values):
            fc.add(r)
        return fc

    def summary(self) -> dict:
        """Résumé : qp(ze) et pression we retenue par zone (valeur de
        calcul à utiliser pour le dimensionnement des murs/ossature)."""
        pressures = self.pressures()
        return {
            "qp": self.qp,
            "ze": self.ze,
            "h_d": self.__walls.h_d,
            "pressures": pressures,
            "we_max": max(pressures.values(), key=abs),
        }

    def __repr__(self) -> str:
        loc = f"region={self.__region}" if self.__country == "FR" else f"qp0={self.__qp0_input}"
        return f"WindLoad(country='{self.__country}', {loc}, h={self.__walls.h:.1f}m, qp={self.qp:.3f}kN/m²)"


# ======================================================================
#  Debug / exemple d'utilisation
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 60

    print(f"\n{sep}")
    print("  CAS 1 : France, région 2, terrain II, bâtiment 9x15x25m")
    print(sep)
    wind_fr = WindLoad(country="FR", h=9, b=15, d=25, terrain_category="II", region="2")
    print(f"  {repr(wind_fr)}")
    s = wind_fr.summary()
    print(f"  qp = {s['qp']:.3f} kN/m² | h/d = {s['h_d']:.2f}")
    for zone, we in s["pressures"].items():
        print(f"    we({zone}) = {we:+.3f} kN/m²")

    print(f"\n{sep}")
    print("  CAS 2 : Suisse, qp0=0.9, terrain III, bâtiment 9x15x25m")
    print(sep)
    wind_ch = WindLoad(country="CH", h=9, b=15, d=25, terrain_category="III", qp0=0.9)
    print(f"  {repr(wind_ch)}")
    s = wind_ch.summary()
    print(f"  qp = {s['qp']:.3f} kN/m² | h/d = {s['h_d']:.2f}")
    for zone, we in s["pressures"].items():
        print(f"    we({zone}) = {we:+.3f} kN/m²")

    print(f"\n{sep}")
    print("  CAS 3 : Full check (rapport détaillé, France)")
    print(sep)
    print(wind_fr.full_check(with_values=True))

    print(f"\n{'=' * 60}")
    print("  FIN DES TESTS")
    print(f"{'=' * 60}")
