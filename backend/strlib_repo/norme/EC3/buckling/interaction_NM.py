#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC3-1-1 — §6.3.3 — Vérification à l'interaction N + M
(flambement + déversement).

Classe ``InteractionNM`` et fonctions standalone.
Méthode 1 (Annexe A) et Méthode 2 (Annexe B).
"""

__all__ = [
    "InteractionNM",
    "interaction_check",
    "Cm_uniform",
    "Cm_table_B3",
]

import math
from typing import TypeVar, Optional

from core.formula import FormulaResult, FormulaCollection

section = TypeVar("section")
material = TypeVar("material")


# ===================================================================
#  Helpers — Coefficients Cm (Tableau B.3)
# ===================================================================

def Cm_uniform(psi: float) -> float:
    """
    Coefficient de moment équivalent pour diagramme linéaire.

    Cm = 0.6 + 0.4·ψ  ≥  0.4

    :param psi: Rapport des moments d'extrémité M_min / M_max
    :return: Cm

    Ref: EC3-1-1 — Tableau B.3
    """
    return max(0.6 + 0.4 * psi, 0.4)


def Cm_table_B3(
    moment_diagram: str,
    psi: float = 0.0,
    alpha_s: float = 0.0,
) -> float:
    """
    Coefficient de moment équivalent Cm selon le Tableau B.3.

    :param moment_diagram:
        - 'linear'     → Cm = 0.6 + 0.4·ψ ≥ 0.4
        - 'parabolic'  → charge répartie : Cm ≈ 0.95 + 0.05·αh
        - 'point_load' → charge ponctuelle : Cm ≈ 0.90 + 0.10·αh
        - 'bilinear'   → Cm = 0.1 − 0.8·αs ≥ 0.4 (si αs < 0)
                          Cm = 0.2 + 0.8·αs ≥ 0.4 (si αs ≥ 0)
    :param psi: Rapport des moments d'extrémité (pour 'linear')
    :param alpha_s: Paramètre αs (ou αh selon le cas)
    :return: Cm

    Ref: EC3-1-1 — Tableau B.3
    """
    diag = moment_diagram.lower().strip()

    if diag == "linear":
        return Cm_uniform(psi)

    elif diag == "parabolic":
        # αh = alpha_s ici (rapport M_span / M_max)
        return max(0.95 + 0.05 * alpha_s, 0.4)

    elif diag == "point_load":
        return max(0.90 + 0.10 * alpha_s, 0.4)

    elif diag == "bilinear":
        if alpha_s < 0:
            return max(0.1 - 0.8 * alpha_s, 0.4)
        else:
            return max(0.2 + 0.8 * alpha_s, 0.4)

    else:
        raise ValueError(
            f"Diagramme '{moment_diagram}' non reconnu. "
            f"Valeurs admises : 'linear', 'parabolic', 'point_load', 'bilinear'."
        )


# ===================================================================
#  Fonction standalone
# ===================================================================

def interaction_check(
    Ned: float,
    Med_y: float,
    Med_z: float,
    chi_y: float,
    chi_z: float,
    chi_LT: float,
    NRk: float,
    My_Rk: float,
    Mz_Rk: float,
    kyy: float,
    kyz: float,
    kzy: float,
    kzz: float,
    gamma_m1: float = 1.0,
) -> tuple:
    """
    Retourne (eq_6_61, eq_6_62) sans instancier la classe.

    :param Ned: Effort normal de compression de calcul [N]
    :param Med_y: Moment fléchissant My,Ed [N·mm]
    :param Med_z: Moment fléchissant Mz,Ed [N·mm]
    :param chi_y: Coefficient de réduction flambement axe y
    :param chi_z: Coefficient de réduction flambement axe z
    :param chi_LT: Coefficient de réduction déversement
    :param NRk: Résistance caractéristique en compression [N]
    :param My_Rk: Moment résistant caractéristique axe y [N·mm]
    :param Mz_Rk: Moment résistant caractéristique axe z [N·mm]
    :param kyy, kyz, kzy, kzz: Facteurs d'interaction
    :param gamma_m1: Coefficient de sécurité γM1
    :return: (eq_6_61, eq_6_62)

    Ref: EC3-1-1 — Éq. (6.61) et (6.62)
    """
    Ned = abs(Ned)
    Med_y = abs(Med_y)
    Med_z = abs(Med_z)

    # Résistances de calcul
    Ny_Rd = chi_y * NRk / gamma_m1 if gamma_m1 > 0 else float("inf")
    Nz_Rd = chi_z * NRk / gamma_m1 if gamma_m1 > 0 else float("inf")
    My_Rd_LT = chi_LT * My_Rk / gamma_m1 if gamma_m1 > 0 else float("inf")
    Mz_Rd = Mz_Rk / gamma_m1 if gamma_m1 > 0 else float("inf")

    # Éq. (6.61)
    eq61 = 0.0
    if Ny_Rd > 0:
        eq61 += Ned / Ny_Rd
    if My_Rd_LT > 0:
        eq61 += kyy * Med_y / My_Rd_LT
    if Mz_Rd > 0:
        eq61 += kyz * Med_z / Mz_Rd

    # Éq. (6.62)
    eq62 = 0.0
    if Nz_Rd > 0:
        eq62 += Ned / Nz_Rd
    if My_Rd_LT > 0:
        eq62 += kzy * Med_y / My_Rd_LT
    if Mz_Rd > 0:
        eq62 += kzz * Med_z / Mz_Rd

    return (eq61, eq62)


# ===================================================================
#  Classe InteractionNM
# ===================================================================

class InteractionNM:
    """
    Vérification à l'interaction effort normal + moments fléchissants
    (flambement + déversement) selon EC3-1-1 §6.3.3.

    Supporte :
    - Méthode 2 (Annexe B, Tableau B.1 / B.2) — par défaut
    - Méthode 1 (Annexe A, Tableau A.1 / A.2)
    """

    def __init__(
        self,
        Ned: float,
        Med_y: float = 0.0,
        Med_z: float = 0.0,
        chi_y: float = 1.0,
        chi_z: float = 1.0,
        chi_LT: float = 1.0,
        mat: Optional[material] = None,
        sec: Optional[section] = None,
        section_class: int = 1,
        Cmy: float = 0.9,
        Cmz: float = 0.9,
        CmLT: float = 0.9,
        lambda_bar_y: float = 0.0,
        lambda_bar_z: float = 0.0,
        lambda_bar_LT: float = 0.0,
        interaction_method: int = 2,
        **kwargs,
    ) -> None:
        """
        :param Ned: Effort normal de compression de calcul [N]
        :param Med_y: Moment fléchissant My,Ed [N·mm]
        :param Med_z: Moment fléchissant Mz,Ed [N·mm]
        :param chi_y: Coefficient de réduction flambement axe y
        :param chi_z: Coefficient de réduction flambement axe z
        :param chi_LT: Coefficient de réduction déversement
        :param mat: Instance Material (optionnel)
        :param sec: Instance Section (optionnel)
        :param section_class: Classe de section (1, 2 ou 3)
        :param Cmy: Coefficient de moment équivalent Cm,y
        :param Cmz: Coefficient de moment équivalent Cm,z
        :param CmLT: Coefficient de moment équivalent Cm,LT
        :param lambda_bar_y: Élancement réduit λ̄_y
        :param lambda_bar_z: Élancement réduit λ̄_z
        :param lambda_bar_LT: Élancement réduit λ̄_LT
        :param interaction_method: 1 (Annexe A) ou 2 (Annexe B)
        :param kwargs: fy, A, Wpl_y, Wpl_z, Wel_y, Wel_z, gamma_m1,
                        NRk, My_Rk, Mz_Rk
        """
        self.__ned = abs(Ned)
        self.__med_y = abs(Med_y)
        self.__med_z = abs(Med_z)
        self.__section_class = section_class
        self.__interaction_method = interaction_method

        # --- χ ---
        self.__chi_y = chi_y
        self.__chi_z = chi_z
        self.__chi_LT = chi_LT

        # --- Cm ---
        self.__Cmy = Cmy
        self.__Cmz = Cmz
        self.__CmLT = CmLT

        # --- Élancements réduits ---
        self.__lambda_bar_y = lambda_bar_y
        self.__lambda_bar_z = lambda_bar_z
        self.__lambda_bar_LT = lambda_bar_LT

        # --- Matériau ---
        self.__fy = mat.fy if mat else kwargs.get("fy", 0.0)
        self.__gamma_m1 = mat.gamma_m1 if mat else kwargs.get("gamma_m1", 1.0)

        # --- Section ---
        self.__A = sec.A if sec else kwargs.get("A", 0.0)
        self.__Wpl_y = sec.Wpl_y if sec else kwargs.get("Wpl_y", 0.0)
        self.__Wpl_z = sec.Wpl_z if sec else kwargs.get("Wpl_z", 0.0)
        self.__Wel_y = sec.Wel_y if sec else kwargs.get("Wel_y", 0.0)
        self.__Wel_z = sec.Wel_z if sec else kwargs.get("Wel_z", 0.0)

        # --- Résistances caractéristiques (overridables) ---
        self.__NRk = kwargs.get("NRk", self.__A * self.__fy)
        self.__My_Rk = kwargs.get("My_Rk", None)
        self.__Mz_Rk = kwargs.get("Mz_Rk", None)

    # ------------------------------------------------------------------
    # Résistances caractéristiques
    # ------------------------------------------------------------------

    @property
    def NRk(self) -> float:
        """NRk = A · fy [N].
        Ref: EC3-1-1 — §6.3.3"""
        return self.__NRk

    @property
    def My_Rk(self) -> float:
        """My,Rk = Wy · fy [N·mm].
        Classe 1, 2 → Wpl,y ; Classe 3 → Wel,y."""
        if self.__My_Rk is not None:
            return self.__My_Rk
        Wy = self.__Wpl_y if self.__section_class <= 2 else self.__Wel_y
        return Wy * self.__fy

    @property
    def Mz_Rk(self) -> float:
        """Mz,Rk = Wz · fy [N·mm].
        Classe 1, 2 → Wpl,z ; Classe 3 → Wel,z."""
        if self.__Mz_Rk is not None:
            return self.__Mz_Rk
        Wz = self.__Wpl_z if self.__section_class <= 2 else self.__Wel_z
        return Wz * self.__fy

    # ------------------------------------------------------------------
    # Résistances de calcul (dénominateurs des éq. d'interaction)
    # ------------------------------------------------------------------

    def _Ny_Rd(self) -> float:
        """χ_y · NRk / γM1"""
        if self.__gamma_m1 == 0:
            return float("inf")
        return self.__chi_y * self.NRk / self.__gamma_m1

    def _Nz_Rd(self) -> float:
        """χ_z · NRk / γM1"""
        if self.__gamma_m1 == 0:
            return float("inf")
        return self.__chi_z * self.NRk / self.__gamma_m1

    def _My_Rd_LT(self) -> float:
        """χ_LT · My,Rk / γM1"""
        if self.__gamma_m1 == 0:
            return float("inf")
        return self.__chi_LT * self.My_Rk / self.__gamma_m1

    def _Mz_Rd(self) -> float:
        """Mz,Rk / γM1"""
        if self.__gamma_m1 == 0:
            return float("inf")
        return self.Mz_Rk / self.__gamma_m1

    # ------------------------------------------------------------------
    # Méthode 2 — Annexe B — Facteurs d'interaction (Tableau B.1 / B.2)
    # ------------------------------------------------------------------

    def _n_y(self) -> float:
        """Ned / (χ_y · NRk / γM1)"""
        d = self._Ny_Rd()
        return self.__ned / d if d > 0 else 0.0

    def _n_z(self) -> float:
        """Ned / (χ_z · NRk / γM1)"""
        d = self._Nz_Rd()
        return self.__ned / d if d > 0 else 0.0

    @property
    def kyy(self) -> float:
        """Facteur d'interaction kyy — Méthode 2, Tableau B.1
        (classe 1, 2) ou Tableau B.2 (classe 3).

        Classe 1, 2 :
          kyy = Cmy · (1 + (λ̄_y − 0.2)·Ned/(χ_y·NRk/γM1))
                ≤ Cmy · (1 + 0.8·Ned/(χ_y·NRk/γM1))
        Classe 3 :
          kyy = Cmy · (1 + 0.6·λ̄_y·Ned/(χ_y·NRk/γM1))
                ≤ Cmy · (1 + 0.6·Ned/(χ_y·NRk/γM1))

        Ref: EC3-1-1 — Annexe B, Tableau B.1 / B.2
        """
        ny = self._n_y()
        lam_y = self.__lambda_bar_y

        if self.__section_class <= 2:
            val = self.__Cmy * (1.0 + (lam_y - 0.2) * ny)
            limit = self.__Cmy * (1.0 + 0.8 * ny)
            return min(val, limit)
        else:
            val = self.__Cmy * (1.0 + 0.6 * lam_y * ny)
            limit = self.__Cmy * (1.0 + 0.6 * ny)
            return min(val, limit)

    @property
    def kyz(self) -> float:
        """Facteur d'interaction kyz — Méthode 2.

        Classe 1, 2 : kyz = 0.6 · kzz
        Classe 3     : kyz = kzz

        Ref: EC3-1-1 — Annexe B, Tableau B.1 / B.2
        """
        if self.__section_class <= 2:
            return 0.6 * self.kzz
        return self.kzz

    @property
    def kzy(self) -> float:
        """Facteur d'interaction kzy — Méthode 2.

        Classe 1, 2 :
          kzy = (1 − 0.1·λ̄_z / (CmLT − 0.25) · Ned/(χ_z·NRk/γM1))
                ≥ (1 − 0.1/(CmLT − 0.25) · Ned/(χ_z·NRk/γM1))
        Classe 3 :
          kzy = 0.6 · kyy  (simplification pour classe 3 non symétrique,
                             ici on prend la formule classe 1,2 de B.2)

        Pour λ̄_z < 0.4 et sans déversement :  kzy = 0.6 + λ̄_z  ≤ 1.0
        (simplifié pour l'utilisateur via override si nécessaire)

        Ref: EC3-1-1 — Annexe B, Tableau B.1 / B.2
        """
        nz = self._n_z()
        lam_z = self.__lambda_bar_z
        CmLT = self.__CmLT
        denom = CmLT - 0.25
        if abs(denom) < 1e-12:
            denom = 1e-12

        if self.__section_class <= 2:
            val = 1.0 - (0.1 * lam_z / denom) * nz
            limit = 1.0 - (0.1 / denom) * nz
            return max(val, limit)
        else:
            # Classe 3 : simplification kzy = 0.6 · kyy (Tableau B.2)
            return 0.6 * self.kyy

    @property
    def kzz(self) -> float:
        """Facteur d'interaction kzz — Méthode 2, Tableau B.1 / B.2.

        Classe 1, 2 :
          kzz = Cmz · (1 + (2·λ̄_z − 0.6)·Ned/(χ_z·NRk/γM1))
                ≤ Cmz · (1 + 1.4·Ned/(χ_z·NRk/γM1))
        Classe 3 :
          kzz = Cmz · (1 + 0.6·λ̄_z·Ned/(χ_z·NRk/γM1))
                ≤ Cmz · (1 + 0.6·Ned/(χ_z·NRk/γM1))

        Ref: EC3-1-1 — Annexe B, Tableau B.1 / B.2
        """
        nz = self._n_z()
        lam_z = self.__lambda_bar_z

        if self.__section_class <= 2:
            val = self.__Cmz * (1.0 + (2.0 * lam_z - 0.6) * nz)
            limit = self.__Cmz * (1.0 + 1.4 * nz)
            return min(val, limit)
        else:
            val = self.__Cmz * (1.0 + 0.6 * lam_z * nz)
            limit = self.__Cmz * (1.0 + 0.6 * nz)
            return min(val, limit)

    # ------------------------------------------------------------------
    # Méthode 1 — Annexe A — Facteurs d'interaction (Tableau A.1 / A.2)
    # ------------------------------------------------------------------
    # NB: La méthode 1 est sensiblement plus complexe. On implémente ici
    # les formules simplifiées principales du Tableau A.1 pour classes 1, 2.

    def _mu_y(self) -> float:
        """μ_y = (1 − Ned/Ncr,y) / (1 − χ_y·Ned/Ncr,y)
        Approximation : Ncr,y ≈ NRk / λ̄_y² quand λ̄_y > 0."""
        lam = self.__lambda_bar_y
        if lam <= 0:
            return 1.0
        Ncr_y = self.NRk / (lam ** 2)
        num = 1.0 - self.__ned / Ncr_y
        den = 1.0 - self.__chi_y * self.__ned / Ncr_y
        return num / den if abs(den) > 1e-12 else 1.0

    def _mu_z(self) -> float:
        """μ_z — idem axe z."""
        lam = self.__lambda_bar_z
        if lam <= 0:
            return 1.0
        Ncr_z = self.NRk / (lam ** 2)
        num = 1.0 - self.__ned / Ncr_z
        den = 1.0 - self.__chi_z * self.__ned / Ncr_z
        return num / den if abs(den) > 1e-12 else 1.0

    @property
    def kyy_A(self) -> float:
        """Facteur d'interaction kyy — Annexe A (Tableau A.1).

        kyy = Cmy · CmLT · μ_y / (1 − Ned/Ncr,y)

        (Simplification pour classes 1, 2 — profilés I doublement symétriques)

        Ref: EC3-1-1 — Annexe A, Tableau A.1
        """
        lam_y = self.__lambda_bar_y
        if lam_y <= 0:
            return self.__Cmy
        Ncr_y = self.NRk / (lam_y ** 2)
        denom = 1.0 - self.__ned / Ncr_y
        if abs(denom) < 1e-12:
            return float("inf")
        mu_y = self._mu_y()
        return self.__Cmy * self.__CmLT * mu_y / denom

    @property
    def kyz_A(self) -> float:
        """Facteur d'interaction kyz — Annexe A.

        kyz = Cmz · μ_z / (1 − Ned/Ncr,z) · (1 − 0.25·Ned/(χ_z·NRk/γM1))

        Ref: EC3-1-1 — Annexe A, Tableau A.1
        """
        lam_z = self.__lambda_bar_z
        if lam_z <= 0:
            return self.__Cmz
        Ncr_z = self.NRk / (lam_z ** 2)
        denom = 1.0 - self.__ned / Ncr_z
        if abs(denom) < 1e-12:
            return float("inf")
        mu_z = self._mu_z()
        nz = self._n_z()
        return self.__Cmz * mu_z / denom * max(1.0 - 0.25 * nz, 0.0)

    @property
    def kzy_A(self) -> float:
        """Facteur d'interaction kzy — Annexe A.

        kzy = Cmy · CmLT · μ_y / (1 − Ned/Ncr,y) · (1 − 0.25·Ned/(χ_y·NRk/γM1))

        Ref: EC3-1-1 — Annexe A, Tableau A.2
        """
        lam_y = self.__lambda_bar_y
        if lam_y <= 0:
            return self.__Cmy
        Ncr_y = self.NRk / (lam_y ** 2)
        denom = 1.0 - self.__ned / Ncr_y
        if abs(denom) < 1e-12:
            return float("inf")
        mu_y = self._mu_y()
        ny = self._n_y()
        return self.__Cmy * self.__CmLT * mu_y / denom * max(1.0 - 0.25 * ny, 0.0)

    @property
    def kzz_A(self) -> float:
        """Facteur d'interaction kzz — Annexe A.

        kzz = Cmz · μ_z / (1 − Ned/Ncr,z)

        Ref: EC3-1-1 — Annexe A, Tableau A.1
        """
        lam_z = self.__lambda_bar_z
        if lam_z <= 0:
            return self.__Cmz
        Ncr_z = self.NRk / (lam_z ** 2)
        denom = 1.0 - self.__ned / Ncr_z
        if abs(denom) < 1e-12:
            return float("inf")
        mu_z = self._mu_z()
        return self.__Cmz * mu_z / denom

    # ------------------------------------------------------------------
    # Sélecteur de kij selon la méthode choisie
    # ------------------------------------------------------------------

    def _kyy(self) -> float:
        return self.kyy_A if self.__interaction_method == 1 else self.kyy

    def _kyz(self) -> float:
        return self.kyz_A if self.__interaction_method == 1 else self.kyz

    def _kzy(self) -> float:
        return self.kzy_A if self.__interaction_method == 1 else self.kzy

    def _kzz(self) -> float:
        return self.kzz_A if self.__interaction_method == 1 else self.kzz

    # ------------------------------------------------------------------
    # Équations d'interaction (§6.3.3)
    # ------------------------------------------------------------------

    @property
    def eq_6_61(self) -> float:
        """Ned/(χ_y·NRk/γM1) + kyy·My,Ed/(χ_LT·My,Rk/γM1) + kyz·Mz,Ed/(Mz,Rk/γM1) ≤ 1.0
        Ref: EC3-1-1 — Éq. (6.61)"""
        val = 0.0
        ny_rd = self._Ny_Rd()
        my_rd_lt = self._My_Rd_LT()
        mz_rd = self._Mz_Rd()

        if ny_rd > 0:
            val += self.__ned / ny_rd
        if my_rd_lt > 0:
            val += self._kyy() * self.__med_y / my_rd_lt
        if mz_rd > 0:
            val += self._kyz() * self.__med_z / mz_rd
        return round(val, 4)

    @property
    def eq_6_62(self) -> float:
        """Ned/(χ_z·NRk/γM1) + kzy·My,Ed/(χ_LT·My,Rk/γM1) + kzz·Mz,Ed/(Mz,Rk/γM1) ≤ 1.0
        Ref: EC3-1-1 — Éq. (6.62)"""
        val = 0.0
        nz_rd = self._Nz_Rd()
        my_rd_lt = self._My_Rd_LT()
        mz_rd = self._Mz_Rd()

        if nz_rd > 0:
            val += self.__ned / nz_rd
        if my_rd_lt > 0:
            val += self._kzy() * self.__med_y / my_rd_lt
        if mz_rd > 0:
            val += self._kzz() * self.__med_z / mz_rd
        return round(val, 4)

    @property
    def verif(self) -> float:
        """max(eq_6_61, eq_6_62)"""
        return max(self.eq_6_61, self.eq_6_62)

    @property
    def is_ok(self) -> bool:
        """True si les deux équations sont ≤ 1.0."""
        return self.verif <= 1.0

    # ------------------------------------------------------------------
    # Méthodes get_xxx (FormulaResult)
    # ------------------------------------------------------------------

    def get_NRk(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour NRk."""
        r = self.NRk
        fv = ""
        if with_values:
            fv = f"NRk = {self.__A:.2f} × {self.__fy:.2f} = {r:.2f} N"
        return FormulaResult(
            name="NRk",
            formula="NRk = A · fy",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.3.3",
        )

    def get_My_Rk(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour My,Rk."""
        r = self.My_Rk
        Wy = self.__Wpl_y if self.__section_class <= 2 else self.__Wel_y
        w_label = "Wpl,y" if self.__section_class <= 2 else "Wel,y"
        fv = ""
        if with_values:
            fv = f"My,Rk = {w_label} × fy = {Wy:.2f} × {self.__fy:.2f} = {r:.2f} N·mm"
        return FormulaResult(
            name="My,Rk",
            formula=f"My,Rk = {w_label} · fy",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.3.3",
        )

    def get_Mz_Rk(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mz,Rk."""
        r = self.Mz_Rk
        Wz = self.__Wpl_z if self.__section_class <= 2 else self.__Wel_z
        w_label = "Wpl,z" if self.__section_class <= 2 else "Wel,z"
        fv = ""
        if with_values:
            fv = f"Mz,Rk = {w_label} × fy = {Wz:.2f} × {self.__fy:.2f} = {r:.2f} N·mm"
        return FormulaResult(
            name="Mz,Rk",
            formula=f"Mz,Rk = {w_label} · fy",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.3.3",
        )

    def _k_label(self, name: str) -> str:
        """Étiquette du facteur k selon la méthode."""
        suffix = " (Annexe A)" if self.__interaction_method == 1 else " (Annexe B)"
        return name + suffix

    def get_kyy(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour kyy."""
        r = self._kyy()
        fv = ""
        if with_values:
            fv = f"kyy = {r:.4f}"
        return FormulaResult(
            name=self._k_label("kyy"),
            formula="kyy — voir Annexe A ou B",
            formula_values=fv,
            result=r,
            unit="-",
            ref=f"EC3-1-1 — Annexe {'A' if self.__interaction_method == 1 else 'B'}",
        )

    def get_kyz(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour kyz."""
        r = self._kyz()
        fv = ""
        if with_values:
            fv = f"kyz = {r:.4f}"
        return FormulaResult(
            name=self._k_label("kyz"),
            formula="kyz — voir Annexe A ou B",
            formula_values=fv,
            result=r,
            unit="-",
            ref=f"EC3-1-1 — Annexe {'A' if self.__interaction_method == 1 else 'B'}",
        )

    def get_kzy(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour kzy."""
        r = self._kzy()
        fv = ""
        if with_values:
            fv = f"kzy = {r:.4f}"
        return FormulaResult(
            name=self._k_label("kzy"),
            formula="kzy — voir Annexe A ou B",
            formula_values=fv,
            result=r,
            unit="-",
            ref=f"EC3-1-1 — Annexe {'A' if self.__interaction_method == 1 else 'B'}",
        )

    def get_kzz(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour kzz."""
        r = self._kzz()
        fv = ""
        if with_values:
            fv = f"kzz = {r:.4f}"
        return FormulaResult(
            name=self._k_label("kzz"),
            formula="kzz — voir Annexe A ou B",
            formula_values=fv,
            result=r,
            unit="-",
            ref=f"EC3-1-1 — Annexe {'A' if self.__interaction_method == 1 else 'B'}",
        )

    def get_eq_6_61(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour l'équation (6.61)."""
        r = self.eq_6_61
        fv = ""
        if with_values:
            status = "OK ✓" if r <= 1.0 else "NON VÉRIFIÉ ✗"
            ny_rd = self._Ny_Rd()
            my_rd_lt = self._My_Rd_LT()
            mz_rd = self._Mz_Rd()
            fv = (
                f"Éq.(6.61) = {self.__ned:.2f}/{ny_rd:.2f} + "
                f"{self._kyy():.4f}×{self.__med_y:.2f}/{my_rd_lt:.2f} + "
                f"{self._kyz():.4f}×{self.__med_z:.2f}/{mz_rd:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="Éq.(6.61)",
            formula="Ned/(χ_y·NRk/γM1) + kyy·My,Ed/(χ_LT·My,Rk/γM1) + kyz·Mz,Ed/(Mz,Rk/γM1) ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — Éq. (6.61)",
            is_check=True,
        )

    def get_eq_6_62(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour l'équation (6.62)."""
        r = self.eq_6_62
        fv = ""
        if with_values:
            status = "OK ✓" if r <= 1.0 else "NON VÉRIFIÉ ✗"
            nz_rd = self._Nz_Rd()
            my_rd_lt = self._My_Rd_LT()
            mz_rd = self._Mz_Rd()
            fv = (
                f"Éq.(6.62) = {self.__ned:.2f}/{nz_rd:.2f} + "
                f"{self._kzy():.4f}×{self.__med_y:.2f}/{my_rd_lt:.2f} + "
                f"{self._kzz():.4f}×{self.__med_z:.2f}/{mz_rd:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="Éq.(6.62)",
            formula="Ned/(χ_z·NRk/γM1) + kzy·My,Ed/(χ_LT·My,Rk/γM1) + kzz·Mz,Ed/(Mz,Rk/γM1) ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — Éq. (6.62)",
            is_check=True,
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification globale."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"max(Éq.6.61={self.eq_6_61:.4f} ; Éq.6.62={self.eq_6_62:.4f}) "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="Interaction N+M",
            formula="max(Éq.6.61 ; Éq.6.62) ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.3.3",
            is_check=True,
        )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes du calcul
        d'interaction N + M.
        """
        method_label = "Annexe A" if self.__interaction_method == 1 else "Annexe B"
        fc = FormulaCollection(
            title=f"Vérification interaction N + M ({method_label})",
            ref="EC3-1-1 — §6.3.3",
        )
        fc.add(self.get_NRk(with_values=with_values))
        fc.add(self.get_My_Rk(with_values=with_values))
        fc.add(self.get_Mz_Rk(with_values=with_values))
        fc.add(self.get_kyy(with_values=with_values))
        fc.add(self.get_kyz(with_values=with_values))
        fc.add(self.get_kzy(with_values=with_values))
        fc.add(self.get_kzz(with_values=with_values))
        fc.add(self.get_eq_6_61(with_values=with_values))
        fc.add(self.get_eq_6_62(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"InteractionNM(Ned={self.__ned:.2f}, "
            f"Med_y={self.__med_y:.2f}, Med_z={self.__med_z:.2f}, "
            f"eq6.61={self.eq_6_61:.4f}, eq6.62={self.eq_6_62:.4f}, "
            f"ok={self.is_ok})"
        )


# ===================================================================
#  Tests
# ===================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("  TEST — interaction_NM.py")
    print("  IPE 300, S235, L = 5 m")
    print("  Ned = 200 kN, Med_y = 80 kN·m, Med_z = 10 kN·m")
    print("  Méthode 2 (Annexe B)")
    print("=" * 65)

    # ------------------------------------------------------------------
    # Étape 1 : calcul préalable des χ et λ̄ via FlexuralBuckling
    #           et LateralTorsionalBuckling (importés localement pour test)
    # ------------------------------------------------------------------
    from norme.EC3.buckling.flexural_buckling import FlexuralBuckling
    from norme.EC3.buckling.lateral_torsional import LateralTorsionalBuckling

    # Propriétés IPE 300
    _h = 300.0
    _b = 150.0
    _tf = 10.7
    _tw = 7.1
    _r = 15.0
    _A = 5381.0          # mm²
    _Iy = 8356e4          # mm⁴
    _Iz = 603.8e4         # mm⁴
    _It = 20.1e4          # mm⁴
    _Iw = 126.0e9         # mm⁶
    _Wpl_y = 628.4e3      # mm³
    _Wpl_z = 125.2e3      # mm³
    _Wel_y = 557.1e3      # mm³
    _Wel_z = 80.5e3       # mm³
    _iy = 124.6           # mm (rayon de giration axe y)
    _iz = 33.5            # mm (rayon de giration axe z)

    _fy = 235.0           # MPa
    _E = 210000.0         # MPa
    _G = 81000.0          # MPa
    _gamma_m1 = 1.0

    _Ned = 200e3          # N
    _Med_y = 80e6         # N·mm
    _Med_z = 10e6         # N·mm
    _L = 5000.0           # mm

    # ------------------------------------------------------------------
    # Étape 2 : Flambement axe y et z
    # ------------------------------------------------------------------
    print("\n--- Flambement axe y ---")
    fb_y = FlexuralBuckling(
        Ned=_Ned,
        fy=_fy, E=_E,
        A=_A, Iy=_Iy, Iz=_Iz,
        h=_h, b=_b, tf=_tf,
        section_type="I",
        L=_L,
        Lcr_y=_L,
        Lcr_z=_L,
        gamma_m1=_gamma_m1,
        section_class=1,
    )
    print(fb_y)
    chi_y_val = fb_y.chi_y
    chi_z_val = fb_y.chi_z
    lam_y_val = fb_y.lambda_bar_y
    lam_z_val = fb_y.lambda_bar_z
    print(f"  χ_y     = {chi_y_val:.4f}  (λ̄_y = {lam_y_val:.4f})")
    print(f"  χ_z     = {chi_z_val:.4f}  (λ̄_z = {lam_z_val:.4f})")

    # ------------------------------------------------------------------
    # Étape 3 : Déversement
    # ------------------------------------------------------------------
    print("\n--- Déversement (méthode rolled) ---")
    ltb = LateralTorsionalBuckling(
        Med_y=_Med_y,
        fy=_fy, E=_E, G=_G,
        Iy=_Iy, Iz=_Iz, It=_It, Iw=_Iw,
        Wpl_y=_Wpl_y, Wel_y=_Wel_y,
        h=_h, b=_b, tf=_tf,
        section_type="I",
        L=_L,
        method="rolled",
        moment_diagram="linear",
        psi=0.0,
        gamma_m1=_gamma_m1,
        section_class=1,
    )
    chi_LT_val = ltb.chi_LT
    lam_LT_val = ltb.lambda_bar_LT
    print(f"  χ_LT    = {chi_LT_val:.4f}  (λ̄_LT = {lam_LT_val:.4f})")

    # ------------------------------------------------------------------
    # Étape 4 : Coefficients Cm
    # ------------------------------------------------------------------
    Cmy_val = Cm_uniform(psi=0.0)     # extrémités : M et 0 → ψ = 0
    Cmz_val = Cm_uniform(psi=0.0)
    CmLT_val = Cm_uniform(psi=0.0)
    print(f"\n--- Coefficients Cm ---")
    print(f"  Cmy     = {Cmy_val:.2f}")
    print(f"  Cmz     = {Cmz_val:.2f}")
    print(f"  CmLT    = {CmLT_val:.2f}")

    # ------------------------------------------------------------------
    # Étape 5 : Interaction N + M (Méthode 2)
    # ------------------------------------------------------------------
    print("\n--- Interaction N + M (Méthode 2 — Annexe B) ---")
    inm = InteractionNM(
        Ned=_Ned,
        Med_y=_Med_y,
        Med_z=_Med_z,
        chi_y=chi_y_val,
        chi_z=chi_z_val,
        chi_LT=chi_LT_val,
        fy=_fy,
        A=_A,
        Wpl_y=_Wpl_y,
        Wpl_z=_Wpl_z,
        Wel_y=_Wel_y,
        Wel_z=_Wel_z,
        gamma_m1=_gamma_m1,
        section_class=1,
        Cmy=Cmy_val,
        Cmz=Cmz_val,
        CmLT=CmLT_val,
        lambda_bar_y=lam_y_val,
        lambda_bar_z=lam_z_val,
        lambda_bar_LT=lam_LT_val,
        interaction_method=2,
    )

    print(inm)
    print(f"\n  NRk     = {inm.NRk / 1e3:.2f} kN")
    print(f"  My,Rk   = {inm.My_Rk / 1e6:.2f} kN·m")
    print(f"  Mz,Rk   = {inm.Mz_Rk / 1e6:.2f} kN·m")
    print(f"\n  kyy     = {inm._kyy():.4f}")
    print(f"  kyz     = {inm._kyz():.4f}")
    print(f"  kzy     = {inm._kzy():.4f}")
    print(f"  kzz     = {inm._kzz():.4f}")
    print(f"\n  Éq.(6.61) = {inm.eq_6_61:.4f}")
    print(f"  Éq.(6.62) = {inm.eq_6_62:.4f}")
    print(f"  Taux      = {inm.verif:.4f}  →  {'OK ✓' if inm.is_ok else 'NON VÉRIFIÉ ✗'}")

    # ------------------------------------------------------------------
    # Étape 6 : Standalone
    # ------------------------------------------------------------------
    print("\n--- Vérification standalone ---")
    eq61_s, eq62_s = interaction_check(
        Ned=_Ned,
        Med_y=_Med_y,
        Med_z=_Med_z,
        chi_y=chi_y_val,
        chi_z=chi_z_val,
        chi_LT=chi_LT_val,
        NRk=inm.NRk,
        My_Rk=inm.My_Rk,
        Mz_Rk=inm.Mz_Rk,
        kyy=inm._kyy(),
        kyz=inm._kyz(),
        kzy=inm._kzy(),
        kzz=inm._kzz(),
        gamma_m1=_gamma_m1,
    )
    print(f"  Éq.(6.61) = {eq61_s:.4f}")
    print(f"  Éq.(6.62) = {eq62_s:.4f}")

    # ------------------------------------------------------------------
    # Étape 7 : Report
    # ------------------------------------------------------------------
    print("\n--- Report ---")
    rpt = inm.report(with_values=True)
    print(rpt)

    # ------------------------------------------------------------------
    # Étape 8 : Test Cm helpers
    # ------------------------------------------------------------------
    print("\n--- Tests Cm ---")
    print(f"  Cm_uniform(ψ=1.0)   = {Cm_uniform(1.0):.2f}  (attendu: 1.00)")
    print(f"  Cm_uniform(ψ=-1.0)  = {Cm_uniform(-1.0):.2f}  (attendu: 0.40)")
    print(f"  Cm_uniform(ψ=0.0)   = {Cm_uniform(0.0):.2f}  (attendu: 0.60)")
    print(f"  Cm_uniform(ψ=-0.5)  = {Cm_uniform(-0.5):.2f}  (attendu: 0.40)")

    print(f"\n  Cm_table_B3('parabolic', αs=0)   = {Cm_table_B3('parabolic', alpha_s=0.0):.2f}")
    print(f"  Cm_table_B3('point_load', αs=0)   = {Cm_table_B3('point_load', alpha_s=0.0):.2f}")
    print(f"  Cm_table_B3('bilinear', αs=0.5)   = {Cm_table_B3('bilinear', alpha_s=0.5):.2f}")
    print(f"  Cm_table_B3('bilinear', αs=-0.5)  = {Cm_table_B3('bilinear', alpha_s=-0.5):.2f}")

    print("\n" + "=" * 65)
    print("  FIN DES TESTS")
    print("=" * 65)
