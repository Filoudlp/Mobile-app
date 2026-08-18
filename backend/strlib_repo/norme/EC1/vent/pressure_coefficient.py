#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coefficients de pression extérieure — murs verticaux de bâtiments à plan
rectangulaire (EN 1991-1-4 §7.2.2, Tableau 7.1).

Périmètre volontairement limité (comme pour le module neige, restreint aux
toitures à un/deux versants) : seuls les murs verticaux d'un bâtiment
rectangulaire sont couverts (zones A, B, C au vent latéral, D au vent, E
sous le vent). Sont explicitement hors périmètre : toitures (Tableaux
7.2-7.4a/b), éléments isolés, frottement, cscd, torsion — cf. docstring de
``norme.EC1.element.wind_load``.

Zones (Figure 7.5) :
    e = min(b, 2h)               largeur de référence
    Zone A : bande 0 -> min(e/5, d)   face latérale, la plus proche du bord au vent
    Zone B : bande min(e/5,d) -> min(e,d)  face latérale, intermédiaire
    Zone C : bande min(e,d) -> d      face latérale, reste (n'existe que si e < d)
    Zone D : face au vent (perpendiculaire à d)
    Zone E : face sous le vent

Hauteur de référence ze : la NOTE de l'EN 1991-1-4 §7.2.2(1) autorise, pour
les zones A/B/C/E, de retenir la hauteur du bâtiment h comme hauteur de
référence (procédure recommandée) — c'est la simplification retenue ici pour
toutes les zones (y compris D), plutôt que le découpage en bandes de la
Figure 7.4 pour h > b, qui est hors périmètre de cette version.

Table 7.1 (valeurs recommandées, reprises telles quelles par la France ET la
Suisse — même définition géométrique des zones) :

    h/d    A(cpe10/cpe1)   B(cpe10/cpe1)   C(cpe10/cpe1)   D(cpe10/cpe1)   E(cpe10/cpe1)
    ≥ 5    -1.2 / -1.4     -0.8 / -1.1     -0.5 / -0.5     +0.8 / +1.0     -0.7 / -0.7
    = 1    -1.2 / -1.4     -0.8 / -1.1     -0.5 / -0.5     +0.8 / +1.0     -0.5 / -0.5
    ≤ 0.25 -1.2 / -1.4     -0.8 / -1.1     -0.5 / -0.5     +0.7 / +1.0     -0.3 / -0.3

Interpolation linéaire pour les valeurs intermédiaires de h/d (NOTE 1).
"""

__all__ = ['WallPressureCoefficients']

from typing import Dict, Tuple

from core.formula import FormulaResult, FormulaCollection

#: {zone: {h/d: (cpe10, cpe1)}} — Tableau 7.1. A, B, C sont indépendantes de h/d.
_TABLE_7_1: Dict[str, Dict[float, Tuple[float, float]]] = {
    "A": {5.0: (-1.2, -1.4), 1.0: (-1.2, -1.4), 0.25: (-1.2, -1.4)},
    "B": {5.0: (-0.8, -1.1), 1.0: (-0.8, -1.1), 0.25: (-0.8, -1.1)},
    "C": {5.0: (-0.5, -0.5), 1.0: (-0.5, -0.5), 0.25: (-0.5, -0.5)},
    "D": {5.0: (0.8, 1.0), 1.0: (0.8, 1.0), 0.25: (0.7, 1.0)},
    "E": {5.0: (-0.7, -0.7), 1.0: (-0.5, -0.5), 0.25: (-0.3, -0.3)},
}
_HD_BREAKPOINTS = (0.25, 1.0, 5.0)


def _interp_zone(zone: str, hd: float) -> Tuple[float, float]:
    table = _TABLE_7_1[zone]
    hd_clamped = min(max(hd, 0.25), 5.0)
    if hd_clamped in table:
        return table[hd_clamped]
    lo, hi = (0.25, 1.0) if hd_clamped < 1.0 else (1.0, 5.0)
    t = (hd_clamped - lo) / (hi - lo)
    cpe10 = table[lo][0] + t * (table[hi][0] - table[lo][0])
    cpe1 = table[lo][1] + t * (table[hi][1] - table[lo][1])
    return round(cpe10, 4), round(cpe1, 4)


class WallPressureCoefficients:
    """
    Coefficients de pression extérieure cpe,10 / cpe,1 pour les murs
    verticaux d'un bâtiment à plan rectangulaire — EN 1991-1-4 §7.2.2.

    :param h: Hauteur du bâtiment [m].
    :param b: Largeur au vent (dimension perpendiculaire à la direction du
        vent considérée) [m].
    :param d: Profondeur dans le sens du vent [m].
    """

    def __init__(self, h: float, b: float, d: float) -> None:
        if h <= 0 or b <= 0 or d <= 0:
            raise ValueError("h, b et d doivent être > 0.")
        self.__h = h
        self.__b = b
        self.__d = d

    @property
    def h(self) -> float:
        return self.__h

    @property
    def b(self) -> float:
        return self.__b

    @property
    def d(self) -> float:
        return self.__d

    @property
    def h_d(self) -> float:
        """Rapport h/d."""
        return round(self.__h / self.__d, 4)

    @property
    def e(self) -> float:
        """Largeur de référence e = min(b, 2h) [m] — Figure 7.5."""
        return round(min(self.__b, 2 * self.__h), 4)

    @property
    def has_zone_c(self) -> bool:
        """La zone C n'existe que si e < d."""
        return self.e < self.__d

    def zone_widths(self) -> Dict[str, float]:
        """Largeurs des bandes A/B/(C) le long de d [m] — Figure 7.5."""
        e, d = self.e, self.__d
        if e >= d:
            return {"A": round(min(e / 5, d), 4), "B": round(d - min(e / 5, d), 4), "C": 0.0}
        return {"A": round(e / 5, 4), "B": round(e - e / 5, 4), "C": round(d - e, 4)}

    def cpe(self, zone: str) -> Tuple[float, float]:
        """(cpe,10, cpe,1) pour la zone donnée ('A'..'E'), interpolés selon h/d."""
        zone = zone.upper().strip()
        if zone not in _TABLE_7_1:
            raise ValueError(f"Zone '{zone}' inconnue. Valeurs valides : A, B, C, D, E.")
        if zone == "C" and not self.has_zone_c:
            raise ValueError("Zone C inexistante pour ce bâtiment (e ≥ d).")
        return _interp_zone(zone, self.h_d)

    def get_cpe(self, zone: str, with_values: bool = False) -> FormulaResult:
        cpe10, cpe1 = self.cpe(zone)
        fv = ""
        if with_values:
            fv = f"h/d = {self.h_d:.3f} -> cpe,10({zone}) = {cpe10:.2f} ; cpe,1({zone}) = {cpe1:.2f}"
        return FormulaResult(
            name=f"cpe,10 ({zone})",
            formula="Tableau 7.1 — interpolation linéaire selon h/d",
            formula_values=fv,
            result=cpe10,
            unit="",
            ref="EN 1991-1-4 — §7.2.2, Tableau 7.1",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Coefficients de pression — murs verticaux (h/d={self.h_d:.2f})",
            ref="EN 1991-1-4 — §7.2.2",
        )
        zones = ["A", "B", "D", "E"] + (["C"] if self.has_zone_c else [])
        for z in zones:
            fc.add(self.get_cpe(z, with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return f"WallPressureCoefficients(h={self.__h:.2f}, b={self.__b:.2f}, d={self.__d:.2f}, h/d={self.h_d:.2f})"


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    wpc = WallPressureCoefficients(h=9.0, b=15.0, d=25.0)
    print(f"{wpc!r}")
    print(f"e = {wpc.e:.2f} m | zone C existe : {wpc.has_zone_c} | largeurs : {wpc.zone_widths()}")
    print(wpc.report(with_values=True))
