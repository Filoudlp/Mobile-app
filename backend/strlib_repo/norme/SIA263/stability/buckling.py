#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Stabilité des barres — SIA 263:2013, chiffre 4.5.

Vérifications unitaires indépendantes (même principe que
``norme.EC3.buckling.*``).

§4.5.1 — Flambage
    N_K,Rd = χ_K·A·fy / γM1                                      (7)
    χ_K = 1/(Φ_K + √(Φ_K² − λ̄_K²))  ≤ 1,0                        (8)
    Φ_K = 0,5·[1 + α_K·(λ̄_K − 0,2) + λ̄_K²]
    λ̄_K = λ_K/λ_E ,  λ_K = L_K/i ,  λ_E = π·√(E/fy)
    α_K : 0,21 (a) / 0,34 (b) / 0,49 (c) / 0,76 (d)   — Tableau 8

    ⚠ α_d = 0,76 en SIA 263 contre 0,76 également en EN 1993-1-1 :
      les courbes a-d coïncident (0,21 / 0,34 / 0,49 / 0,76).

§4.5.2 — Déversement des poutres fléchies
    M_D,Rd = χ_D·W·fy / γM1                                      (9)
    χ_D = 1/(Φ_D + √(Φ_D² − λ̄_D²))  ≤ 1,0                        (10)
    Φ_D = 0,5·[1 + α_D·(λ̄_D − 0,4) + λ̄_D²]
    λ̄_D = √(W·fy / M_cr,D)
    α_D = 0,21 (profilés laminés) / 0,49 (profilés soudés)

    ⚠ Écart vs EN 1993-1-1 : le décalage est de 0,4 en SIA (§4.5.2.3)
      contre 0,2 en EC3 §6.3.2.2 (cas général) — et l'EC3 §6.3.2.3
      (profilés laminés) utilise 0,4 mais avec en plus β = 0,75 et un
      plafond χ_LT ≤ 1/λ̄_LT². Les deux formulations sont donc distinctes.
      §4.5.2.4 autorise explicitement de calculer χ_D selon l'EN 1993-1-1.

§4.5.4 — Voilement des éléments plans cisaillés
    V_Rd = 0,9·√(τ_cr·τ_y)·b·t / γM1  ≤  τ_y·b·t / γM1           (13)
    τ_y = fy/√3
    τ_cr = k_τ·0,9·E·(t/b)²
    k_τ = 4,0 + 5,34/α²  pour α < 1 ;  k_τ = 5,34 + 4,0/α²  pour α ≥ 1
    α = a/b (rapport des côtés du panneau)

    ⚠ La forme 0,9·√(τ_cr·τ_y) de l'éq. (13) est reconstruite depuis un
      PDF dont la formule est partiellement illisible (OCR) ; elle est
      cohérente avec la formulation classique du voilement par
      cisaillement en domaine élasto-plastique. À confirmer contre le
      document source avant usage en production. Les k_τ, eux, sont lus
      sans ambiguïté (figure 8) et coïncident avec l'Annexe A.3 de
      l'EN 1993-1-5.
"""

__all__ = [
    'ALPHA_K', 'ALPHA_D',
    'FlexuralBucklingSIA', 'LateralTorsionalBucklingSIA', 'ShearBucklingSIA',
    'eta_moment_distribution',
]

import math
from typing import Optional, TypeVar

from core.formula import FormulaResult, FormulaCollection
from norme.SIA263.elu.resistance import GAMMA_M1

SecMatSteel = TypeVar('SecMatSteel')

#: Facteurs d'imperfection au flambage — SIA 263 Tableau 8.
ALPHA_K = {"a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}

#: Facteurs d'imperfection au déversement — SIA 263 §4.5.2.3.
ALPHA_D = {"rolled": 0.21, "welded": 0.49}


def eta_moment_distribution(psi: float) -> float:
    """
    Coefficient η de répartition des moments — SIA 263 éq. (94), Annexe B.6 :

        η = 1,75 − 1,05·ψ + 0,3·ψ²   pour ψ > −0,5

    :param psi: Rapport du plus petit au plus grand moment d'extrémité
        (signes compris).
    """
    if psi <= -0.5:
        # Hors domaine de l'éq. (94) — on plafonne à la valeur en ψ = −0,5
        psi = -0.5
    return 1.75 - 1.05 * psi + 0.3 * psi ** 2


# ======================================================================
#  §4.5.1 — Flambage
# ======================================================================

class FlexuralBucklingSIA:
    """
    Flambage par flexion — SIA 263 §4.5.1.

    :param Ned: Effort normal de compression [N].
    :param Lk: Longueur de flambage [mm].
    :param i: Rayon de giration de l'axe considéré [mm].
    :param curve: Courbe de flambage "a"/"b"/"c"/"d" (Tableau 8, figure 7).
    :param axis: Étiquette de l'axe ("y" ou "z") — affichage seulement.
    """

    def __init__(
        self,
        Ned: float = 0.0,
        Lk: float = 0.0,
        i: float = 0.0,
        curve: str = "b",
        axis: str = "y",
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__ned = abs(Ned)
        self.__Lk = Lk
        self.__axis = axis
        self.__curve = curve.lower()
        if self.__curve not in ALPHA_K:
            raise ValueError(
                f"Courbe de flambage '{curve}' inconnue. "
                f"Valeurs : {list(ALPHA_K.keys())}"
            )

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__E = (sec_mat.E if sec_mat else kwargs.get("E", 210000.0)) or 210000.0
        self.__A = sec_mat.A if sec_mat else kwargs.get("A", 0.0)
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)

        if i:
            self.__i = i
        elif sec_mat is not None:
            self.__i = sec_mat.iz if axis == "z" else sec_mat.iy
        else:
            self.__i = kwargs.get("iz" if axis == "z" else "iy", 0.0)

    @property
    def lambda_E(self) -> float:
        """λ_E = π·√(E/fy) — élancement de référence."""
        if self.__fy <= 0:
            return 0.0
        return math.pi * math.sqrt(self.__E / self.__fy)

    @property
    def lambda_K(self) -> float:
        """λ_K = L_K / i."""
        if self.__i == 0:
            return float('inf')
        return self.__Lk / self.__i

    @property
    def lambda_bar_K(self) -> float:
        """λ̄_K = λ_K / λ_E."""
        if self.lambda_E == 0:
            return float('inf')
        return self.lambda_K / self.lambda_E

    @property
    def alpha_K(self) -> float:
        """Facteur d'imperfection α_K — Tableau 8."""
        return ALPHA_K[self.__curve]

    @property
    def phi_K(self) -> float:
        """Φ_K = 0,5·[1 + α_K·(λ̄_K − 0,2) + λ̄_K²]."""
        lam = self.lambda_bar_K
        return 0.5 * (1.0 + self.alpha_K * (lam - 0.2) + lam ** 2)

    @property
    def chi_K(self) -> float:
        """χ_K = 1/(Φ_K + √(Φ_K² − λ̄_K²)) ≤ 1,0 — éq. (8)."""
        phi, lam = self.phi_K, self.lambda_bar_K
        disc = phi ** 2 - lam ** 2
        if disc < 0:
            return 0.0
        denom = phi + math.sqrt(disc)
        if denom == 0:
            return 0.0
        return min(1.0 / denom, 1.0)

    @property
    def nk_rd(self) -> float:
        """N_K,Rd = χ_K·A·fy / γM1  [N] — éq. (7)."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.chi_K * self.__A * self.__fy / self.__gamma_m1

    @property
    def verif(self) -> float:
        if self.nk_rd == 0:
            return float('inf')
        return round(self.__ned / self.nk_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def get_lambda_bar(self, with_values: bool = False) -> FormulaResult:
        r = self.lambda_bar_K
        fv = (
            f"λ̄_K = (L_K/i)/λ_E = ({self.__Lk:.1f}/{self.__i:.2f}) / "
            f"{self.lambda_E:.2f} = {r:.4f}"
        ) if with_values else ""
        return FormulaResult(
            name=f"λ̄_K,{self.__axis}",
            formula="λ̄_K = (L_K/i) / λ_E,  λ_E = π·√(E/fy)",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="SIA 263 — §4.5.1.4",
        )

    def get_chi(self, with_values: bool = False) -> FormulaResult:
        r = self.chi_K
        fv = (
            f"Φ_K = {self.phi_K:.4f} (α_K = {self.alpha_K}, courbe "
            f"{self.__curve}) → χ_K = {r:.4f}"
        ) if with_values else ""
        return FormulaResult(
            name=f"χ_K,{self.__axis}",
            formula="χ_K = 1/(Φ_K + √(Φ_K² − λ̄_K²)) ≤ 1,0",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="SIA 263 — §4.5.1.4, éq. (8)",
        )

    def get_nk_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.nk_rd
        fv = (
            f"N_K,Rd = {self.chi_K:.4f} × {self.__A:.1f} × {self.__fy:.1f} / "
            f"{self.__gamma_m1} = {r:.2f} N"
        ) if with_values else ""
        return FormulaResult(
            name=f"N_K,Rd,{self.__axis}",
            formula="N_K,Rd = χ_K·A·fy / γM1",
            formula_values=fv, result=r, unit="N",
            ref="SIA 263 — §4.5.1.3, éq. (7)",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"N_Ed / N_K,Rd = {self.__ned:.2f} / {self.nk_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name=f"N_Ed/N_K,Rd,{self.__axis}",
            formula="N_Ed / N_K,Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §4.5.1",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Flambage par flexion (axe {self.__axis})",
            ref="SIA 263 — §4.5.1",
        )
        fc.add(self.get_lambda_bar(with_values=with_values))
        fc.add(self.get_chi(with_values=with_values))
        fc.add(self.get_nk_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"FlexuralBucklingSIA(axe={self.__axis}, λ̄_K={self.lambda_bar_K:.4f}, "
            f"χ_K={self.chi_K:.4f}, N_K,Rd={self.nk_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  §4.5.2 — Déversement
# ======================================================================

class LateralTorsionalBucklingSIA:
    """
    Déversement des poutres fléchies — SIA 263 §4.5.2.

    :param My_ed: Moment de calcul My,Ed [N·mm].
    :param Mcr: Moment critique de déversement élastique [N·mm]. Si absent,
        calculé par la formule classique (appuis à fourche) avec le
        coefficient η de l'éq. (94) :
            M_cr = η·(π²·E·Iz/L²)·√(Iw/Iz + L²·G·It/(π²·E·Iz))
    :param profile: "rolled" (α_D = 0,21) ou "welded" (α_D = 0,49).
    :param psi: Rapport des moments d'extrémité — pour η via l'éq. (94).
    """

    def __init__(
        self,
        My_ed: float = 0.0,
        L: float = 0.0,
        Mcr: Optional[float] = None,
        profile: str = "rolled",
        section_class: int = 1,
        psi: float = 1.0,
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__my_ed = abs(My_ed)
        self.__L = L
        self.__mcr_input = Mcr
        self.__section_class = section_class
        self.__psi = psi
        self.__profile = profile.lower()
        if self.__profile not in ALPHA_D:
            raise ValueError(
                f"profile '{profile}' inconnu. Valeurs : {list(ALPHA_D.keys())}"
            )

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__E = (sec_mat.E if sec_mat else kwargs.get("E", 210000.0)) or 210000.0
        self.__G = kwargs.get("G", 81000.0)
        self.__Iz = sec_mat.Iz if sec_mat else kwargs.get("Iz", 0.0)
        self.__It = sec_mat.It if sec_mat else kwargs.get("It", 0.0)
        self.__Iw = sec_mat.Iw if sec_mat else kwargs.get("Iw", 0.0)
        self.__Wpl_y = sec_mat.Wpl_y if sec_mat else kwargs.get("Wpl_y", 0.0)
        self.__Wel_y = sec_mat.Wel_y if sec_mat else kwargs.get("Wel_y", 0.0)
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)

    @property
    def W(self) -> float:
        """Module de section — W_pl (classes 1-2) ou W_el (classe 3)."""
        return self.__Wpl_y if self.__section_class <= 2 else self.__Wel_y

    @property
    def eta_psi(self) -> float:
        """η — coefficient de répartition des moments, éq. (94)."""
        return eta_moment_distribution(self.__psi)

    @property
    def mcr(self) -> float:
        """Moment critique de déversement élastique [N·mm]."""
        if self.__mcr_input is not None:
            return self.__mcr_input
        if self.__L <= 0 or self.__Iz <= 0:
            return 0.0
        pi2EIz = math.pi ** 2 * self.__E * self.__Iz
        term = self.__Iw / self.__Iz + (
            self.__L ** 2 * self.__G * self.__It / pi2EIz
        )
        if term < 0:
            return 0.0
        return self.eta_psi * (pi2EIz / self.__L ** 2) * math.sqrt(term)

    @property
    def lambda_bar_D(self) -> float:
        """λ̄_D = √(W·fy / M_cr,D)."""
        if self.mcr <= 0:
            return float('inf')
        return math.sqrt(self.W * self.__fy / self.mcr)

    @property
    def alpha_D(self) -> float:
        """α_D — 0,21 laminé / 0,49 soudé."""
        return ALPHA_D[self.__profile]

    @property
    def phi_D(self) -> float:
        """Φ_D = 0,5·[1 + α_D·(λ̄_D − 0,4) + λ̄_D²]."""
        lam = self.lambda_bar_D
        return 0.5 * (1.0 + self.alpha_D * (lam - 0.4) + lam ** 2)

    @property
    def chi_D(self) -> float:
        """χ_D = 1/(Φ_D + √(Φ_D² − λ̄_D²)) ≤ 1,0 — éq. (10)."""
        phi, lam = self.phi_D, self.lambda_bar_D
        if math.isinf(lam):
            return 0.0
        disc = phi ** 2 - lam ** 2
        if disc < 0:
            return 0.0
        denom = phi + math.sqrt(disc)
        if denom == 0:
            return 0.0
        return min(1.0 / denom, 1.0)

    @property
    def md_rd(self) -> float:
        """M_D,Rd = χ_D·W·fy / γM1  [N·mm] — éq. (9)."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.chi_D * self.W * self.__fy / self.__gamma_m1

    @property
    def verif(self) -> float:
        if self.md_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.md_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def get_mcr(self, with_values: bool = False) -> FormulaResult:
        r = self.mcr
        fv = ""
        if with_values:
            src = (
                "valeur fournie" if self.__mcr_input is not None
                else f"η = {self.eta_psi:.4f} (ψ = {self.__psi:+.2f}), appuis à fourche"
            )
            fv = f"M_cr,D = {r:.2f} N·mm  ({src})"
        return FormulaResult(
            name="M_cr,D",
            formula="M_cr,D = η·(π²EIz/L²)·√(Iw/Iz + L²·G·It/(π²EIz))",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 263 — Annexe B, éq. (94)",
        )

    def get_lambda_bar(self, with_values: bool = False) -> FormulaResult:
        r = self.lambda_bar_D
        fv = (
            f"λ̄_D = √({self.W:.1f} × {self.__fy:.1f} / {self.mcr:.2f}) = {r:.4f}"
        ) if with_values else ""
        return FormulaResult(
            name="λ̄_D",
            formula="λ̄_D = √(W·fy / M_cr,D)",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="SIA 263 — §4.5.2.3",
        )

    def get_chi(self, with_values: bool = False) -> FormulaResult:
        r = self.chi_D
        fv = (
            f"Φ_D = {self.phi_D:.4f} (α_D = {self.alpha_D}, "
            f"{self.__profile}) → χ_D = {r:.4f}"
        ) if with_values else ""
        return FormulaResult(
            name="χ_D",
            formula="χ_D = 1/(Φ_D + √(Φ_D² − λ̄_D²)) ≤ 1,0",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="SIA 263 — §4.5.2.3, éq. (10)",
        )

    def get_md_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.md_rd
        fv = (
            f"M_D,Rd = {self.chi_D:.4f} × {self.W:.1f} × {self.__fy:.1f} / "
            f"{self.__gamma_m1} = {r:.2f} N·mm"
        ) if with_values else ""
        return FormulaResult(
            name="M_D,Rd",
            formula="M_D,Rd = χ_D·W·fy / γM1",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 263 — §4.5.2.2, éq. (9)",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"My_Ed / M_D,Rd = {self.__my_ed:.2f} / {self.md_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="My_Ed/M_D,Rd",
            formula="My_Ed / M_D,Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §4.5.2",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Déversement", ref="SIA 263 — §4.5.2",
        )
        fc.add(self.get_mcr(with_values=with_values))
        fc.add(self.get_lambda_bar(with_values=with_values))
        fc.add(self.get_chi(with_values=with_values))
        fc.add(self.get_md_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"LateralTorsionalBucklingSIA(λ̄_D={self.lambda_bar_D:.4f}, "
            f"χ_D={self.chi_D:.4f}, M_D,Rd={self.md_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  §4.5.4 — Voilement des éléments plans cisaillés
# ======================================================================

class ShearBucklingSIA:
    """
    Voilement de l'âme cisaillée — SIA 263 §4.5.4, éq. (13).

    :param Ved: Effort tranchant de calcul [N].
    :param hw: Hauteur de l'âme (b dans l'éq. 13) [mm].
    :param tw: Épaisseur de l'âme (t) [mm].
    :param a: Espacement des raidisseurs transversaux [mm] (None = aucun).
    """

    def __init__(
        self,
        Ved: float = 0.0,
        hw: float = 0.0,
        tw: float = 0.0,
        a: Optional[float] = None,
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__ved = abs(Ved)
        self.__a = a

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__E = (sec_mat.E if sec_mat else kwargs.get("E", 210000.0)) or 210000.0
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)

        if hw:
            self.__hw = hw
        elif sec_mat is not None and hasattr(sec_mat, "hw"):
            self.__hw = sec_mat.hw
        else:
            self.__hw = kwargs.get("hw", 0.0)
        self.__tw = tw or (sec_mat.tw if sec_mat else kwargs.get("tw", 0.0))

    @property
    def tau_y(self) -> float:
        """τ_y = fy/√3 — limite d'élasticité en cisaillement [MPa]."""
        return self.__fy / math.sqrt(3)

    @property
    def k_tau(self) -> float:
        """k_τ — figure 8 (identique à l'Annexe A.3 de l'EN 1993-1-5)."""
        if not self.__a or self.__a <= 0 or self.__hw <= 0:
            return 5.34
        alpha = self.__a / self.__hw
        if alpha >= 1.0:
            return 5.34 + 4.00 / alpha ** 2
        return 4.00 + 5.34 / alpha ** 2

    @property
    def tau_cr(self) -> float:
        """τ_cr = k_τ·0,9·E·(t/b)²  [MPa]."""
        if self.__hw == 0:
            return 0.0
        return self.k_tau * 0.9 * self.__E * (self.__tw / self.__hw) ** 2

    @property
    def v_rd(self) -> float:
        """
        V_Rd = 0,9·√(τ_cr·τ_y)·b·t / γM1  ≤  τ_y·b·t / γM1  — éq. (13).
        """
        if self.__gamma_m1 == 0:
            return 0.0
        area = self.__hw * self.__tw
        plastic = self.tau_y * area / self.__gamma_m1
        if self.tau_cr <= 0:
            return 0.0
        buckling = 0.9 * math.sqrt(self.tau_cr * self.tau_y) * area / self.__gamma_m1
        return min(buckling, plastic)

    @property
    def is_buckling_governing(self) -> bool:
        """True si le voilement gouverne (V_Rd < plafond plastique)."""
        area = self.__hw * self.__tw
        if self.__gamma_m1 == 0 or area == 0:
            return False
        plastic = self.tau_y * area / self.__gamma_m1
        return self.v_rd < plastic - 1e-9

    @property
    def verif(self) -> float:
        if self.v_rd == 0:
            return float('inf')
        return round(self.__ved / self.v_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def get_tau_cr(self, with_values: bool = False) -> FormulaResult:
        r = self.tau_cr
        fv = (
            f"τ_cr = {self.k_tau:.4f} × 0,9 × {self.__E:.0f} × "
            f"({self.__tw:.2f}/{self.__hw:.1f})² = {r:.2f} MPa"
        ) if with_values else ""
        return FormulaResult(
            name="τ_cr",
            formula="τ_cr = k_τ·0,9·E·(t/b)²",
            formula_values=fv, result=r, unit="MPa",
            ref="SIA 263 — §4.5.4.1",
        )

    def get_v_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd
        fv = ""
        if with_values:
            area = self.__hw * self.__tw
            plastic = self.tau_y * area / self.__gamma_m1
            gov = (
                "voilement déterminant" if self.is_buckling_governing
                else "plafond plastique τ_y·b·t/γM1 déterminant"
            )
            fv = (
                f"V_Rd = min(0,9·√({self.tau_cr:.2f} × {self.tau_y:.2f}) × "
                f"{area:.1f} ; {plastic:.2f}) / {self.__gamma_m1} "
                f"= {r:.2f} N  ({gov})"
            )
        return FormulaResult(
            name="V_Rd (voilement)",
            formula="V_Rd = 0,9·√(τ_cr·τ_y)·b·t / γM1 ≤ τ_y·b·t / γM1",
            formula_values=fv, result=r, unit="N",
            ref="SIA 263 — §4.5.4.1, éq. (13) [forme à confirmer]",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"V_Ed / V_Rd = {self.__ved:.2f} / {self.v_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="V_Ed/V_Rd (voilement)",
            formula="V_Ed / V_Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §4.5.4",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Voilement de l'âme cisaillée",
            ref="SIA 263 — §4.5.4",
        )
        fc.add(self.get_tau_cr(with_values=with_values))
        fc.add(self.get_v_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"ShearBucklingSIA(k_τ={self.k_tau:.3f}, τ_cr={self.tau_cr:.2f}, "
            f"V_Rd={self.v_rd:.2f}, voilement_gouverne="
            f"{self.is_buckling_governing}, taux={self.verif:.4f}, "
            f"ok={self.is_ok})"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 60
    ipe = dict(
        fy=235.0, E=210000.0, A=5381.0, Iz=603.8e4, It=20.12e4, Iw=125.9e9,
        Wpl_y=628.4e3, Wel_y=557.1e3, iy=124.6, iz=33.5,
    )

    print(f"\n{sep}\n  §4.5.1 — Flambage axe z, L_K = 3 m, courbe b\n{sep}")
    fb = FlexuralBucklingSIA(Ned=300e3, Lk=3000.0, axis="z", curve="b", **ipe)
    print(f"  {fb!r}")

    print(f"\n{sep}\n  §4.5.2 — Déversement, L = 6 m, laminé, ψ = 1\n{sep}")
    ltb = LateralTorsionalBucklingSIA(
        My_ed=80e6, L=6000.0, profile="rolled", section_class=1, psi=1.0, **ipe,
    )
    print(f"  {ltb!r}")
    print(ltb.report(with_values=True))

    print(f"\n{sep}\n  §4.5.4 — Voilement âme IPE 300 (trapue)\n{sep}")
    sb = ShearBucklingSIA(Ved=200e3, hw=278.6, tw=7.1, **ipe)
    print(f"  {sb!r}")

    print(f"\n{sep}\n  §4.5.4 — Voilement âme élancée hw=1200, tw=6\n{sep}")
    sb2 = ShearBucklingSIA(Ved=400e3, hw=1200.0, tw=6.0, fy=355.0, E=210000.0)
    print(f"  {sb2!r}")
    print(sb2.report(with_values=True))

    print(f"\n{'=' * 60}\n  FIN DES TESTS\n{'=' * 60}")
