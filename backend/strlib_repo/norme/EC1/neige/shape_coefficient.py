#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coefficients de forme de toiture pour la charge de neige — μ1 (sans
accumulation) et μ2 (avec accumulation), toitures à un ou deux versants.

EN 1991-1-3 §5.3.2/5.3.3 — Tableau 5.2 (repris à l'identique par la SIA 261,
Figure 2 — même base physique, mêmes seuils angulaires 30°/60°).

Vérification unitaire indépendante : ne dépend que de l'angle de toiture,
comme ``elu.compression`` ne dépend que de N et A/fy.
"""

__all__ = ['RoofShapeCoefficient']

from typing import Optional
from core.formula import FormulaResult, FormulaCollection


class RoofShapeCoefficient:
    """
    Coefficients de forme μ1 (sans accumulation) et μ2 (avec accumulation)
    pour une toiture à un ou deux versants.

    Tableau 5.2 — EN 1991-1-3 :
        0°  ≤ α ≤ 30° : μ1 = 0,8              μ2 = 0,8 + 0,8·α/30
        30° < α < 60° : μ1 = 0,8·(60-α)/30     μ2 = 1,6
        α ≥ 60°       : μ1 = 0                 μ2 = —  (n/a)

    :param angle: Angle de la toiture par rapport à l'horizontale [°].
    """

    def __init__(self, angle: float) -> None:
        if angle < 0 or angle > 90:
            raise ValueError(f"Angle de toiture hors domaine (0-90°) : {angle}")
        self.__angle = angle

    @property
    def angle(self) -> float:
        return self.__angle

    @property
    def mu1(self) -> float:
        """μ1 — coefficient de forme sans accumulation."""
        a = self.__angle
        if a <= 30:
            return 0.8
        if a < 60:
            return round(0.8 * (60 - a) / 30, 4)
        return 0.0

    @property
    def mu2(self) -> Optional[float]:
        """μ2 — coefficient de forme avec accumulation (None si α ≥ 60°)."""
        a = self.__angle
        if a <= 30:
            return round(0.8 + 0.8 * a / 30, 4)
        if a < 60:
            return 1.6
        return None

    def get_mu1(self, with_values: bool = False) -> FormulaResult:
        a = self.__angle
        r = self.mu1
        fv = ""
        if with_values:
            if a <= 30:
                fv = f"μ1 = 0,8 (0° ≤ {a:.1f}° ≤ 30°)"
            elif a < 60:
                fv = f"μ1 = 0,8×(60-{a:.1f})/30 = {r:.4f}"
            else:
                fv = f"μ1 = 0 (α = {a:.1f}° ≥ 60°)"
        return FormulaResult(
            name="μ1",
            formula="μ1 — Tableau 5.2",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EN 1991-1-3 — Tableau 5.2 / SIA 261 — Fig. 2",
        )

    def get_mu2(self, with_values: bool = False) -> FormulaResult:
        a = self.__angle
        r = self.mu2 if self.mu2 is not None else 0.0
        fv = ""
        if with_values:
            if a <= 30:
                fv = f"μ2 = 0,8 + 0,8×{a:.1f}/30 = {r:.4f}"
            elif a < 60:
                fv = f"μ2 = 1,6 (30° < {a:.1f}° < 60°)"
            else:
                fv = f"μ2 non applicable (α = {a:.1f}° ≥ 60°)"
        return FormulaResult(
            name="μ2",
            formula="μ2 — Tableau 5.2",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EN 1991-1-3 — Tableau 5.2 / SIA 261 — Fig. 2",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Coefficients de forme de toiture — α = {self.__angle:.1f}°",
            ref="EN 1991-1-3 — §5.3.2/5.3.3",
        )
        fc.add(self.get_mu1(with_values=with_values))
        fc.add(self.get_mu2(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        mu2_str = f"{self.mu2:.4f}" if self.mu2 is not None else "n/a"
        return f"RoofShapeCoefficient(angle={self.__angle:.1f}°, mu1={self.mu1:.4f}, mu2={mu2_str})"


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    for angle in (0, 15, 30, 45, 59, 60, 75):
        rsc = RoofShapeCoefficient(angle)
        print(f"{rsc!r}")
    print()
    print(RoofShapeCoefficient(25).report(with_values=True))
