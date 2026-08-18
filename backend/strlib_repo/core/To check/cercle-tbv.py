#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define circular section geometric properties.

    This class is purely geometric — no material dependency.
    Material-specific properties live in Section_Material classes.

    References:
        - Standard geometry formulas
"""

__all__ = ['SecCircular']

from typing import Optional, List
import math

from core.section.section import Section
from formula import FormulaResult


class SecCircular(Section):
    """
    Section circulaire — propriétés géométriques pures.

    Convention d'axes :
        - y : axe horizontal
        - z : axe vertical
        - Origine au centre de gravité (centre du cercle)

    :param d: Diamètre extérieur de la section [mm]
    :param t: Épaisseur paroi pour tube creux [mm] (None = plein)
    :param name: Nom optionnel de la section
    """

    def __init__(
        self,
        d: float,
        t: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:

        # ----- Validation -----
        if d <= 0:
            raise ValueError(f"d doit être strictement positif (reçu : {d})")
        if t is not None:
            if t <= 0:
                raise ValueError(f"t doit être strictement positif (reçu : {t})")
            if t >= d / 2:
                raise ValueError(f"t doit être < d/2 (reçu : t={t}, d/2={d/2})")

        # ----- Données d'entrée -----
        self._d = d
        self._t = t

        # ----- Nom par défaut -----
        if name is None:
            if t is None:
                name = f"CIRC Ø{d:.0f}"
            else:
                name = f"CHS Ø{d:.0f}×{t:.1f}"

        super().__init__(name=name)

    # =================================================================
    # Dimensions internes (lecture seule)
    # =================================================================

    @property
    def _di(self) -> float:
        """Diamètre intérieur [mm] — 0 si plein"""
        if self._t is None:
            return 0.0
        return self._d - 2 * self._t

    @property
    def _r(self) -> float:
        """Rayon extérieur [mm]"""
        return self._d / 2

    @property
    def _ri(self) -> float:
        """Rayon intérieur [mm] — 0 si plein"""
        return self._di / 2

    @property
    def is_hollow(self) -> bool:
        """True si section creuse (tube)"""
        return self._t is not None

    # =================================================================
    # Setters avec recalcul implicite (tout est en @property)
    # =================================================================

    @property
    def d(self) -> float:
        """Diamètre extérieur [mm]"""
        return self._d

    @d.setter
    def d(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"d doit être strictement positif (reçu : {value})")
        if self._t is not None and self._t >= value / 2:
            raise ValueError(f"t={self._t} incompatible avec d={value}")
        self._d = value

    @property
    def t(self) -> Optional[float]:
        """Épaisseur paroi [mm] — None si plein"""
        return self._t

    @t.setter
    def t(self, value: Optional[float]) -> None:
        if value is not None:
            if value <= 0:
                raise ValueError(f"t doit être strictement positif (reçu : {value})")
            if value >= self._d / 2:
                raise ValueError(f"t doit être < d/2 (reçu : t={value}, d/2={self._d/2})")
        self._t = value

    # =================================================================
    # Centre de gravité
    # =================================================================

    @property
    def yg(self) -> float:
        """Position du CDG selon y depuis le bord gauche [mm]"""
        return self._r

    @property
    def zg(self) -> float:
        """Position du CDG selon z depuis le bord inférieur [mm]"""
        return self._r

    # =================================================================
    # Aire
    # =================================================================

    @property
    def area(self) -> float:
        """Aire de la section [mm²]"""
        return math.pi / 4 * (self._d**2 - self._di**2)

    def _report_area(self) -> FormulaResult:
        if self.is_hollow:
            return FormulaResult(
                name="A",
                formula="A = π/4 × (D² − Di²)",
                formula_values=f"A = π/4 × ({self._d:.1f}² − {self._di:.1f}²) = {self.area:.2f}",
                value=self.area,
                unit="mm²",
                ref="Géométrie",
            )
        return FormulaResult(
            name="A",
            formula="A = π/4 × D²",
            formula_values=f"A = π/4 × {self._d:.1f}² = {self.area:.2f}",
            value=self.area,
            unit="mm²",
            ref="Géométrie",
        )

    # =================================================================
    # Moments d'inertie
    # =================================================================

    @property
    def inertia_y(self) -> float:
        """Moment d'inertie selon y (= selon z par symétrie) [mm⁴]"""
        return math.pi / 64 * (self._d**4 - self._di**4)

    @property
    def inertia_z(self) -> float:
        """Moment d'inertie selon z [mm⁴]"""
        return self.inertia_y

    def _report_inertia(self) -> FormulaResult:
        if self.is_hollow:
            return FormulaResult(
                name="I",
                formula="I = π/64 × (D⁴ − Di⁴)",
                formula_values=f"I = π/64 × ({self._d:.1f}⁴ − {self._di:.1f}⁴) = {self.inertia_y:.2f}",
                value=self.inertia_y,
                unit="mm⁴",
                ref="Géométrie",
            )
        return FormulaResult(
            name="I",
            formula="I = π/64 × D⁴",
            formula_values=f"I = π/64 × {self._d:.1f}⁴ = {self.inertia_y:.2f}",
            value=self.inertia_y,
            unit="mm⁴",
            ref="Géométrie",
        )

    # =================================================================
    # Moments statiques max
    # =================================================================

    @property
    def sy(self) -> float:
        """Moment statique maximal selon y [mm³]"""
        return (self._d**3 - self._di**3) / 12

    @property
    def sz(self) -> float:
        """Moment statique maximal selon z [mm³]"""
        return self.sy

    def _report_sy(self) -> FormulaResult:
        if self.is_hollow:
            return FormulaResult(
                name="Sy",
                formula="Sy = (D³ − Di³) / 12",
                formula_values=f"Sy = ({self._d:.1f}³ − {self._di:.1f}³) / 12 = {self.sy:.2f}",
                value=self.sy,
                unit="mm³",
                ref="Géométrie",
            )
        return FormulaResult(
            name="Sy",
            formula="Sy = D³ / 12",
            formula_values=f"Sy = {self._d:.1f}³ / 12 = {self.sy:.2f}",
            value=self.sy,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Modules de résistance élastiques
    # =================================================================

    @property
    def wel_y(self) -> float:
        """Module de résistance élastique selon y [mm³]"""
        return self.inertia_y / self._r

    @property
    def wel_z(self) -> float:
        """Module de résistance élastique selon z [mm³]"""
        return self.wel_y

    def _report_wel(self) -> FormulaResult:
        return FormulaResult(
            name="Wel",
            formula="Wel = I / (D/2)",
            formula_values=f"Wel = {self.inertia_y:.2f} / {self._r:.1f} = {self.wel_y:.2f}",
            value=self.wel_y,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Modules de résistance plastiques
    # =================================================================

    @property
    def wpl_y(self) -> float:
        """Module de résistance plastique selon y [mm³]"""
        return (self._d**3 - self._di**3) / 6

    @property
    def wpl_z(self) -> float:
        """Module de résistance plastique selon z [mm³]"""
        return self.wpl_y

    def _report_wpl(self) -> FormulaResult:
        if self.is_hollow:
            return FormulaResult(
                name="Wpl",
                formula="Wpl = (D³ − Di³) / 6",
                formula_values=f"Wpl = ({self._d:.1f}³ − {self._di:.1f}³) / 6 = {self.wpl_y:.2f}",
                value=self.wpl_y,
                unit="mm³",
                ref="Géométrie",
            )
        return FormulaResult(
            name="Wpl",
            formula="Wpl = D³ / 6",
            formula_values=f"Wpl = {self._d:.1f}³ / 6 = {self.wpl_y:.2f}",
            value=self.wpl_y,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Rayons de giration
    # =================================================================

    @property
    def iy(self) -> float:
        """Rayon de giration selon y [mm]"""
        return math.sqrt(self.inertia_y / self.area)

    @property
    def iz(self) -> float:
        """Rayon de giration selon z [mm]"""
        return self.iy

    def _report_iy(self) -> FormulaResult:
        return FormulaResult(
            name="iy",
            formula="iy = √(I / A)",
            formula_values=f"iy = √({self.inertia_y:.2f} / {self.area:.2f}) = {self.iy:.2f}",
            value=self.iy,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Périmètre
    # =================================================================

    @property
    def perimeter(self) -> float:
        """Périmètre extérieur [mm]"""
        return math.pi * self._d

    @property
    def perimeter_inner(self) -> float:
        """Périmètre intérieur [mm] — 0 si plein"""
        if not self.is_hollow:
            return 0.0
        return math.pi * self._di

    def _report_perimeter(self) -> FormulaResult:
        return FormulaResult(
            name="u",
            formula="u = π × D",
            formula_values=f"u = π × {self._d:.1f} = {self.perimeter:.2f}",
            value=self.perimeter,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Inertie de torsion (Saint-Venant)
    # =================================================================

    @property
    def it(self) -> float:
        """Inertie de torsion de Saint-Venant [mm⁴]"""
        return math.pi / 32 * (self._d**4 - self._di**4)

    def _report_it(self) -> FormulaResult:
        if self.is_hollow:
            return FormulaResult(
                name="It",
                formula="It = π/32 × (D⁴ − Di⁴)",
                formula_values=f"It = π/32 × ({self._d:.1f}⁴ − {self._di:.1f}⁴) = {self.it:.2f}",
                value=self.it,
                unit="mm⁴",
                ref="Géométrie",
            )
        return FormulaResult(
            name="It",
            formula="It = π/32 × D⁴",
            formula_values=f"It = π/32 × {self._d:.1f}⁴ = {self.it:.2f}",
            value=self.it,
            unit="mm⁴",
            ref="Géométrie",
        )

    # =================================================================
    # Reporting
    # =================================================================

    def all_reports(self) -> List[FormulaResult]:
        """Liste de tous les FormulaResult de la section"""
        return [
            self._report_area(),
            self._report_inertia(),
            self._report_sy(),
            self._report_wel(),
            self._report_wpl(),
            self._report_iy(),
            self._report_perimeter(),
            self._report_it(),
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        if self.is_hollow:
            return f"SecCircular(d={self._d}, t={self._t}, name='{self._name}')"
        return f"SecCircular(d={self._d}, name='{self._name}')"

    def __str__(self) -> str:
        header = f"Ø{self._d:.0f}" + (f"×{self._t:.1f}" if self.is_hollow else " plein")
        lines = [
            f"{'=' * 65}",
            f"  {self._name} — {header}",
            f"{'=' * 65}",
        ]
        for r in self.all_reports():
            lines.append(f"  {r.formula_values:55s} [{r.unit:5s}]  ({r.ref})")
        lines.append(f"{'=' * 65}")
        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    # --- Cercle plein Ø300 ---
    circ = SecCircular(d=300)
    print(circ)

    # --- Tube CHS Ø273×10 ---
    tube = SecCircular(d=273, t=10)
    print(tube)

    # --- Modification dynamique ---
    print("\n--- Passage à Ø400 ---")
    circ.d = 400
    print(f"A  = {circ.area:.0f} mm²")
    print(f"I  = {circ.inertia_y:.0f} mm⁴")
    print(f"It = {circ.it:.0f} mm⁴")
