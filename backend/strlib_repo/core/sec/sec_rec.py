#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define rectangular section geometric properties.

    This class is purely geometric — no material dependency.
    Material-specific properties (effective depth, plastic modulus, etc.)
    live in Section_Material classes (SecMatRC, SecMatSteel, etc.).

    References:
        - Standard geometry formulas
"""

__all__ = ['SecRectangular']

from typing import Optional

from core.sec.section import Section
from core.formula import FormulaResult


# =============================================================================
# SecRectangular
# =============================================================================

class SecRectangular(Section):
    """
    Section rectangulaire — propriétés géométriques pures.

    Aucune dépendance au matériau : la section ne connaît que sa géométrie.
    Les propriétés liées au matériau (hauteur utile, modules plastiques
    spécifiques, etc.) seront gérées par les classes Section_Material
    (SecMatRC, SecMatSteel, SecMatTimber, etc.).

    Convention d'axes :
        - y : axe horizontal (largeur b)
        - z : axe vertical   (hauteur h)
        - Origine au centre de gravité

    :param b: Largeur de la section [mm]
    :param h: Hauteur de la section [mm]
    :param name: Nom optionnel de la section
    """

    def __init__(
        self,
        b: float,
        h: float,
        name: Optional[str] = None,
    ) -> None:

        # ----- Validation -----
        if b <= 0:
            raise ValueError(f"b doit être strictement positif (reçu : {b})")
        if h <= 0:
            raise ValueError(f"h doit être strictement positif (reçu : {h})")

        # ----- Données d'entrée -----
        self._b = b
        self._h = h

        # ----- Nom auto -----
        _name = name or f"RECT {b:.0f}×{h:.0f}"
        super().__init__(name=_name)

    # =================================================================
    # Setters avec recalcul implicite (les @property font le calcul)
    # =================================================================

    @property
    def b(self) -> float:
        """Largeur de la section [mm]"""
        return self._b

    @b.setter
    def b(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"b doit être strictement positif (reçu : {value})")
        self._b = value
        self._name = f"RECT {self._b:.0f}×{self._h:.0f}"

    @property
    def h(self) -> float:
        """Hauteur de la section [mm]"""
        return self._h

    @h.setter
    def h(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"h doit être strictement positif (reçu : {value})")
        self._h = value
        self._name = f"RECT {self._b:.0f}×{self._h:.0f}"

    # =================================================================
    # Propriétés géométriques — Centre de gravité
    # =================================================================

    @property
    def yg(self) -> float:
        """Position du CDG selon y depuis le bord gauche [mm]"""
        return self._b / 2

    @property
    def yg_report(self) -> FormulaResult:
        return FormulaResult(
            name="yg",
            formula="yg = b / 2",
            formula_values=f"yg = {self._b:.2f} / 2 = {self.yg:.2f}",
            result=self.yg,
            unit="mm",
            ref="Géométrie",
        )

    @property
    def zg(self) -> float:
        """Position du CDG selon z depuis le bord inférieur [mm]"""
        return self._h / 2

    @property
    def zg_report(self) -> FormulaResult:
        return FormulaResult(
            name="zg",
            formula="zg = h / 2",
            formula_values=f"zg = {self._h:.2f} / 2 = {self.zg:.2f}",
            result=self.zg,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Propriétés géométriques — Aire
    # =================================================================

    @property
    def area(self) -> float:
        """Aire de la section [mm²]"""
        return self._b * self._h

    @property
    def area_report(self) -> FormulaResult:
        return FormulaResult(
            name="A",
            formula="A = b × h",
            formula_values=f"A = {self._b:.2f} × {self._h:.2f} = {self.area:.2f}",
            result=self.area,
            unit="mm²",
            ref="Géométrie",
        )

    # =================================================================
    # Propriétés géométriques — Moments d'inertie
    # =================================================================

    @property
    def inertia_y(self) -> float:
        """Moment d'inertie selon y (flexion autour de y) [mm⁴]"""
        return self._b * self._h ** 3 / 12

    @property
    def inertia_y_report(self) -> FormulaResult:
        return FormulaResult(
            name="Iy",
            formula="Iy = b × h³ / 12",
            formula_values=(
                f"Iy = {self._b:.2f} × {self._h:.2f}³ / 12 = {self.inertia_y:.2f}"
            ),
            result=self.inertia_y,
            unit="mm⁴",
            ref="Géométrie",
        )

    @property
    def inertia_z(self) -> float:
        """Moment d'inertie selon z (flexion autour de z) [mm⁴]"""
        return self._h * self._b ** 3 / 12

    @property
    def inertia_z_report(self) -> FormulaResult:
        return FormulaResult(
            name="Iz",
            formula="Iz = h × b³ / 12",
            formula_values=(
                f"Iz = {self._h:.2f} × {self._b:.2f}³ / 12 = {self.inertia_z:.2f}"
            ),
            result=self.inertia_z,
            unit="mm⁴",
            ref="Géométrie",
        )

    # =================================================================
    # Propriétés géométriques — Moments statiques
    # =================================================================

    @property
    def sy(self) -> float:
        """Moment statique maximal selon y (à mi-hauteur) [mm³]"""
        return self._b * self._h ** 2 / 8

    @property
    def sy_report(self) -> FormulaResult:
        return FormulaResult(
            name="Sy",
            formula="Sy = b × h² / 8",
            formula_values=f"Sy = {self._b:.2f} × {self._h:.2f}² / 8 = {self.sy:.2f}",
            result=self.sy,
            unit="mm³",
            ref="Géométrie — moment statique maximal",
        )

    @property
    def sz(self) -> float:
        """Moment statique maximal selon z (à mi-largeur) [mm³]"""
        return self._h * self._b ** 2 / 8

    @property
    def sz_report(self) -> FormulaResult:
        return FormulaResult(
            name="Sz",
            formula="Sz = h × b² / 8",
            formula_values=f"Sz = {self._h:.2f} × {self._b:.2f}² / 8 = {self.sz:.2f}",
            result=self.sz,
            unit="mm³",
            ref="Géométrie — moment statique maximal",
        )

    # =================================================================
    # Propriétés géométriques — Modules de résistance élastiques
    # =================================================================

    @property
    def wel_y(self) -> float:
        """Module de résistance élastique selon y [mm³]"""
        return self._b * self._h ** 2 / 6

    @property
    def wel_y_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wel,y",
            formula="Wel,y = b × h² / 6",
            formula_values=f"Wel,y = {self._b:.2f} × {self._h:.2f}² / 6 = {self.wel_y:.2f}",
            result=self.wel_y,
            unit="mm³",
            ref="Géométrie",
        )

    @property
    def wel_z(self) -> float:
        """Module de résistance élastique selon z [mm³]"""
        return self._h * self._b ** 2 / 6

    @property
    def wel_z_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wel,z",
            formula="Wel,z = h × b² / 6",
            formula_values=f"Wel,z = {self._h:.2f} × {self._b:.2f}² / 6 = {self.wel_z:.2f}",
            result=self.wel_z,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Propriétés géométriques — Modules de résistance plastiques
    # =================================================================

    @property
    def wpl_y(self) -> float:
        """Module de résistance plastique selon y [mm³]"""
        return self._b * self._h ** 2 / 4

    @property
    def wpl_y_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wpl,y",
            formula="Wpl,y = b × h² / 4",
            formula_values=f"Wpl,y = {self._b:.2f} × {self._h:.2f}² / 4 = {self.wpl_y:.2f}",
            result=self.wpl_y,
            unit="mm³",
            ref="Géométrie",
        )

    @property
    def wpl_z(self) -> float:
        """Module de résistance plastique selon z [mm³]"""
        return self._h * self._b ** 2 / 4

    @property
    def wpl_z_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wpl,z",
            formula="Wpl,z = h × b² / 4",
            formula_values=f"Wpl,z = {self._h:.2f} × {self._b:.2f}² / 4 = {self.wpl_z:.2f}",
            result=self.wpl_z,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Propriétés géométriques — Rayons de giration
    # =================================================================

    @property
    def iy(self) -> float:
        """Rayon de giration selon y [mm]"""
        return self._h / (12 ** 0.5)

    @property
    def iy_report(self) -> FormulaResult:
        return FormulaResult(
            name="iy",
            formula="iy = h / √12",
            formula_values=f"iy = {self._h:.2f} / √12 = {self.iy:.2f}",
            result=self.iy,
            unit="mm",
            ref="Géométrie",
        )

    @property
    def iz(self) -> float:
        """Rayon de giration selon z [mm]"""
        return self._b / (12 ** 0.5)

    @property
    def iz_report(self) -> FormulaResult:
        return FormulaResult(
            name="iz",
            formula="iz = b / √12",
            formula_values=f"iz = {self._b:.2f} / √12 = {self.iz:.2f}",
            result=self.iz,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Périmètre
    # =================================================================

    @property
    def perimeter(self) -> float:
        """Périmètre de la section [mm]"""
        return 2 * (self._b + self._h)

    @property
    def perimeter_report(self) -> FormulaResult:
        return FormulaResult(
            name="u",
            formula="u = 2 × (b + h)",
            formula_values=f"u = 2 × ({self._b:.2f} + {self._h:.2f}) = {self.perimeter:.2f}",
            result=self.perimeter,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Rapport complet
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        """Renvoie la liste de tous les FormulaResult."""
        return [
            self.area_report,
            self.yg_report,
            self.zg_report,
            self.inertia_y_report,
            self.inertia_z_report,
            self.sy_report,
            self.sz_report,
            self.wel_y_report,
            self.wel_z_report,
            self.wpl_y_report,
            self.wpl_z_report,
            self.iy_report,
            self.iz_report,
            self.perimeter_report,
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        return f"SecRectangular(b={self._b}, h={self._h})"

    def __str__(self) -> str:
        lines = [
            f"{'=' * 65}",
            f"  {self._name} — b={self._b:.0f}mm × h={self._h:.0f}mm",
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

    # --- Section 300×500 ---
    rect = SecRectangular(b=300, h=500)
    print(rect)

    # --- Accès individuel ---
    print(f"\nA   = {rect.area:.0f} mm²")
    print(f"Iy  = {rect.inertia_y:.0f} mm⁴")
    print(f"Wpl = {rect.wpl_y:.0f} mm³")

    # --- Modification dynamique ---
    print("\n--- Passage à b=400 ---")
    rect.b = 400
    print(f"A   = {rect.area:.0f} mm²")
    print(f"Iy  = {rect.inertia_y:.0f} mm⁴")
    print(rect)
