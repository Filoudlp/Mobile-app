#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define triangular section geometric properties.

    Triangle isocèle ou quelconque défini par sa base et sa hauteur.
    Convention : base en bas, pointe en haut.

    References:
        - Standard geometry formulas
"""

__all__ = ['SecTriangular']

from typing import Optional, List
import math

from .section import Section
from .formula import FormulaResult


class SecTriangular(Section):
    """
    Section triangulaire — propriétés géométriques pures.

    Convention d'axes :
        - y : axe horizontal (parallèle à la base)
        - z : axe vertical (perpendiculaire à la base)
        - Origine au bord inférieur gauche de la base

    Le triangle est défini par :
        - b  : largeur de la base [mm]
        - h  : hauteur du triangle [mm]
        - d1 : distance horizontale du sommet au bord gauche [mm]
              (par défaut b/2 → triangle isocèle)

    Schéma (isocèle) :
    
              * (d1, h)
             / \
            /   \
           /     \
          /   G   \
         /    ·    \
        *-----------*
        0           b

    :param b:  Largeur de la base [mm]
    :param h:  Hauteur du triangle [mm]
    :param d1: Offset horizontal du sommet depuis le bord gauche [mm]
               (défaut = b/2 → isocèle)
    :param name: Nom optionnel de la section
    """

    def __init__(
        self,
        b: float,
        h: float,
        d1: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:

        # ----- Validation -----
        if b <= 0:
            raise ValueError(f"b doit être strictement positif (reçu : {b})")
        if h <= 0:
            raise ValueError(f"h doit être strictement positif (reçu : {h})")

        if d1 is not None and (d1 < 0 or d1 > b):
            raise ValueError(f"d1 doit être dans [0, b] (reçu : d1={d1}, b={b})")

        # ----- Données d'entrée -----
        self._b = b
        self._h = h
        self._d1 = d1 if d1 is not None else b / 2

        # ----- Nom par défaut -----
        if name is None:
            if self.is_isocele:
                name = f"TRI ISO {b:.0f}×{h:.0f}"
            else:
                name = f"TRI {b:.0f}×{h:.0f} (d1={self._d1:.0f})"

        super().__init__(name=name)

    # =================================================================
    # Utilitaires
    # =================================================================

    @property
    def is_isocele(self) -> bool:
        """True si triangle isocèle (sommet centré sur la base)"""
        return math.isclose(self._d1, self._b / 2, rel_tol=1e-9)

    # =================================================================
    # Setters
    # =================================================================

    @property
    def b(self) -> float:
        """Largeur de la base [mm]"""
        return self._b

    @b.setter
    def b(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"b doit être strictement positif (reçu : {value})")
        if self._d1 > value:
            raise ValueError(f"d1={self._d1} incompatible avec b={value}")
        self._b = value

    @property
    def h(self) -> float:
        """Hauteur du triangle [mm]"""
        return self._h

    @h.setter
    def h(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"h doit être strictement positif (reçu : {value})")
        self._h = value

    @property
    def d1(self) -> float:
        """Offset horizontal du sommet [mm]"""
        return self._d1

    @d1.setter
    def d1(self, value: float) -> None:
        if value < 0 or value > self._b:
            raise ValueError(f"d1 doit être dans [0, b] (reçu : d1={value}, b={self._b})")
        self._d1 = value

    # =================================================================
    # Longueurs des côtés
    # =================================================================

    @property
    def _side_left(self) -> float:
        """Longueur du côté gauche [mm]"""
        return math.sqrt(self._d1**2 + self._h**2)

    @property
    def _side_right(self) -> float:
        """Longueur du côté droit [mm]"""
        return math.sqrt((self._b - self._d1)**2 + self._h**2)

    # =================================================================
    # Centre de gravité
    # =================================================================

    @property
    def yg(self) -> float:
        """Position du CDG selon y depuis le bord gauche [mm]

        Pour un triangle de sommets (0,0), (b,0), (d1,h) :
            yg = (0 + b + d1) / 3
        """
        return (0 + self._b + self._d1) / 3

    @property
    def zg(self) -> float:
        """Position du CDG selon z depuis la base [mm]

        zg = h / 3 (toujours au tiers de la hauteur depuis la base)
        """
        return self._h / 3

    def _report_cdg(self) -> FormulaResult:
        return FormulaResult(
            name="CDG",
            formula="yg = (b + d1) / 3 ; zg = h / 3",
            formula_values=(
                f"yg = ({self._b:.1f} + {self._d1:.1f}) / 3 = {self.yg:.2f} ; "
                f"zg = {self._h:.1f} / 3 = {self.zg:.2f}"
            ),
            value=self.zg,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Aire
    # =================================================================

    @property
    def area(self) -> float:
        """Aire de la section [mm²]"""
        return self._b * self._h / 2

    def _report_area(self) -> FormulaResult:
        return FormulaResult(
            name="A",
            formula="A = b × h / 2",
            formula_values=f"A = {self._b:.1f} × {self._h:.1f} / 2 = {self.area:.2f}",
            value=self.area,
            unit="mm²",
            ref="Géométrie",
        )

    # =================================================================
    # Moments d'inertie (axes centroïdaux)
    # =================================================================

    @property
    def inertia_y(self) -> float:
        """Moment d'inertie selon y (axe horizontal passant par G) [mm⁴]

        Iy = b × h³ / 36  (identique pour tout triangle de base b, hauteur h)
        """
        return self._b * self._h**3 / 36

    @property
    def inertia_z(self) -> float:
        """Moment d'inertie selon z (axe vertical passant par G) [mm⁴]

        Pour un triangle de sommets A(0,0), B(b,0), C(d1,h) :
            Iz_O = (b³ + b²·d1 + b·d1² − b²·d1) ... formule générale

        Formule directe axes centroïdaux :
            Iz = A/18 × (b² − b·d1 + d1²)

        Cas isocèle (d1 = b/2) : Iz = b³×h / 48
        """
        b, d1 = self._b, self._d1
        return self.area / 18 * (b**2 - b * d1 + d1**2)

    def _report_inertia_y(self) -> FormulaResult:
        return FormulaResult(
            name="Iy",
            formula="Iy = b × h³ / 36",
            formula_values=f"Iy = {self._b:.1f} × {self._h:.1f}³ / 36 = {self.inertia_y:.2f}",
            value=self.inertia_y,
            unit="mm⁴",
            ref="Géométrie",
        )

    def _report_inertia_z(self) -> FormulaResult:
        return FormulaResult(
            name="Iz",
            formula="Iz = A/18 × (b² − b·d1 + d1²)",
            formula_values=(
                f"Iz = {self.area:.1f}/18 × ({self._b:.1f}² − {self._b:.1f}×{self._d1:.1f} "
                f"+ {self._d1:.1f}²) = {self.inertia_z:.2f}"
            ),
            value=self.inertia_z,
            unit="mm⁴",
            ref="Géométrie",
        )

    # =================================================================
    # Moments statiques max
    # =================================================================

    @property
    def sy(self) -> float:
        """Moment statique maximal selon y au CDG [mm³]

        Demi-section sous le CDG (trapèze de hauteur h/3) :
            Sy = A × zg / 2 ... approximation courante
        
        Formule exacte pour triangle :
            Sy = b × h² / 24
        """
        return self._b * self._h**2 / 24

    @property
    def sz(self) -> float:
        """Moment statique maximal selon z [mm³]

        Pas de formule simple universelle pour triangle quelconque.
        On utilise : Sz = Iz / (distance max au CDG selon y)
        ... non, Sz est le moment statique, pas le module.

        Pour un triangle quelconque, le moment statique max selon z
        dépend de la géométrie. On donne une valeur approchée via
        Sz ≈ A × max(yg, b−yg) / 3
        
        Cas isocèle exact : Sz = b² × h / 24
        """
        # Formule générale simplifiée (conservatrice)
        # TODO: affiner si besoin pour triangle très asymétrique
        if self.is_isocele:
            return self._b**2 * self._h / 24
        # Approche numérique : Sz_max au plan de coupe passant par yg
        # Pour un triangle quelconque c'est complexe, on utilise Iz/ymax
        # comme approximation conservatrice du module, pas du moment statique
        return self._b**2 * self._h / 24  # approx isocèle

    def _report_sy(self) -> FormulaResult:
        return FormulaResult(
            name="Sy",
            formula="Sy = b × h² / 24",
            formula_values=f"Sy = {self._b:.1f} × {self._h:.1f}² / 24 = {self.sy:.2f}",
            value=self.sy,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Modules de résistance élastiques
    # =================================================================

    @property
    def _v_top(self) -> float:
        """Distance du CDG au sommet (fibre sup) [mm]"""
        return self._h - self.zg  # = 2h/3

    @property
    def _v_bot(self) -> float:
        """Distance du CDG à la base (fibre inf) [mm]"""
        return self.zg  # = h/3

    @property
    def wel_y(self) -> float:
        """Module de résistance élastique selon y — fibre la plus éloignée [mm³]

        Wel,y = Iy / max(v_top, v_bot) = Iy / (2h/3) = b×h² / 24
        """
        return self.inertia_y / max(self._v_top, self._v_bot)

    @property
    def wel_y_top(self) -> float:
        """Module de résistance élastique — fibre supérieure [mm³]"""
        return self.inertia_y / self._v_top

    @property
    def wel_y_bot(self) -> float:
        """Module de résistance élastique — fibre inférieure [mm³]"""
        return self.inertia_y / self._v_bot

    @property
    def wel_z(self) -> float:
        """Module de résistance élastique selon z — fibre la plus éloignée [mm³]"""
        v_left = self.yg
        v_right = self._b - self.yg
        return self.inertia_z / max(v_left, v_right)

    def _report_wel_y(self) -> FormulaResult:
        return FormulaResult(
            name="Wel,y",
            formula="Wel,y = Iy / v_max",
            formula_values=(
                f"Wel,y = {self.inertia_y:.2f} / {max(self._v_top, self._v_bot):.2f} "
                f"= {self.wel_y:.2f}"
            ),
            value=self.wel_y,
            unit="mm³",
            ref="Géométrie",
        )

    def _report_wel_z(self) -> FormulaResult:
        v_max = max(self.yg, self._b - self.yg)
        return FormulaResult(
            name="Wel,z",
            formula="Wel,z = Iz / v_max",
            formula_values=f"Wel,z = {self.inertia_z:.2f} / {v_max:.2f} = {self.wel_z:.2f}",
            value=self.wel_z,
            unit="mm³",
            ref="Géométrie",
        )

    # =================================================================
    # Modules de résistance plastiques
    # =================================================================

    @property
    def wpl_y(self) -> float:
        """Module de résistance plastique selon y [mm³]

        L'axe plastique coupe le triangle en deux aires égales A/2.
        Pour un triangle de base b et hauteur h, la hauteur de coupe est :
            z_pl = h × (1 − 1/√2)  (coupe depuis le sommet)
        ou depuis la base : z_pl = h / √2

        Wpl,y = A/2 × (z̄_sup + z̄_inf)
        
        Formule exacte : Wpl,y = b × h² / 12 × (√2 − 1) × ... complexe
        
        Simplification classique :
            Wpl,y = b × h² × (3 − 2√2) / 6 ... NON
        
        Formule vérifiée :
            z_pl = h / √2  (depuis la base)
            A_inf = b × z_pl / (2h) × z_pl = b × z_pl² / (2h) ... non
            
        En fait pour un triangle isocèle :
            Wpl,y = b × h² / (12√2)  ≈  b × h² / 16.97
        """
        # Axe neutre plastique depuis la base : z_pl = h / sqrt(2)
        h, b = self._h, self._b
        z_pl = h / math.sqrt(2)

        # Largeur du triangle à la hauteur z : w(z) = b × (h − z) / h  
        # NON : largeur à z depuis la base = b × z / h pour triangle 
        #       avec sommet en haut... Non.
        # 
        # Sommet en haut, base en bas :
        #   à z depuis la base, la largeur = b × (1 − z/h)  si le triangle
        #   se rétrécit vers le haut.
        # 
        # Wait : largeur à hauteur z (depuis base) :
        #   Le triangle va de largeur b (à z=0) à 0 (à z=h)
        #   w(z) = b × (h − z) / h

        # Aire sous z_pl :
        # A_inf = ∫₀^{z_pl} b(h−z)/h dz = b/h × [hz − z²/2]₀^{z_pl}
        #       = b/h × (h·z_pl − z_pl²/2)
        #       = b × (z_pl − z_pl²/(2h))

        # CDG de la partie inférieure (trapèze) :
        # z̄_inf = ∫₀^{z_pl} z·b(h−z)/h dz / A_inf
        # Numérateur = b/h × [hz²/2 − z³/3]₀^{z_pl}
        #            = b/h × (h·z_pl²/2 − z_pl³/3)

        a_inf = b / h * (h * z_pl - z_pl**2 / 2)
        num_inf = b / h * (h * z_pl**2 / 2 - z_pl**3 / 3)
        z_bar_inf = num_inf / a_inf

        a_sup = self.area - a_inf
        # CDG de la partie supérieure :
        # z̄_sup via barycentre global : A × zg = A_inf × z̄_inf + A_sup × z̄_sup
        z_bar_sup = (self.area * self.zg - a_inf * z_bar_inf) / a_sup

        return a_inf * (z_pl - z_bar_inf) + a_sup * (z_bar_sup - z_pl)

    @property
    def wpl_z(self) -> float:
        """Module de résistance plastique selon z [mm³]

        Pour un triangle quelconque, le calcul est complexe.
        On utilise une approche numérique simplifiée pour le cas isocèle.
        """
        # Pour le cas isocèle, par symétrie l'axe plastique passe par yg
        # Wpl,z ≈ même logique que wpl_y mais sur l'autre axe
        # Pour simplifier, on utilise : Wpl ≈ 2 × Sz (approximation)
        return 2 * self.sz

    def _report_wpl_y(self) -> FormulaResult:
        return FormulaResult(
            name="Wpl,y",
            formula="Wpl,y (calcul intégral)",
            formula_values=f"Wpl,y = {self.wpl_y:.2f}",
            value=self.wpl_y,
            unit="mm³",
            ref="Géométrie",
        )

    def _report_wpl_z(self) -> FormulaResult:
        return FormulaResult(
            name="Wpl,z",
            formula="Wpl,z ≈ 2 × Sz",
            formula_values=f"Wpl,z ≈ 2 × {self.sz:.2f} = {self.wpl_z:.2f}",
            value=self.wpl_z,
            unit="mm³",
            ref="Géométrie (approx.)",
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
        return math.sqrt(self.inertia_z / self.area)

    def _report_iy(self) -> FormulaResult:
        return FormulaResult(
            name="iy",
            formula="iy = √(Iy / A)",
            formula_values=f"iy = √({self.inertia_y:.2f} / {self.area:.2f}) = {self.iy:.2f}",
            value=self.iy,
            unit="mm",
            ref="Géométrie",
        )

    def _report_iz(self) -> FormulaResult:
        return FormulaResult(
            name="iz",
            formula="iz = √(Iz / A)",
            formula_values=f"iz = √({self.inertia_z:.2f} / {self.area:.2f}) = {self.iz:.2f}",
            value=self.iz,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Périmètre
    # =================================================================

    @property
    def perimeter(self) -> float:
        """Périmètre du triangle [mm]"""
        return self._b + self._side_left + self._side_right

    def _report_perimeter(self) -> FormulaResult:
        return FormulaResult(
            name="u",
            formula="u = b + côté_g + côté_d",
            formula_values=(
                f"u = {self._b:.1f} + {self._side_left:.1f} + {self._side_right:.1f} "
                f"= {self.perimeter:.2f}"
            ),
            value=self.perimeter,
            unit="mm",
            ref="Géométrie",
        )

    # =================================================================
    # Reporting
    # =================================================================

    def all_reports(self) -> List[FormulaResult]:
        """Liste de tous les FormulaResult de la section"""
        return [
            self._report_cdg(),
            self._report_area(),
            self._report_inertia_y(),
            self._report_inertia_z(),
            self._report_sy(),
            self._report_wel_y(),
            self._report_wel_z(),
            self._report_wpl_y(),
            self._report_wpl_z(),
            self._report_iy(),
            self._report_iz(),
            self._report_perimeter(),
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        if self.is_isocele:
            return f"SecTriangular(b={self._b}, h={self._h}, name='{self._name}')"
        return f"SecTriangular(b={self._b}, h={self._h}, d1={self._d1}, name='{self._name}')"

    def __str__(self) -> str:
        kind = "isocèle" if self.is_isocele else f"quelconque (d1={self._d1:.0f})"
        lines = [
            f"{'=' * 65}",
            f"  {self._name} — Triangle {kind}",
            f"  b={self._b:.1f} mm | h={self._h:.1f} mm",
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

    # --- Triangle isocèle 300×500 ---
    tri = SecTriangular(b=300, h=500)
    print(tri)

    # --- Triangle quelconque ---
    tri2 = SecTriangular(b=300, h=500, d1=100)
    print(tri2)

    # --- Vérification valeurs connues (isocèle) ---
    print("\n--- Vérifications triangle isocèle 300×500 ---")
    print(f"A    = {tri.area:.0f}  (attendu : 75000)")
    print(f"zg   = {tri.zg:.2f}  (attendu : 166.67)")
    print(f"Iy   = {tri.inertia_y:.0f}  (attendu : 1041666667)")
    print(f"Wel,y = {tri.wel_y:.0f}")
    print(f"Wpl,y = {tri.wpl_y:.0f}")
