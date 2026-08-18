#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC3-1-1 — §6.3.1 — Vérification au flambement par flexion.

Classe ``FlexuralBuckling`` et fonctions standalone.
"""

__all__ = [
    "FlexuralBuckling",
    "nb_rd",
    "ncr",
    "lambda_bar",
]

import math
from typing import TypeVar, Optional

from core.formula import FormulaResult, FormulaCollection
from norme.EC3.buckling.buckling_curves import (
    get_buckling_curve,
    get_imperfection_factor,
    chi as _chi,
)

section = TypeVar("section")
material = TypeVar("material")


class FlexuralBuckling:
    """
    Vérification au flambement par flexion d'une barre comprimée
    selon EC3-1-1 §6.3.1.

    Couvre les deux axes principaux (y-y et z-z).
    Classes de section 1, 2 ou 3 (classe 4 non couverte ici).
    """

    def __init__(
        self,
        Ned: float,
        mat: Optional[material] = None,
        sec: Optional[section] = None,
        Lcr_y: Optional[float] = None,
        Lcr_z: Optional[float] = None,
        curve_y: Optional[str] = None,
        curve_z: Optional[str] = None,
        section_class: int = 1,
        **kwargs,
    ) -> None:
        """
        :param Ned: Effort normal de compression de calcul [N] (stocké en |Ned|)
        :param mat: Instance Material (optionnel)
        :param sec: Instance Section (optionnel)
        :param Lcr_y: Longueur de flambement axe y [mm] (défaut = L)
        :param Lcr_z: Longueur de flambement axe z [mm] (défaut = L)
        :param curve_y: Courbe de flambement axe y (si None → auto)
        :param curve_z: Courbe de flambement axe z (si None → auto)
        :param section_class: Classe de section (1, 2 ou 3)
        :param kwargs: fy, E, A, Iy, Iz, h, b, tf, tw,
                        section_type, fabrication, gamma_m0, gamma_m1, L
        """
        self.__ned = abs(Ned)
        self.__section_class = section_class

        # --- Matériau ---
        self.__fy = mat.fy if mat else kwargs.get("fy", 0.0)
        self.__E = mat.E if mat else kwargs.get("E", 210000.0)
        self.__gamma_m0 = mat.gamma_m0 if mat else kwargs.get("gamma_m0", 1.0)
        self.__gamma_m1 = mat.gamma_m1 if mat else kwargs.get("gamma_m1", 1.0)

        # --- Section ---
        self.__A = sec.A if sec else kwargs.get("A", 0.0)
        self.__Iy = sec.Iy if sec else kwargs.get("Iy", 0.0)
        self.__Iz = sec.Iz if sec else kwargs.get("Iz", 0.0)
        self.__h = sec.h if sec else kwargs.get("h", 0.0)
        self.__b = sec.b if sec else kwargs.get("b", 0.0)
        self.__tf = sec.tf if sec else kwargs.get("tf", 0.0)
        self.__tw = sec.tw if sec else kwargs.get("tw", 0.0)
        sec_type = sec.section_type if sec else kwargs.get("section_type", "I")
        self.__section_type = sec_type.upper()
        self.__fabrication = kwargs.get("fabrication", "rolled").lower()

        # --- Longueurs de flambement ---
        L = kwargs.get("L", 0.0)
        self.__Lcr_y = Lcr_y if Lcr_y is not None else L
        self.__Lcr_z = Lcr_z if Lcr_z is not None else L

        # --- Courbes ---
        if curve_y is not None:
            self.__curve_y = curve_y
        else:
            try:
                self.__curve_y = get_buckling_curve(
                    self.__section_type, self.__fabrication, "y",
                    self.__h, self.__b, self.__tf,
                )
            except ValueError:
                self.__curve_y = "b"

        if curve_z is not None:
            self.__curve_z = curve_z
        else:
            try:
                self.__curve_z = get_buckling_curve(
                    self.__section_type, self.__fabrication, "z",
                    self.__h, self.__b, self.__tf,
                )
            except ValueError:
                self.__curve_z = "c"

    # ------------------------------------------------------------------
    # Propriétés de calcul — axe y
    # ------------------------------------------------------------------

    @property
    def ned(self) -> float:
        """Effort de compression de calcul [N]."""
        return self.__ned

    @property
    def ncr_y(self) -> float:
        """Ncr,y = π²·E·Iy / Lcr,y²  — Charge critique d'Euler axe y [N].
        Ref: EC3-1-1 — §6.3.1.2"""
        if self.__Lcr_y == 0:
            return float("inf")
        return math.pi ** 2 * self.__E * self.__Iy / self.__Lcr_y ** 2

    @property
    def ncr_z(self) -> float:
        """Ncr,z = π²·E·Iz / Lcr,z²  — Charge critique d'Euler axe z [N]."""
        if self.__Lcr_z == 0:
            return float("inf")
        return math.pi ** 2 * self.__E * self.__Iz / self.__Lcr_z ** 2

    @property
    def lambda_bar_y(self) -> float:
        """λ̄_y = √(A·fy / Ncr,y)  — Élancement réduit axe y.
        Ref: EC3-1-1 — §6.3.1.2 (1)"""
        ncr = self.ncr_y
        if ncr <= 0 or ncr == float("inf"):
            return 0.0
        return math.sqrt(self.__A * self.__fy / ncr)

    @property
    def lambda_bar_z(self) -> float:
        """λ̄_z = √(A·fy / Ncr,z)  — Élancement réduit axe z."""
        ncr = self.ncr_z
        if ncr <= 0 or ncr == float("inf"):
            return 0.0
        return math.sqrt(self.__A * self.__fy / ncr)

    @property
    def chi_y(self) -> float:
        """χ_y — coefficient de réduction axe y.
        Ref: EC3-1-1 — §6.3.1.2 (1)"""
        return _chi(self.lambda_bar_y, self.__curve_y)

    @property
    def chi_z(self) -> float:
        """χ_z — coefficient de réduction axe z."""
        return _chi(self.lambda_bar_z, self.__curve_z)

    @property
    def nb_rd_y(self) -> float:
        """Nb,Rd,y = χ_y · A · fy / γM1 [N].
        Ref: EC3-1-1 — §6.3.1.1 (3)"""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.chi_y * self.__A * self.__fy / self.__gamma_m1

    @property
    def nb_rd_z(self) -> float:
        """Nb,Rd,z = χ_z · A · fy / γM1 [N]."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.chi_z * self.__A * self.__fy / self.__gamma_m1

    @property
    def nb_rd(self) -> float:
        """Nb,Rd = min(Nb,Rd,y ; Nb,Rd,z) [N]."""
        return min(self.nb_rd_y, self.nb_rd_z)

    @property
    def verif(self) -> float:
        """Taux de travail Ned / Nb,Rd."""
        if self.nb_rd == 0:
            return float("inf")
        return round(self.__ned / self.nb_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si la vérification est satisfaite."""
        return self.verif <= 1.0

    # ------------------------------------------------------------------
    # Méthodes get_xxx  (FormulaResult)
    # ------------------------------------------------------------------

    def get_ncr_y(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Ncr,y."""
        r = self.ncr_y
        fv = ""
        if with_values:
            fv = (
                f"Ncr,y = π²×{self.__E:.0f}×{self.__Iy:.0f} / "
                f"{self.__Lcr_y:.0f}² = {r:.2f} N"
            )
        return FormulaResult(
            name="Ncr,y",
            formula="Ncr,y = π²·E·Iy / Lcr,y²",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.3.1.2",
        )

    def get_ncr_z(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Ncr,z."""
        r = self.ncr_z
        fv = ""
        if with_values:
            fv = (
                f"Ncr,z = π²×{self.__E:.0f}×{self.__Iz:.0f} / "
                f"{self.__Lcr_z:.0f}² = {r:.2f} N"
            )
        return FormulaResult(
            name="Ncr,z",
            formula="Ncr,z = π²·E·Iz / Lcr,z²",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.3.1.2",
        )

    def get_lambda_bar_y(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour λ̄_y."""
        r = self.lambda_bar_y
        fv = ""
        if with_values:
            fv = (
                f"λ̄_y = √({self.__A:.2f}×{self.__fy:.2f} / "
                f"{self.ncr_y:.2f}) = {r:.4f}"
            )
        return FormulaResult(
            name="λ̄_y",
            formula="λ̄_y = √(A·fy / Ncr,y)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.1.2 (1)",
        )

    def get_lambda_bar_z(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour λ̄_z."""
        r = self.lambda_bar_z
        fv = ""
        if with_values:
            fv = (
                f"λ̄_z = √({self.__A:.2f}×{self.__fy:.2f} / "
                f"{self.ncr_z:.2f}) = {r:.4f}"
            )
        return FormulaResult(
            name="λ̄_z",
            formula="λ̄_z = √(A·fy / Ncr,z)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.1.2 (1)",
        )

    def get_chi_y(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour χ_y."""
        r = self.chi_y
        alpha = get_imperfection_factor(self.__curve_y)
        fv = ""
        if with_values:
            fv = (
                f"Courbe '{self.__curve_y}' → α = {alpha:.2f}, "
                f"λ̄_y = {self.lambda_bar_y:.4f} → χ_y = {r:.4f}"
            )
        return FormulaResult(
            name="χ_y",
            formula="χ = 1 / (Φ + √(Φ² − λ̄²))  ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.1.2 (1)",
        )

    def get_chi_z(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour χ_z."""
        r = self.chi_z
        alpha = get_imperfection_factor(self.__curve_z)
        fv = ""
        if with_values:
            fv = (
                f"Courbe '{self.__curve_z}' → α = {alpha:.2f}, "
                f"λ̄_z = {self.lambda_bar_z:.4f} → χ_z = {r:.4f}"
            )
        return FormulaResult(
            name="χ_z",
            formula="χ = 1 / (Φ + √(Φ² − λ̄²))  ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.1.2 (1)",
        )

    def get_nb_rd_y(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Nb,Rd,y."""
        r = self.nb_rd_y
        fv = ""
        if with_values:
            fv = (
                f"Nb,Rd,y = {self.chi_y:.4f}×{self.__A:.2f}×"
                f"{self.__fy:.2f} / {self.__gamma_m1} = {r:.2f} N"
            )
        return FormulaResult(
            name="Nb,Rd,y",
            formula="Nb,Rd,y = χ_y · A · fy / γM1",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.3.1.1 (3)",
        )

    def get_nb_rd_z(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Nb,Rd,z."""
        r = self.nb_rd_z
        fv = ""
        if with_values:
            fv = (
                f"Nb,Rd,z = {self.chi_z:.4f}×{self.__A:.2f}×"
                f"{self.__fy:.2f} / {self.__gamma_m1} = {r:.2f} N"
            )
        return FormulaResult(
            name="Nb,Rd,z",
            formula="Nb,Rd,z = χ_z · A · fy / γM1",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.3.1.1 (3)",
        )

    def get_nb_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Nb,Rd."""
        r = self.nb_rd
        fv = ""
        if with_values:
            fv = (
                f"Nb,Rd = min({self.nb_rd_y:.2f} ; {self.nb_rd_z:.2f}) "
                f"= {r:.2f} N"
            )
        return FormulaResult(
            name="Nb,Rd",
            formula="Nb,Rd = min(Nb,Rd,y ; Nb,Rd,z)",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.3.1.1 (3)",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification Ned / Nb,Rd ≤ 1.0."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"Ned / Nb,Rd = {self.__ned:.2f} / {self.nb_rd:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="Ned/Nb,Rd",
            formula="Ned / Nb,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.1.1 (1)",
            is_check=True,
        )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes du calcul
        de flambement par flexion.
        """
        fc = FormulaCollection(
            title="Vérification au flambement par flexion",
            ref="EC3-1-1 — §6.3.1",
        )
        fc.add(self.get_ncr_y(with_values=with_values))
        fc.add(self.get_lambda_bar_y(with_values=with_values))
        fc.add(self.get_chi_y(with_values=with_values))
        fc.add(self.get_nb_rd_y(with_values=with_values))
        fc.add(self.get_ncr_z(with_values=with_values))
        fc.add(self.get_lambda_bar_z(with_values=with_values))
        fc.add(self.get_chi_z(with_values=with_values))
        fc.add(self.get_nb_rd_z(with_values=with_values))
        fc.add(self.get_nb_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"FlexuralBuckling(Ned={self.__ned:.2f}, "
            f"Nb,Rd={self.nb_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ===================================================================
#  Fonctions standalone
# ===================================================================

def ncr(E: float, I: float, Lcr: float) -> float:
    """
    Charge critique d'Euler.

    :param E: Module de Young [MPa]
    :param I: Inertie [mm⁴]
    :param Lcr: Longueur de flambement [mm]
    :return: Ncr [N]
    """
    if Lcr == 0:
        return float("inf")
    return math.pi ** 2 * E * I / Lcr ** 2


def lambda_bar(A: float, fy: float, Ncr: float) -> float:
    """
    Élancement réduit.

    :param A: Section brute [mm²]
    :param fy: Limite d'élasticité [MPa]
    :param Ncr: Charge critique d'Euler [N]
    :return: λ̄
    """
    if Ncr <= 0:
        return 0.0
    return math.sqrt(A * fy / Ncr)


def nb_rd(
    A: float,
    fy: float,
    Lcr: float,
    I: float,
    E: float,
    curve: str,
    gamma_m1: float = 1.0,
) -> float:
    """
    Calcul rapide de Nb,Rd sans instancier la classe.

    :param A: Section brute [mm²]
    :param fy: Limite d'élasticité [MPa]
    :param Lcr: Longueur de flambement [mm]
    :param I: Inertie selon l'axe considéré [mm⁴]
    :param E: Module de Young [MPa]
    :param curve: Courbe de flambement
    :param gamma_m1: Coefficient de sécurité γM1
    :return: Nb,Rd [N]
    """
    n_cr = ncr(E, I, Lcr)
    lam = lambda_bar(A, fy, n_cr)
    x = _chi(lam, curve)
    return x * A * fy / gamma_m1


# ===================================================================
#  Tests
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST — flexural_buckling.py")
    print("  IPE 300, S235, L = 5 m, bi-articulé, Ned = 500 kN")
    print("=" * 60)

    fb = FlexuralBuckling(
        Ned=500e3,
        fy=235.0,
        E=210000.0,
        A=5381.0,
        Iy=8356e4,
        Iz=603.8e4,
        h=300.0,
        b=150.0,
        tf=10.7,
        tw=7.1,
        section_type="I",
        fabrication="rolled",
        L=5000.0,
        gamma_m1=1.0,
        section_class=1,
    )

    print(f"\n{fb}")
    print(f"\nNcr,y = {fb.ncr_y / 1e3:.1f} kN")
    print(f"Ncr,z = {fb.ncr_z / 1e3:.1f} kN")
    print(f"λ̄_y   = {fb.lambda_bar_y:.4f}")
    print(f"λ̄_z   = {fb.lambda_bar_z:.4f}")
    print(f"χ_y   = {fb.chi_y:.4f}")
    print(f"χ_z   = {fb.chi_z:.4f}")
    print(f"Nb,Rd,y = {fb.nb_rd_y / 1e3:.1f} kN")
    print(f"Nb,Rd,z = {fb.nb_rd_z / 1e3:.1f} kN")
    print(f"Nb,Rd   = {fb.nb_rd / 1e3:.1f} kN")
    print(f"Taux    = {fb.verif:.4f}  →  {'OK ✓' if fb.is_ok else 'NON VÉRIFIÉ ✗'}")

    rpt = fb.report(with_values=True)
    print(f"\n--- Report ---")
    print(rpt)
