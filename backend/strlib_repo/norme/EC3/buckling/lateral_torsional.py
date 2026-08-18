#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC3-1-1 — §6.3.2 — Vérification au déversement.

Classe ``LateralTorsionalBuckling`` et fonctions standalone.
Deux méthodes : générale (§6.3.2.2) et profilés laminés (§6.3.2.3).
Inclut le calcul du moment critique Mcr (NCCI SN003).
"""

__all__ = [
    "LateralTorsionalBuckling",
    "get_C_coefficients",
    "get_kc",
    "mcr",
    "mb_rd",
]

import math
from typing import TypeVar, Optional, Tuple

from core.formula import FormulaResult, FormulaCollection
from norme.EC3.buckling.buckling_curves import (
    get_lt_buckling_curve,
    get_imperfection_factor,
    chi_LT as _chi_LT,
    phi_LT as _phi_LT,
)

section = TypeVar("section")
material = TypeVar("material")


# ===================================================================
#  Helpers — Coefficients C1, C2, C3 et kc
# ===================================================================

def get_C_coefficients(
    moment_diagram: str,
    psi: float = 0.0,
    mu: float = 0.0,
) -> Tuple[float, float, float]:
    """
    Retourne (C1, C2, C3) selon le type de diagramme de moment.

    :param moment_diagram:
        - 'uniform'    → moment constant
        - 'linear'     → moment linéaire (ψ = M_min/M_max)
        - 'parabolic'  → charge répartie (appuis fourche)
        - 'point_load' → charge ponctuelle à mi-portée
    :param psi: Rapport des moments d'extrémité M_min/M_max (pour 'linear')
    :param mu: Paramètre complémentaire (réservé)
    :return: (C1, C2, C3)

    Ref: NCCI SN003 / Annexe F (EN 1993-1-1)
    """
    diag = moment_diagram.lower().strip()

    if diag == "uniform":
        return (1.0, 0.0, 1.0)

    elif diag == "linear":
        # Approximation courante C1 pour moment linéaire
        # C1 = 1.88 - 1.40·ψ + 0.52·ψ²  ≤ 2.70   (NCCI SN003)
        c1 = 1.88 - 1.40 * psi + 0.52 * psi ** 2
        c1 = min(c1, 2.70)
        return (c1, 0.0, 1.0)

    elif diag == "parabolic":
        # Charge répartie, appuis fourche, moment parabolique
        return (1.127, 0.454, 0.525)

    elif diag == "point_load":
        # Charge ponctuelle à mi-portée
        return (1.348, 0.630, 1.0)

    else:
        raise ValueError(
            f"Diagramme de moment '{moment_diagram}' non reconnu. "
            f"Valeurs admises : 'uniform', 'linear', 'parabolic', 'point_load'."
        )


def get_kc(moment_diagram: str, psi: float = 0.0) -> float:
    """
    Facteur de correction kc selon le Tableau 6.6.

    :param moment_diagram: Type de diagramme ('uniform', 'linear',
                            'parabolic', 'point_load')
    :param psi: Rapport des moments d'extrémité (pour 'linear')
    :return: kc

    Ref: EC3-1-1 — Tableau 6.6
    """
    diag = moment_diagram.lower().strip()

    if diag == "uniform":
        return 1.0
    elif diag == "linear":
        # kc = 1 / C1  approximation usuelle (Tableau 6.6, ligne ψ)
        c1, _, _ = get_C_coefficients("linear", psi)
        return 1.0 / math.sqrt(c1) if c1 > 0 else 1.0
    elif diag == "parabolic":
        return 0.94
    elif diag == "point_load":
        return 0.90
    else:
        raise ValueError(
            f"Diagramme '{moment_diagram}' non reconnu pour kc."
        )


# ===================================================================
#  Calcul standalone du moment critique Mcr
# ===================================================================

def mcr(
    E: float,
    G: float,
    Iz: float,
    It: float,
    Iw: float,
    L: float,
    C1: float = 1.0,
    C2: float = 0.0,
    k: float = 1.0,
    kw: float = 1.0,
    za: float = 0.0,
) -> float:
    """
    Moment critique élastique de déversement Mcr.

    Mcr = C1 · (π²·E·Iz / (k·L)²) ·
          [√( (kw/k)²·(Iw/Iz) + (k·L)²·G·It/(π²·E·Iz) + (C2·za)² ) − C2·za]

    :param E: Module de Young [MPa]
    :param G: Module de cisaillement [MPa]
    :param Iz: Inertie flexion faible axe [mm⁴]
    :param It: Inertie de torsion St-Venant [mm⁴]
    :param Iw: Inertie de gauchissement [mm⁶]
    :param L: Longueur de déversement [mm]
    :param C1, C2: Coefficients de moment
    :param k: Facteur de longueur effective (rotation en plan)
    :param kw: Facteur de longueur effective (gauchissement)
    :param za: Coordonnée du point d'application de la charge p/r au
               centre de cisaillement [mm] (positif = au-dessus)
    :return: Mcr [N·mm]

    Ref: NCCI SN003
    """
    if L == 0 or Iz == 0:
        return float("inf")

    kL = k * L
    pi2_E_Iz = math.pi ** 2 * E * Iz
    term1 = (kw / k) ** 2 * (Iw / Iz)
    term2 = kL ** 2 * G * It / pi2_E_Iz
    term3 = (C2 * za) ** 2

    inner = term1 + term2 + term3
    if inner < 0:
        inner = 0.0

    result = C1 * (pi2_E_Iz / kL ** 2) * (math.sqrt(inner) - C2 * za)
    return max(result, 0.0)


def mb_rd(
    Wy: float,
    fy: float,
    Mcr: float,
    curve: str,
    method: str = "general",
    gamma_m1: float = 1.0,
    kc: float = 1.0,
) -> float:
    """
    Calcul rapide de Mb,Rd.

    :param Wy: Module de flexion (Wpl,y ou Wel,y) [mm³]
    :param fy: Limite d'élasticité [MPa]
    :param Mcr: Moment critique [N·mm]
    :param curve: Courbe de déversement
    :param method: 'general' ou 'rolled'
    :param gamma_m1: Coefficient de sécurité γM1
    :param kc: Facteur kc pour le calcul de f (méthode rolled)
    :return: Mb,Rd [N·mm]
    """
    if Mcr <= 0:
        return 0.0
    lam_LT = math.sqrt(Wy * fy / Mcr)

    f = 1.0
    if method.lower() == "rolled":
        f = 1.0 - 0.5 * (1.0 - kc) * (1.0 - 2.0 * (lam_LT - 0.8) ** 2)
        f = min(f, 1.0)
        f = max(f, 0.5)  # Borne basse de sécurité

    x_LT = _chi_LT(lam_LT, curve, method, f)
    return x_LT * Wy * fy / gamma_m1


# ===================================================================
#  Classe LateralTorsionalBuckling
# ===================================================================

class LateralTorsionalBuckling:
    """
    Vérification au déversement d'une poutre fléchie selon EC3-1-1 §6.3.2.

    Méthode générale (§6.3.2.2) ou profilés laminés (§6.3.2.3).
    """

    def __init__(
        self,
        Med_y: float,
        mat: Optional[material] = None,
        sec: Optional[section] = None,
        L: float = 0.0,
        Lcr_LT: Optional[float] = None,
        method: str = "general",
        curve_LT: Optional[str] = None,
        section_class: int = 1,
        C1: float = 1.0,
        C2: float = 0.0,
        C3: float = 1.0,
        k: float = 1.0,
        kw: float = 1.0,
        za: float = 0.0,
        moment_diagram: Optional[str] = None,
        psi: float = 0.0,
        **kwargs,
    ) -> None:
        """
        :param Med_y: Moment fléchissant de calcul My,Ed [N·mm]
        :param mat: Instance Material (optionnel)
        :param sec: Instance Section (optionnel)
        :param L: Longueur de la poutre [mm]
        :param Lcr_LT: Longueur de déversement [mm] (défaut = L)
        :param method: 'general' (§6.3.2.2) ou 'rolled' (§6.3.2.3)
        :param curve_LT: Courbe de déversement (si None → auto)
        :param section_class: Classe de section (1, 2 ou 3)
        :param C1, C2, C3: Coefficients de moment
        :param k, kw: Facteurs de longueur effective
        :param za: Coordonnée du point d'application de la charge [mm]
        :param moment_diagram: Type de diagramme pour calcul auto de C1/C2/C3 et kc
        :param psi: Rapport des moments d'extrémité (si moment_diagram='linear')
        :param kwargs: fy, E, G, Iy, Iz, It, Iw, Wpl_y, Wel_y, h, b, tf,
                        section_type, gamma_m0, gamma_m1
        """
        self.__med_y = abs(Med_y)
        self.__section_class = section_class
        self.__method = method.lower().strip()

        # --- Matériau ---
        self.__fy = mat.fy if mat else kwargs.get("fy", 0.0)
        self.__E = mat.E if mat else kwargs.get("E", 210000.0)
        self.__G = mat.G if mat else kwargs.get("G", 81000.0)
        self.__gamma_m0 = mat.gamma_m0 if mat else kwargs.get("gamma_m0", 1.0)
        self.__gamma_m1 = mat.gamma_m1 if mat else kwargs.get("gamma_m1", 1.0)

        # --- Section ---
        self.__Iy = sec.Iy if sec else kwargs.get("Iy", 0.0)
        self.__Iz = sec.Iz if sec else kwargs.get("Iz", 0.0)
        self.__It = sec.It if sec else kwargs.get("It", 0.0)
        self.__Iw = sec.Iw if sec else kwargs.get("Iw", 0.0)
        self.__Wpl_y = sec.Wpl_y if sec else kwargs.get("Wpl_y", 0.0)
        self.__Wel_y = sec.Wel_y if sec else kwargs.get("Wel_y", 0.0)
        self.__h = sec.h if sec else kwargs.get("h", 0.0)
        self.__b = sec.b if sec else kwargs.get("b", 0.0)
        self.__tf = sec.tf if sec else kwargs.get("tf", 0.0)
        sec_type = sec.section_type if sec else kwargs.get("section_type", "I")
        self.__section_type = sec_type.upper()

        # --- Longueurs ---
        self.__L = L if L > 0 else kwargs.get("L", 0.0)
        self.__Lcr_LT = Lcr_LT if Lcr_LT is not None else self.__L
        self.__k = k
        self.__kw = kw
        self.__za = za

        # --- Coefficients de moment ---
        self.__psi = psi
        self.__moment_diagram = moment_diagram

        if moment_diagram is not None:
            c1_auto, c2_auto, c3_auto = get_C_coefficients(moment_diagram, psi)
            self.__C1 = c1_auto
            self.__C2 = c2_auto
            self.__C3 = c3_auto
            self.__kc = get_kc(moment_diagram, psi)
        else:
            self.__C1 = C1
            self.__C2 = C2
            self.__C3 = C3
            self.__kc = kwargs.get("kc", 1.0)

        # --- Courbe de déversement ---
        if curve_LT is not None:
            self.__curve_LT = curve_LT
        else:
            try:
                self.__curve_LT = get_lt_buckling_curve(
                    self.__section_type, self.__h, self.__b, self.__method,
                )
            except ValueError:
                self.__curve_LT = "c"

    # ------------------------------------------------------------------
    # Module de flexion approprié selon la classe de section
    # ------------------------------------------------------------------

    @property
    def Wy(self) -> float:
        """Module de flexion Wy selon la classe de section [mm³].
        Classe 1, 2 → Wpl,y ; Classe 3 → Wel,y."""
        if self.__section_class <= 2:
            return self.__Wpl_y
        return self.__Wel_y

    # ------------------------------------------------------------------
    # Propriétés de calcul
    # ------------------------------------------------------------------

    @property
    def med_y(self) -> float:
        """Moment fléchissant de calcul My,Ed [N·mm]."""
        return self.__med_y

    @property
    def mcr(self) -> float:
        """Moment critique élastique de déversement Mcr [N·mm].
        Ref: NCCI SN003"""
        return mcr(
            self.__E, self.__G, self.__Iz, self.__It, self.__Iw,
            self.__Lcr_LT, self.__C1, self.__C2,
            self.__k, self.__kw, self.__za,
        )

    @property
    def lambda_bar_LT(self) -> float:
        """λ̄_LT = √(Wy·fy / Mcr)  — Élancement réduit de déversement.
        Ref: EC3-1-1 — §6.3.2.2 (1)"""
        m = self.mcr
        if m <= 0 or m == float("inf"):
            return 0.0
        return math.sqrt(self.Wy * self.__fy / m)

    @property
    def f(self) -> float:
        """Facteur de correction f (§6.3.2.3 (2)).
        f = 1 − 0.5·(1 − kc)·[1 − 2·(λ̄_LT − 0.8)²]  ∈ [0.5 ; 1.0]
        Pour méthode générale → f = 1.0."""
        if self.__method == "general":
            return 1.0
        lam = self.lambda_bar_LT
        val = 1.0 - 0.5 * (1.0 - self.__kc) * (1.0 - 2.0 * (lam - 0.8) ** 2)
        return max(0.5, min(val, 1.0))

    @property
    def chi_LT(self) -> float:
        """χ_LT — Coefficient de réduction pour le déversement.
        Ref: EC3-1-1 — §6.3.2.2 / §6.3.2.3"""
        return _chi_LT(
            self.lambda_bar_LT,
            self.__curve_LT,
            self.__method,
            self.f,
        )

    @property
    def mb_rd(self) -> float:
        """Mb,Rd = χ_LT · Wy · fy / γM1 [N·mm].
        Ref: EC3-1-1 — §6.3.2.1 (3)"""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.chi_LT * self.Wy * self.__fy / self.__gamma_m1

    @property
    def verif(self) -> float:
        """Taux de travail Med,y / Mb,Rd."""
        if self.mb_rd == 0:
            return float("inf")
        return round(self.__med_y / self.mb_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si la vérification est satisfaite."""
        return self.verif <= 1.0

    # ------------------------------------------------------------------
    # Méthodes get_xxx (FormulaResult)
    # ------------------------------------------------------------------

    def get_mcr(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mcr."""
        r = self.mcr
        fv = ""
        if with_values:
            fv = (
                f"Mcr (C1={self.__C1:.3f}, C2={self.__C2:.3f}, "
                f"L={self.__Lcr_LT:.0f}, Iz={self.__Iz:.0f}, "
                f"It={self.__It:.0f}, Iw={self.__Iw:.0f}) = {r:.2f} N·mm"
            )
        return FormulaResult(
            name="Mcr",
            formula=(
                "Mcr = C1·(π²·E·Iz/(k·L)²)·"
                "[√((kw/k)²·Iw/Iz + (k·L)²·G·It/(π²·E·Iz) + (C2·za)²) − C2·za]"
            ),
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="NCCI SN003",
        )

    def get_lambda_bar_LT(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour λ̄_LT."""
        r = self.lambda_bar_LT
        fv = ""
        if with_values:
            fv = (
                f"λ̄_LT = √({self.Wy:.2f}×{self.__fy:.2f} / "
                f"{self.mcr:.2f}) = {r:.4f}"
            )
        return FormulaResult(
            name="λ̄_LT",
            formula="λ̄_LT = √(Wy·fy / Mcr)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.2.2 (1)",
        )

    def get_chi_LT(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour χ_LT."""
        r = self.chi_LT
        alpha_lt = get_imperfection_factor(self.__curve_LT)
        fv = ""
        if with_values:
            method_label = "générale" if self.__method == "general" else "profilés laminés"
            fv = (
                f"Méthode {method_label}, courbe '{self.__curve_LT}' "
                f"→ α_LT = {alpha_lt:.2f}, λ̄_LT = {self.lambda_bar_LT:.4f}"
            )
            if self.__method == "rolled":
                fv += f", f = {self.f:.4f}"
            fv += f" → χ_LT = {r:.4f}"
        return FormulaResult(
            name="χ_LT",
            formula="χ_LT = 1 / (Φ_LT + √(Φ_LT² − β·λ̄_LT²))  ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref=f"EC3-1-1 — §6.3.2.{'2' if self.__method == 'general' else '3'}",
        )

    def get_mb_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mb,Rd."""
        r = self.mb_rd
        fv = ""
        if with_values:
            fv = (
                f"Mb,Rd = {self.chi_LT:.4f}×{self.Wy:.2f}×"
                f"{self.__fy:.2f} / {self.__gamma_m1} = {r:.2f} N·mm"
            )
        return FormulaResult(
            name="Mb,Rd",
            formula="Mb,Rd = χ_LT · Wy · fy / γM1",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.3.2.1 (3)",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification Med,y / Mb,Rd ≤ 1.0."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"Med,y / Mb,Rd = {self.__med_y:.2f} / {self.mb_rd:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="Med,y/Mb,Rd",
            formula="Med,y / Mb,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.2.1 (1)",
            is_check=True,
        )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes du calcul
        de déversement.
        """
        fc = FormulaCollection(
            title="Vérification au déversement",
            ref=f"EC3-1-1 — §6.3.2 (méthode {'générale' if self.__method == 'general' else 'profilés laminés'})",
        )
        fc.add(self.get_mcr(with_values=with_values))
        fc.add(self.get_lambda_bar_LT(with_values=with_values))
        fc.add(self.get_chi_LT(with_values=with_values))
        fc.add(self.get_mb_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"LateralTorsionalBuckling(Med,y={self.__med_y:.2f}, "
            f"Mb,Rd={self.mb_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ===================================================================
#  Tests
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST — lateral_torsional.py")
    print("  IPE 300, S235, L = 6 m, charge répartie, Med_y = 80 kN·m")
    print("=" * 60)

    # Propriétés IPE 300
    _h = 300.0
    _b = 150.0
    _tf = 10.7
    _tw = 7.1
    _Iy = 8356e4       # mm⁴
    _Iz = 603.8e4       # mm⁴
    _It = 20.1e4        # mm⁴
    _Iw = 126.0e9       # mm⁶
    _Wpl_y = 628.4e3    # mm³
    _Wel_y = 557.1e3    # mm³
    _A = 5381.0         # mm²

    Med = 80e6  # N·mm

    # --- Méthode générale ---
    print("\n--- Méthode générale (§6.3.2.2) ---")
    ltb_gen = LateralTorsionalBuckling(
        Med_y=Med,
        fy=235.0, E=210000.0, G=81000.0,
        Iy=_Iy, Iz=_Iz, It=_It, Iw=_Iw,
        Wpl_y=_Wpl_y, Wel_y=_Wel_y,
        h=_h, b=_b, tf=_tf,
        section_type="I",
        L=6000.0,
        method="general",
        moment_diagram="parabolic",
        gamma_m1=1.0,
        section_class=1,
    )
    print(ltb_gen)
    print(f"  Mcr     = {ltb_gen.mcr / 1e6:.2f} kN·m")
    print(f"  λ̄_LT   = {ltb_gen.lambda_bar_LT:.4f}")
    print(f"  χ_LT   = {ltb_gen.chi_LT:.4f}")
    print(f"  Mb,Rd   = {ltb_gen.mb_rd / 1e6:.2f} kN·m")
    print(f"  Taux    = {ltb_gen.verif:.4f}  →  {'OK ✓' if ltb_gen.is_ok else 'NON VÉRIFIÉ ✗'}")

    # --- Méthode profilés laminés ---
    print("\n--- Méthode profilés laminés (§6.3.2.3) ---")
    ltb_rolled = LateralTorsionalBuckling(
        Med_y=Med,
        fy=235.0, E=210000.0, G=81000.0,
        Iy=_Iy, Iz=_Iz, It=_It, Iw=_Iw,
        Wpl_y=_Wpl_y, Wel_y=_Wel_y,
        h=_h, b=_b, tf=_tf,
        section_type="I",
        L=6000.0,
        method="rolled",
        moment_diagram="parabolic",
        gamma_m1=1.0,
        section_class=1,
    )
    print(ltb_rolled)
    print(f"  Mcr     = {ltb_rolled.mcr / 1e6:.2f} kN·m")
    print(f"  λ̄_LT   = {ltb_rolled.lambda_bar_LT:.4f}")
    print(f"  f       = {ltb_rolled.f:.4f}")
    print(f"  χ_LT   = {ltb_rolled.chi_LT:.4f}")
    print(f"  Mb,Rd   = {ltb_rolled.mb_rd / 1e6:.2f} kN·m")
    print(f"  Taux    = {ltb_rolled.verif:.4f}  →  {'OK ✓' if ltb_rolled.is_ok else 'NON VÉRIFIÉ ✗'}")

    # --- Report ---
    print("\n--- Report (méthode générale) ---")
    rpt = ltb_gen.report(with_values=True)
    print(rpt)
