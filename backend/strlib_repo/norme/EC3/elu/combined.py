#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérifications combinées selon EC3-1-1 :
- §6.2.8  : Flexion + cisaillement
- §6.2.9  : Flexion + effort normal (uniaxial et biaxial)
- §6.2.10 : Flexion + cisaillement + effort normal

Couvre les profilés I/H en classes 1, 2 et 3.
"""
__all__ = [
    'CombinedBendingShear',
    'CombinedBendingAxial',
    'CombinedAll',
    'rho_shear',
    'mn_rd_I_section',
]

import math
from typing import TypeVar, Optional
from core.formula import FormulaResult, FormulaCollection

section = TypeVar('section')
material = TypeVar('material')

# TODO — Implémentation future :
# - Sections de classe 4 : utiliser Aeff, Weff, eN (excentricité)
# - Profilés creux rectangulaires (RHS) — formules §6.2.9.1 spécifiques
# - Profilés creux circulaires (CHS) — formules §6.2.9.1 spécifiques
# - Profilés en U, L, T — interaction spécifique
# - Prise en compte du gauchissement dans §6.2.10
# - Réduction biaxiale simultanée V+M dans les deux plans
# - Intégration avec le déversement (MbRd au lieu de McRd)
# - §6.2.9.2 — profilés I bi-symétriques formules alternatives
# - §6.2.9.3 — sections creuses


# ======================================================================
#  Fonctions standalone
# ======================================================================

def rho_shear(Ved: float, Vpl_Rd: float) -> float:
    """
    Facteur de réduction ρ pour cisaillement élevé — §6.2.8 (3).

    Parameters
    ----------
    Ved : float
        Effort tranchant de calcul [N].
    Vpl_Rd : float
        Résistance plastique au cisaillement [N].

    Returns
    -------
    float
        ρ = (2·Ved/Vpl,Rd - 1)² si Ved > 0.5·Vpl,Rd, sinon 0.
    """
    if Vpl_Rd == 0:
        return 0.0
    if abs(Ved) <= 0.5 * Vpl_Rd:
        return 0.0
    return (2.0 * abs(Ved) / Vpl_Rd - 1.0) ** 2


def mn_rd_I_section(Mpl_Rd: float, n: float, a: float) -> float:
    """
    Moment réduit MN,y,Rd pour profilé I — §6.2.9.1 (3).

    MN,y,Rd = Mpl,Rd · (1 - n) / (1 - 0.5·a)   mais ≤ Mpl,Rd.

    Parameters
    ----------
    Mpl_Rd : float
        Moment résistant plastique [N·mm].
    n : float
        Rapport Ned / Npl,Rd.
    a : float
        Rapport (A - 2·b·tf) / A  (part de l'âme dans la section).

    Returns
    -------
    float
        MN,y,Rd [N·mm].
    """
    if (1.0 - 0.5 * a) == 0:
        return 0.0
    val = Mpl_Rd * (1.0 - n) / (1.0 - 0.5 * a)
    return min(val, Mpl_Rd)


# ======================================================================
#  §6.2.8 — Flexion + Cisaillement
# ======================================================================

class CombinedBendingShear:
    """
    Vérification flexion + cisaillement — EC3-1-1 §6.2.8

    Si le cisaillement est élevé (Ved > 0.5·Vpl,Rd), le moment
    résistant est réduit par le facteur ρ.
    """

    def __init__(self, My_ed: float = 0.0, Ved: float = 0.0,
                 section_class: int = 1,
                 mat: Optional[material] = None,
                 sec: Optional[section] = None,
                 shear: Optional[object] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        My_ed : float
            Moment de calcul My,Ed [N·mm] (valeur absolue).
        Ved : float
            Effort tranchant de calcul [N] (valeur absolue).
        section_class : int
            Classe de section (1, 2 ou 3).
        mat : material, optional
            Objet matériau.
        sec : section, optional
            Objet section.
        shear : Shear, optional
            Objet Shear déjà calculé (fournit Vpl,Rd).
        **kwargs
            Valeurs alternatives : fy, gamma_m0, Wpl_y, Wel_y,
            Av_z, tw, Vpl_Rd.
        """
        self.__my_ed = abs(My_ed)
        self.__ved = abs(Ved)
        self.__section_class = section_class

        # --- Matériau ---
        self.__fy = mat.fy if mat else kwargs.get("fy", 0.0)
        self.__gamma_m0 = mat.gamma_m0 if mat else kwargs.get("gamma_m0", 1.0)

        # --- Section ---
        self.__Wpl_y = sec.Wpl_y if sec else kwargs.get("Wpl_y", 0.0)
        self.__Wel_y = sec.Wel_y if sec else kwargs.get("Wel_y", 0.0)
        self.__Av = sec.Av_z if sec else kwargs.get("Av_z", kwargs.get("Av", 0.0))
        self.__tw = sec.tw if sec else kwargs.get("tw", 0.0)

        # --- Vpl,Rd depuis objet Shear ou kwargs ---
        if shear is not None:
            self.__vpl_rd = shear.vpl_rd
        elif "Vpl_Rd" in kwargs:
            self.__vpl_rd = kwargs["Vpl_Rd"]
        else:
            if self.__gamma_m0 != 0 and self.__Av != 0:
                self.__vpl_rd = self.__Av * (self.__fy / math.sqrt(3)) / self.__gamma_m0
            else:
                self.__vpl_rd = 0.0

    # ------------------------------------------------------------------
    # Moment résistant de base (sans réduction)
    # ------------------------------------------------------------------

    @property
    def mc_y_rd(self) -> float:
        """Mc,y,Rd selon la classe de section [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        if self.__section_class <= 2:
            return self.__Wpl_y * self.__fy / self.__gamma_m0
        return self.__Wel_y * self.__fy / self.__gamma_m0

    # ------------------------------------------------------------------
    # Facteur de réduction ρ — §6.2.8 (3)
    # ------------------------------------------------------------------

    @property
    def rho(self) -> float:
        """
        Facteur ρ = (2·Ved/Vpl,Rd - 1)²  si Ved > 0.5·Vpl,Rd, sinon 0.
        §6.2.8 (3)
        """
        return rho_shear(self.__ved, self.__vpl_rd)

    def get_rho(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour le facteur ρ."""
        r = self.rho
        fv = ""
        if with_values:
            if self.__vpl_rd == 0:
                fv = "Vpl,Rd = 0 → ρ = 0"
            elif self.__ved <= 0.5 * self.__vpl_rd:
                fv = (f"Ved = {self.__ved:.2f} ≤ 0.5 × Vpl,Rd = "
                      f"{0.5 * self.__vpl_rd:.2f} → ρ = 0 (pas de réduction)")
            else:
                ratio = self.__ved / self.__vpl_rd
                fv = (f"ρ = (2 × {self.__ved:.2f} / {self.__vpl_rd:.2f} - 1)² "
                      f"= (2 × {ratio:.4f} - 1)² = {r:.4f}")
        return FormulaResult(
            name="ρ",
            formula="ρ = (2·Ved/Vpl,Rd - 1)²  si Ved > 0.5·Vpl,Rd, sinon 0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.8 (3)",
        )

    # ------------------------------------------------------------------
    # Moment résistant réduit — §6.2.8 (5)
    # ------------------------------------------------------------------

    @property
    def mv_y_rd(self) -> float:
        """
        MV,y,Rd — moment résistant réduit par cisaillement [N·mm].

        Pour profilés I, classes 1-2 :
            MV,y,Rd = (Wpl,y - ρ·Av²/(4·tw)) · fy / γM0
        Si ρ = 0, MV,y,Rd = Mc,y,Rd.
        """
        if self.rho == 0:
            return self.mc_y_rd
        if self.__gamma_m0 == 0:
            return 0.0
        if self.__section_class <= 2:
            if self.__tw == 0:
                return 0.0
            w_red = self.__Wpl_y - self.rho * self.__Av ** 2 / (4.0 * self.__tw)
            return max(w_red * self.__fy / self.__gamma_m0, 0.0)
        # Classe 3 : conservativement, pas de réduction plastique
        return self.mc_y_rd

    def get_mv_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour MV,y,Rd."""
        r = self.mv_y_rd
        fv = ""
        if with_values:
            if self.rho == 0:
                fv = (f"ρ = 0 → MV,y,Rd = Mc,y,Rd = {r:.2f} N·mm "
                      f"(pas de réduction)")
            else:
                av2_4tw = self.__Av ** 2 / (4.0 * self.__tw) if self.__tw != 0 else 0
                w_red = self.__Wpl_y - self.rho * av2_4tw
                fv = (f"MV,y,Rd = ({self.__Wpl_y:.2f} - {self.rho:.4f} × "
                      f"{self.__Av:.2f}² / (4 × {self.__tw:.2f})) × "
                      f"{self.__fy:.2f} / {self.__gamma_m0} = "
                      f"({w_red:.2f}) × {self.__fy:.2f} / "
                      f"{self.__gamma_m0} = {r:.2f} N·mm")
        return FormulaResult(
            name="MV,y,Rd",
            formula="MV,y,Rd = (Wpl,y - ρ·Av²/(4·tw)) · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.8 (5)",
        )

    # ------------------------------------------------------------------
    # Vérification
    # ------------------------------------------------------------------

    @property
    def verif(self) -> float:
        """Taux de travail My,Ed / MV,y,Rd."""
        if self.mv_y_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.mv_y_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si My,Ed / MV,y,Rd ≤ 1.0."""
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification §6.2.8."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (f"My,Ed / MV,y,Rd = {self.__my_ed:.2f} / "
                  f"{self.mv_y_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="My,Ed/MV,y,Rd",
            formula="My,Ed / MV,y,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.8 (1)",
            is_check=True,
            limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection pour la vérification M+V."""
        fc = FormulaCollection(
            title="Vérification flexion + cisaillement",
            ref="EC3-1-1 — §6.2.8",
        )
        fc.add(self.get_rho(with_values=with_values))
        fc.add(self.get_mv_y_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (f"CombinedBendingShear(My,Ed={self.__my_ed:.2f}, "
                f"Ved={self.__ved:.2f}, ρ={self.rho:.4f}, "
                f"MV,y,Rd={self.mv_y_rd:.2f}, taux={self.verif:.4f}, "
                f"ok={self.is_ok})")


# ======================================================================
#  §6.2.9 — Flexion + Effort normal
# ======================================================================

class CombinedBendingAxial:
    """
    Vérification flexion + effort normal — EC3-1-1 §6.2.9

    Profilés I/H, classes 1-2 : moments réduits MN,y,Rd et MN,z,Rd,
    puis interaction biaxiale §6.2.9 (6).
    Classe 3 : vérification élastique σ ≤ fy/γM0.
    """

    def __init__(self, Ned: float = 0.0,
                 My_ed: float = 0.0, Mz_ed: float = 0.0,
                 section_class: int = 1,
                 section_type: str = "I",
                 mat: Optional[material] = None,
                 sec: Optional[section] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        Ned : float
            Effort normal de calcul [N] (valeur absolue).
        My_ed, Mz_ed : float
            Moments de calcul [N·mm] (valeurs absolues).
        section_class : int
            Classe de section (1, 2 ou 3).
        section_type : str
            Type de section : "I", "H", "RHS", "CHS", etc.
        mat : material, optional
            Objet matériau.
        sec : section, optional
            Objet section.
        **kwargs
            Valeurs alternatives : fy, gamma_m0, A, Wpl_y, Wpl_z,
            Wel_y, Wel_z, b, tf, tw, hw, Mpl_y_Rd_input,
            Mpl_z_Rd_input, Npl_Rd_input, alpha, beta.
        """
        self.__ned = abs(Ned)
        self.__my_ed = abs(My_ed)
        self.__mz_ed = abs(Mz_ed)
        self.__section_class = section_class
        self.__section_type = section_type.upper()

        # --- Matériau ---
        self.__fy = mat.fy if mat else kwargs.get("fy", 0.0)
        self.__gamma_m0 = mat.gamma_m0 if mat else kwargs.get("gamma_m0", 1.0)

        # --- Section ---
        self.__A = sec.A if sec else kwargs.get("A", 0.0)
        self.__Wpl_y = sec.Wpl_y if sec else kwargs.get("Wpl_y", 0.0)
        self.__Wpl_z = sec.Wpl_z if sec else kwargs.get("Wpl_z", 0.0)
        self.__Wel_y = sec.Wel_y if sec else kwargs.get("Wel_y", 0.0)
        self.__Wel_z = sec.Wel_z if sec else kwargs.get("Wel_z", 0.0)
        self.__b = sec.b if sec else kwargs.get("b", 0.0)
        self.__tf = sec.tf if sec else kwargs.get("tf", 0.0)
        self.__tw = sec.tw if sec else kwargs.get("tw", 0.0)
        self.__hw = (sec.hw if sec and hasattr(sec, 'hw')
                     else kwargs.get("hw", 0.0))

        # --- Possibilité de forcer les résistances (ex. réduites par V) ---
        self.__mpl_y_rd_input = kwargs.get("Mpl_y_Rd_input", None)
        self.__mpl_z_rd_input = kwargs.get("Mpl_z_Rd_input", None)
        self.__npl_rd_input = kwargs.get("Npl_Rd_input", None)

        # --- Exposants biaxiaux (possibilité de forçage) ---
        self.__alpha_user = kwargs.get("alpha", None)
        self.__beta_user = kwargs.get("beta", None)

    # ==================================================================
    # Résistances plastiques de base
    # ==================================================================

    @property
    def npl_rd(self) -> float:
        """Npl,Rd = A · fy / γM0  [N]."""
        if self.__npl_rd_input is not None:
            return self.__npl_rd_input
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__A * self.__fy / self.__gamma_m0

    @property
    def mpl_y_rd(self) -> float:
        """Mpl,y,Rd = Wpl,y · fy / γM0  [N·mm]."""
        if self.__mpl_y_rd_input is not None:
            return self.__mpl_y_rd_input
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wpl_y * self.__fy / self.__gamma_m0

    @property
    def mpl_z_rd(self) -> float:
        """Mpl,z,Rd = Wpl,z · fy / γM0  [N·mm]."""
        if self.__mpl_z_rd_input is not None:
            return self.__mpl_z_rd_input
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wpl_z * self.__fy / self.__gamma_m0

    # ==================================================================
    # Rapport d'effort normal n et paramètre a (profilés I)
    # ==================================================================

    @property
    def n(self) -> float:
        """n = Ned / Npl,Rd — rapport d'effort normal réduit."""
        if self.npl_rd == 0:
            return float('inf')
        return self.__ned / self.npl_rd

    def get_n(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour n = Ned / Npl,Rd."""
        r = self.n
        fv = ""
        if with_values:
            fv = (f"n = Ned / Npl,Rd = {self.__ned:.2f} / "
                  f"{self.npl_rd:.2f} = {r:.4f}")
        return FormulaResult(
            name="n",
            formula="n = Ned / Npl,Rd",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9.1 (2)",
        )

    @property
    def a(self) -> float:
        """
        a = (A - 2·b·tf) / A  ≤ 0.5 — part de l'âme.
        §6.2.9.1 (3) pour profilés I.
        """
        if self.__A == 0:
            return 0.0
        val = (self.__A - 2.0 * self.__b * self.__tf) / self.__A
        return min(max(val, 0.0), 0.5)

    def get_a(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour le paramètre a."""
        r = self.a
        raw = (self.__A - 2.0 * self.__b * self.__tf) / self.__A if self.__A != 0 else 0
        fv = ""
        if with_values:
            fv = (f"a = (A - 2·b·tf) / A = ({self.__A:.2f} - 2 × "
                  f"{self.__b:.2f} × {self.__tf:.2f}) / {self.__A:.2f} "
                  f"= {raw:.4f} → min(a, 0.5) = {r:.4f}")
        return FormulaResult(
            name="a",
            formula="a = (A - 2·b·tf) / A  ≤ 0.5",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9.1 (3)",
        )

    # ==================================================================
    # Moments réduits — profilés I, classes 1-2 — §6.2.9.1
    # ==================================================================

    @property
    def mn_y_rd(self) -> float:
        """
        MN,y,Rd — moment réduit autour de y pour profilé I [N·mm].

        Si n ≤ a :  MN,y,Rd = Mpl,y,Rd  (effort normal repris par l'âme)
        Si n > a :  MN,y,Rd = Mpl,y,Rd · (1 - n) / (1 - 0.5·a)
        Dans tous les cas : MN,y,Rd ≤ Mpl,y,Rd
        §6.2.9.1 (3)
        """
        if self.__section_class > 2:
            # Classe 3 : pas de moment réduit plastique, retour Mel
            if self.__gamma_m0 == 0:
                return 0.0
            return self.__Wel_y * self.__fy / self.__gamma_m0

        if self.n <= self.a:
            return self.mpl_y_rd
        return mn_rd_I_section(self.mpl_y_rd, self.n, self.a)

    def get_mn_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour MN,y,Rd."""
        r = self.mn_y_rd
        fv = ""
        if with_values:
            if self.__section_class > 2:
                fv = (f"Classe 3 → MN,y,Rd = Mel,y,Rd = {r:.2f} N·mm")
            elif self.n <= self.a:
                fv = (f"n = {self.n:.4f} ≤ a = {self.a:.4f} → "
                      f"MN,y,Rd = Mpl,y,Rd = {r:.2f} N·mm "
                      f"(effort normal repris par l'âme)")
            else:
                fv = (f"MN,y,Rd = {self.mpl_y_rd:.2f} × "
                      f"(1 - {self.n:.4f}) / (1 - 0.5 × {self.a:.4f}) = "
                      f"{self.mpl_y_rd:.2f} × {(1 - self.n):.4f} / "
                      f"{(1 - 0.5 * self.a):.4f} = {r:.2f} N·mm")
        return FormulaResult(
            name="MN,y,Rd",
            formula="MN,y,Rd = Mpl,y,Rd · (1 - n) / (1 - 0.5·a)  ≤ Mpl,y,Rd",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.9.1 (3)",
        )

    @property
    def mn_z_rd(self) -> float:
        """
        MN,z,Rd — moment réduit autour de z pour profilé I [N·mm].

        Si n ≤ a :
            MN,z,Rd = Mpl,z,Rd
        Si n > a :
            MN,z,Rd = Mpl,z,Rd · (1 - ((n - a) / (1 - a))²)
        §6.2.9.1 (4)-(5)
        """
        if self.__section_class > 2:
            if self.__gamma_m0 == 0:
                return 0.0
            return self.__Wel_z * self.__fy / self.__gamma_m0

        if self.n <= self.a:
            return self.mpl_z_rd

        if (1.0 - self.a) == 0:
            return 0.0
        factor = 1.0 - ((self.n - self.a) / (1.0 - self.a)) ** 2
        return max(self.mpl_z_rd * factor, 0.0)

    def get_mn_z_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour MN,z,Rd."""
        r = self.mn_z_rd
        fv = ""
        if with_values:
            if self.__section_class > 2:
                fv = f"Classe 3 → MN,z,Rd = Mel,z,Rd = {r:.2f} N·mm"
            elif self.n <= self.a:
                fv = (f"n = {self.n:.4f} ≤ a = {self.a:.4f} → "
                      f"MN,z,Rd = Mpl,z,Rd = {r:.2f} N·mm")
            else:
                ratio = (self.n - self.a) / (1.0 - self.a) if (1 - self.a) != 0 else 0
                factor = 1.0 - ratio ** 2
                fv = (f"MN,z,Rd = {self.mpl_z_rd:.2f} × "
                      f"(1 - (({self.n:.4f} - {self.a:.4f}) / "
                      f"(1 - {self.a:.4f}))²) = "
                      f"{self.mpl_z_rd:.2f} × (1 - {ratio:.4f}²) = "
                      f"{self.mpl_z_rd:.2f} × {factor:.4f} = {r:.2f} N·mm")
        return FormulaResult(
            name="MN,z,Rd",
            formula="MN,z,Rd = Mpl,z,Rd · (1 - ((n-a)/(1-a))²)",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.9.1 (4)-(5)",
        )

    # ==================================================================
    # Vérifications uniaxiales
    # ==================================================================

    @property
    def verif_my(self) -> float:
        """My,Ed / MN,y,Rd."""
        if self.mn_y_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.mn_y_rd, 4)

    @property
    def verif_mz(self) -> float:
        """Mz,Ed / MN,z,Rd."""
        if self.mn_z_rd == 0:
            return float('inf')
        return round(self.__mz_ed / self.mn_z_rd, 4)

    # ==================================================================
    # Exposants biaxiaux — §6.2.9 (6)
    # ==================================================================

    @property
    def alpha(self) -> float:
        """
        Exposant α pour la vérification biaxiale §6.2.9 (6).

        Profilés I/H : α = 2.0 ; sinon α = 1.0 (conservatif).
        Peut être forcé via kwargs('alpha').
        """
        if self.__alpha_user is not None:
            return self.__alpha_user
        if self.__section_type in ("I", "H"):
            return 2.0
        return 1.0

    @property
    def beta(self) -> float:
        """
        Exposant β pour la vérification biaxiale §6.2.9 (6).

        Profilés I/H : β = max(5·n, 1.0).
        Peut être forcé via kwargs('beta').
        """
        if self.__beta_user is not None:
            return self.__beta_user
        if self.__section_type in ("I", "H"):
            return max(5.0 * self.n, 1.0)
        return 1.0

    # ==================================================================
    # Vérification biaxiale — §6.2.9 (6)
    # ==================================================================

    @property
    def verif_biaxial(self) -> float:
        """
        [My,Ed / MN,y,Rd]^α + [Mz,Ed / MN,z,Rd]^β  ≤ 1.0
        §6.2.9 (6)
        """
        ratio_y = self.__my_ed / self.mn_y_rd if self.mn_y_rd != 0 else float('inf')
        ratio_z = self.__mz_ed / self.mn_z_rd if self.mn_z_rd != 0 else float('inf')

        if ratio_y == float('inf') or ratio_z == float('inf'):
            return float('inf')

        return round(ratio_y ** self.alpha + ratio_z ** self.beta, 4)

    def get_verif_biaxial(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification biaxiale §6.2.9 (6)."""
        r = self.verif_biaxial
        ok = r <= 1.0
        fv = ""
        if with_values:
            ry = self.__my_ed / self.mn_y_rd if self.mn_y_rd != 0 else float('inf')
            rz = self.__mz_ed / self.mn_z_rd if self.mn_z_rd != 0 else float('inf')
            status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
            fv = (f"[My,Ed/MN,y,Rd]^α + [Mz,Ed/MN,z,Rd]^β = "
                  f"[{ry:.4f}]^{self.alpha:.2f} + [{rz:.4f}]^{self.beta:.2f} "
                  f"= {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="Biaxial M+N",
            formula="[My,Ed/MN,y,Rd]^α + [Mz,Ed/MN,z,Rd]^β ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9 (6)",
            is_check=True,
            limit=1.0,
        )

    # ==================================================================
    # Vérification élastique — classe 3 — §6.2.9 (4)
    # ==================================================================

    @property
    def verif_elastic(self) -> float:
        """
        σ = Ned/A + My,Ed/Wel,y + Mz,Ed/Wel,z  ≤  fy / γM0
        Retourne le ratio σ / (fy/γM0).
        §6.2.9 (4)
        """
        if self.__gamma_m0 == 0 or self.__fy == 0:
            return float('inf')
        sigma = 0.0
        if self.__A != 0:
            sigma += self.__ned / self.__A
        if self.__Wel_y != 0:
            sigma += self.__my_ed / self.__Wel_y
        if self.__Wel_z != 0:
            sigma += self.__mz_ed / self.__Wel_z
        fy_red = self.__fy / self.__gamma_m0
        if fy_red == 0:
            return float('inf')
        return round(sigma / fy_red, 4)

    def get_verif_elastic(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification élastique classe 3."""
        r = self.verif_elastic
        ok = r <= 1.0
        fy_red = self.__fy / self.__gamma_m0 if self.__gamma_m0 != 0 else 0
        sigma_n = self.__ned / self.__A if self.__A != 0 else 0
        sigma_my = self.__my_ed / self.__Wel_y if self.__Wel_y != 0 else 0
        sigma_mz = self.__mz_ed / self.__Wel_z if self.__Wel_z != 0 else 0
        sigma = sigma_n + sigma_my + sigma_mz
        fv = ""
        if with_values:
            status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
            fv = (f"σ = N/A + My/Wel,y + Mz/Wel,z = "
                  f"{sigma_n:.2f} + {sigma_my:.2f} + {sigma_mz:.2f} = "
                  f"{sigma:.2f} MPa / (fy/γM0 = {fy_red:.2f} MPa) = "
                  f"{r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="σ/(fy/γM0)",
            formula="σ = Ned/A + My,Ed/Wel,y + Mz,Ed/Wel,z  ≤ fy/γM0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9 (4)",
            is_check=True,
            limit=1.0,
        )

    # ==================================================================
    # Synthèse
    # ==================================================================

    @property
    def verif(self) -> float:
        """
        Taux de travail principal.

        Classe 1-2 :
            - biaxial si My et Mz > 0
            - uniaxial sinon
        Classe 3 : vérification élastique.
        """
        if self.__section_class <= 2:
            if self.__my_ed > 0 and self.__mz_ed > 0:
                return self.verif_biaxial
            elif self.__my_ed > 0:
                return self.verif_my
            elif self.__mz_ed > 0:
                return self.verif_mz
            else:
                # N seul — N/Npl,Rd
                return round(self.n, 4)
        return self.verif_elastic

    @property
    def is_ok(self) -> bool:
        """True si la vérification est satisfaite."""
        return self.verif <= 1.0

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection avec toutes les étapes."""
        fc = FormulaCollection(
            title="Vérification flexion + effort normal",
            ref="EC3-1-1 — §6.2.9",
        )
        fc.add(self.get_n(with_values=with_values))
        fc.add(self.get_a(with_values=with_values))
        if self.__my_ed > 0:
            fc.add(self.get_mn_y_rd(with_values=with_values))
        if self.__mz_ed > 0:
            fc.add(self.get_mn_z_rd(with_values=with_values))
        if self.__section_class <= 2:
            if self.__my_ed > 0 and self.__mz_ed > 0:
                fc.add(self.get_verif_biaxial(with_values=with_values))
            elif self.__my_ed > 0:
                r = self.verif_my
                ok = r <= 1.0
                fv = ""
                if with_values:
                    status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
                    fv = (f"My,Ed / MN,y,Rd = {self.__my_ed:.2f} / "
                          f"{self.mn_y_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
                fc.add(FormulaResult(
                    name="My,Ed/MN,y,Rd",
                    formula="My,Ed / MN,y,Rd ≤ 1.0",
                    formula_values=fv,
                    result=r,
                    unit="-",
                    ref="EC3-1-1 — §6.2.9 (1)",
                    is_check=True,
                    limit=1.0,
                ))
            elif self.__mz_ed > 0:
                r = self.verif_mz
                ok = r <= 1.0
                fv = ""
                if with_values:
                    status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
                    fv = (f"Mz,Ed / MN,z,Rd = {self.__mz_ed:.2f} / "
                          f"{self.mn_z_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
                fc.add(FormulaResult(
                    name="Mz,Ed/MN,z,Rd",
                    formula="Mz,Ed / MN,z,Rd ≤ 1.0",
                    formula_values=fv,
                    result=r,
                    unit="-",
                    ref="EC3-1-1 — §6.2.9 (1)",
                    is_check=True,
                    limit=1.0,
                ))
        else:
            fc.add(self.get_verif_elastic(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (f"CombinedBendingAxial(Ned={self.__ned:.2f}, "
                f"My,Ed={self.__my_ed:.2f}, Mz,Ed={self.__mz_ed:.2f}, "
                f"n={self.n:.4f}, taux={self.verif:.4f}, ok={self.is_ok})")


# ======================================================================
#  §6.2.10 — Flexion + Cisaillement + Effort normal (combinaison totale)
# ======================================================================

class CombinedAll:
    """
    Vérification complète §6.2.10 — EC3-1-1

    Enchaîne :
    1. Cisaillement → ρ (§6.2.8)
    2. Moment réduit par cisaillement MV,Rd (§6.2.8)
    3. Moment réduit par effort normal MN,Rd (§6.2.9)
       — en utilisant MV,Rd au lieu de Mpl,Rd si ρ > 0
    4. Vérification finale
    """

    def __init__(self, Ned: float = 0.0,
                 My_ed: float = 0.0, Mz_ed: float = 0.0,
                 Ved: float = 0.0,
                 section_class: int = 1,
                 section_type: str = "I",
                 mat: Optional[material] = None,
                 sec: Optional[section] = None,
                 shear: Optional[object] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        Ned : float
            Effort normal de calcul [N] (valeur absolue).
        My_ed, Mz_ed : float
            Moments de calcul [N·mm] (valeurs absolues).
        Ved : float
            Effort tranchant de calcul [N] (valeur absolue).
        section_class : int
            Classe de section (1, 2 ou 3).
        section_type : str
            Type de section : "I", "H", "RHS", etc.
        mat : material, optional
            Objet matériau.
        sec : section, optional
            Objet section.
        shear : Shear, optional
            Objet Shear déjà calculé.
        **kwargs
            Valeurs alternatives : fy, gamma_m0, A, Wpl_y, Wpl_z,
            Wel_y, Wel_z, Av_z, b, tf, tw, hw, Vpl_Rd.
        """
        self.__ned = abs(Ned)
        self.__my_ed = abs(My_ed)
        self.__mz_ed = abs(Mz_ed)
        self.__ved = abs(Ved)
        self.__section_class = section_class
        self.__section_type = section_type.upper()

        # --- Matériau ---
        self.__fy = mat.fy if mat else kwargs.get("fy", 0.0)
        self.__gamma_m0 = mat.gamma_m0 if mat else kwargs.get("gamma_m0", 1.0)

        # --- Section ---
        self.__A = sec.A if sec else kwargs.get("A", 0.0)
        self.__Wpl_y = sec.Wpl_y if sec else kwargs.get("Wpl_y", 0.0)
        self.__Wpl_z = sec.Wpl_z if sec else kwargs.get("Wpl_z", 0.0)
        self.__Wel_y = sec.Wel_y if sec else kwargs.get("Wel_y", 0.0)
        self.__Wel_z = sec.Wel_z if sec else kwargs.get("Wel_z", 0.0)
        self.__Av = sec.Av_z if sec else kwargs.get("Av_z", kwargs.get("Av", 0.0))
        self.__b = sec.b if sec else kwargs.get("b", 0.0)
        self.__tf = sec.tf if sec else kwargs.get("tf", 0.0)
        self.__tw = sec.tw if sec else kwargs.get("tw", 0.0)
        self.__hw = (sec.hw if sec and hasattr(sec, 'hw')
                     else kwargs.get("hw", 0.0))

        # --- Vpl,Rd ---
        if shear is not None:
            self.__vpl_rd = shear.vpl_rd
        elif "Vpl_Rd" in kwargs:
            self.__vpl_rd = kwargs["Vpl_Rd"]
        else:
            if self.__gamma_m0 != 0 and self.__Av != 0:
                self.__vpl_rd = self.__Av * (self.__fy / math.sqrt(3)) / self.__gamma_m0
            else:
                self.__vpl_rd = 0.0

    # ==================================================================
    # Étape 1 : Cisaillement — ρ
    # ==================================================================

    @property
    def rho(self) -> float:
        """Facteur ρ — §6.2.8 (3)."""
        return rho_shear(self.__ved, self.__vpl_rd)

    def get_rho(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour ρ."""
        r = self.rho
        fv = ""
        if with_values:
            if self.__vpl_rd == 0:
                fv = "Vpl,Rd = 0 → ρ = 0"
            elif self.__ved <= 0.5 * self.__vpl_rd:
                fv = (f"Ved = {self.__ved:.2f} ≤ 0.5 × Vpl,Rd = "
                      f"{0.5 * self.__vpl_rd:.2f} → ρ = 0")
            else:
                ratio = self.__ved / self.__vpl_rd
                fv = (f"ρ = (2 × {ratio:.4f} - 1)² = {r:.4f}")
        return FormulaResult(
            name="ρ",
            formula="ρ = (2·Ved/Vpl,Rd - 1)²  si Ved > 0.5·Vpl,Rd, sinon 0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.8 (3)",
        )

    # ==================================================================
    # Étape 2 : Moment réduit par cisaillement
    # ==================================================================

    @property
    def npl_rd(self) -> float:
        """Npl,Rd [N]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__A * self.__fy / self.__gamma_m0

    @property
    def mpl_y_rd(self) -> float:
        """Mpl,y,Rd non réduit [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wpl_y * self.__fy / self.__gamma_m0

    @property
    def mpl_z_rd(self) -> float:
        """Mpl,z,Rd non réduit [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wpl_z * self.__fy / self.__gamma_m0

    @property
    def mv_y_rd(self) -> float:
        """
        MV,y,Rd — moment réduit par cisaillement [N·mm].

        §6.2.8 (5) pour profilés I, classes 1-2.
        """
        if self.rho == 0:
            return self.mpl_y_rd
        if self.__gamma_m0 == 0 or self.__tw == 0:
            return 0.0
        if self.__section_class <= 2:
            w_red = self.__Wpl_y - self.rho * self.__Av ** 2 / (4.0 * self.__tw)
            return max(w_red * self.__fy / self.__gamma_m0, 0.0)
        return self.__Wel_y * self.__fy / self.__gamma_m0

    def get_mv_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour MV,y,Rd."""
        r = self.mv_y_rd
        fv = ""
        if with_values:
            if self.rho == 0:
                fv = f"ρ = 0 → MV,y,Rd = Mpl,y,Rd = {r:.2f} N·mm"
            else:
                av2_4tw = self.__Av ** 2 / (4.0 * self.__tw) if self.__tw != 0 else 0
                w_red = self.__Wpl_y - self.rho * av2_4tw
                fv = (f"MV,y,Rd = ({self.__Wpl_y:.2f} - {self.rho:.4f} × "
                      f"{self.__Av:.2f}² / (4 × {self.__tw:.2f})) × "
                      f"{self.__fy:.2f} / {self.__gamma_m0} = {r:.2f} N·mm")
        return FormulaResult(
            name="MV,y,Rd",
            formula="MV,y,Rd = (Wpl,y - ρ·Av²/(4·tw)) · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.8 (5)",
        )

    # ==================================================================
    # Étape 3 : Moments réduits par effort normal (basés sur MV,Rd)
    # ==================================================================

    @property
    def n(self) -> float:
        """n = Ned / Npl,Rd."""
        if self.npl_rd == 0:
            return float('inf')
        return self.__ned / self.npl_rd

    @property
    def a(self) -> float:
        """a = (A - 2·b·tf) / A  ≤ 0.5 — §6.2.9.1 (3)."""
        if self.__A == 0:
            return 0.0
        val = (self.__A - 2.0 * self.__b * self.__tf) / self.__A
        return min(max(val, 0.0), 0.5)

    def get_n(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour n."""
        r = self.n
        fv = ""
        if with_values:
            fv = (f"n = Ned / Npl,Rd = {self.__ned:.2f} / "
                  f"{self.npl_rd:.2f} = {r:.4f}")
        return FormulaResult(
            name="n",
            formula="n = Ned / Npl,Rd",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9.1 (2)",
        )

    def get_a(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour a."""
        r = self.a
        fv = ""
        if with_values:
            raw = (self.__A - 2 * self.__b * self.__tf) / self.__A if self.__A != 0 else 0
            fv = (f"a = (A - 2·b·tf) / A = ({self.__A:.2f} - 2 × "
                  f"{self.__b:.2f} × {self.__tf:.2f}) / {self.__A:.2f} "
                  f"= {raw:.4f} → min(a, 0.5) = {r:.4f}")
        return FormulaResult(
            name="a",
            formula="a = (A - 2·b·tf) / A  ≤ 0.5",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9.1 (3)",
        )

    @property
    def mn_y_rd(self) -> float:
        """
        MN,y,Rd — basé sur MV,y,Rd si ρ > 0, sinon Mpl,y,Rd.

        §6.2.9.1 (3) adapté pour §6.2.10.
        """
        if self.__section_class > 2:
            if self.__gamma_m0 == 0:
                return 0.0
            return self.__Wel_y * self.__fy / self.__gamma_m0

        # Le moment de référence est MV,y,Rd (qui vaut Mpl,y,Rd si ρ = 0)
        m_ref = self.mv_y_rd

        if self.n <= self.a:
            return m_ref

        if (1.0 - 0.5 * self.a) == 0:
            return 0.0
        val = m_ref * (1.0 - self.n) / (1.0 - 0.5 * self.a)
        return min(max(val, 0.0), m_ref)

    def get_mn_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour MN,y,Rd."""
        r = self.mn_y_rd
        m_ref = self.mv_y_rd
        ref_name = "MV,y,Rd" if self.rho > 0 else "Mpl,y,Rd"
        fv = ""
        if with_values:
            if self.__section_class > 2:
                fv = f"Classe 3 → MN,y,Rd = Mel,y,Rd = {r:.2f} N·mm"
            elif self.n <= self.a:
                fv = (f"n = {self.n:.4f} ≤ a = {self.a:.4f} → "
                      f"MN,y,Rd = {ref_name} = {r:.2f} N·mm")
            else:
                fv = (f"MN,y,Rd = {ref_name} × (1 - n) / (1 - 0.5·a) = "
                      f"{m_ref:.2f} × (1 - {self.n:.4f}) / "
                      f"(1 - 0.5 × {self.a:.4f}) = {r:.2f} N·mm")
        return FormulaResult(
            name="MN,y,Rd",
            formula=f"MN,y,Rd = {ref_name} · (1 - n) / (1 - 0.5·a)  ≤ {ref_name}",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.9.1 (3) / §6.2.10",
        )

    @property
    def mn_z_rd(self) -> float:
        """MN,z,Rd — moment réduit autour de z par effort normal [N·mm]."""
        if self.__section_class > 2:
            if self.__gamma_m0 == 0:
                return 0.0
            return self.__Wel_z * self.__fy / self.__gamma_m0

        if self.n <= self.a:
            return self.mpl_z_rd

        if (1.0 - self.a) == 0:
            return 0.0
        factor = 1.0 - ((self.n - self.a) / (1.0 - self.a)) ** 2
        return max(self.mpl_z_rd * factor, 0.0)

    def get_mn_z_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour MN,z,Rd."""
        r = self.mn_z_rd
        fv = ""
        if with_values:
            if self.__section_class > 2:
                fv = f"Classe 3 → MN,z,Rd = Mel,z,Rd = {r:.2f} N·mm"
            elif self.n <= self.a:
                fv = (f"n = {self.n:.4f} ≤ a = {self.a:.4f} → "
                      f"MN,z,Rd = Mpl,z,Rd = {r:.2f} N·mm")
            else:
                ratio = (self.n - self.a) / (1.0 - self.a) if (1 - self.a) != 0 else 0
                factor = 1.0 - ratio ** 2
                fv = (f"MN,z,Rd = {self.mpl_z_rd:.2f} × "
                      f"(1 - (({self.n:.4f} - {self.a:.4f}) / "
                      f"(1 - {self.a:.4f}))²) = {r:.2f} N·mm")
        return FormulaResult(
            name="MN,z,Rd",
            formula="MN,z,Rd = Mpl,z,Rd · (1 - ((n-a)/(1-a))²)",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.9.1 (4)-(5)",
        )

    # ==================================================================
    # Exposants biaxiaux
    # ==================================================================

    @property
    def alpha(self) -> float:
        """Exposant α — §6.2.9 (6). Profilés I/H : 2.0."""
        if self.__section_type in ("I", "H"):
            return 2.0
        return 1.0

    @property
    def beta(self) -> float:
        """Exposant β — §6.2.9 (6). Profilés I/H : max(5n, 1)."""
        if self.__section_type in ("I", "H"):
            return max(5.0 * self.n, 1.0)
        return 1.0

    # ==================================================================
    # Étape 4 : Vérification finale
    # ==================================================================

    @property
    def verif_biaxial(self) -> float:
        """[My,Ed / MN,y,Rd]^α + [Mz,Ed / MN,z,Rd]^β ≤ 1.0."""
        ry = self.__my_ed / self.mn_y_rd if self.mn_y_rd != 0 else float('inf')
        rz = self.__mz_ed / self.mn_z_rd if self.mn_z_rd != 0 else float('inf')
        if ry == float('inf') or rz == float('inf'):
            return float('inf')
        return round(ry ** self.alpha + rz ** self.beta, 4)

    @property
    def verif_uniaxial_y(self) -> float:
        """My,Ed / MN,y,Rd."""
        if self.mn_y_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.mn_y_rd, 4)

    @property
    def verif_elastic(self) -> float:
        """σ / (fy/γM0) pour classe 3."""
        if self.__gamma_m0 == 0 or self.__fy == 0:
            return float('inf')
        sigma = 0.0
        if self.__A != 0:
            sigma += self.__ned / self.__A
        if self.__Wel_y != 0:
            sigma += self.__my_ed / self.__Wel_y
        if self.__Wel_z != 0:
            sigma += self.__mz_ed / self.__Wel_z
        fy_red = self.__fy / self.__gamma_m0
        if fy_red == 0:
            return float('inf')
        return round(sigma / fy_red, 4)

    @property
    def verif(self) -> float:
        """
        Taux de travail final — §6.2.10.

        Classe 1-2 :
            - biaxial si My et Mz > 0
            - uniaxial y si Mz = 0
            - N seul si My = Mz = 0
        Classe 3 : vérification élastique.
        """
        if self.__section_class <= 2:
            if self.__my_ed > 0 and self.__mz_ed > 0:
                return self.verif_biaxial
            elif self.__my_ed > 0:
                return self.verif_uniaxial_y
            elif self.__mz_ed > 0:
                if self.mn_z_rd == 0:
                    return float('inf')
                return round(self.__mz_ed / self.mn_z_rd, 4)
            else:
                return round(self.n, 4)
        return self.verif_elastic

    @property
    def is_ok(self) -> bool:
        """True si la vérification est satisfaite."""
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification finale §6.2.10."""
        r = self.verif
        ok = self.is_ok
        fv = ""
        if with_values:
            status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
            if self.__section_class <= 2:
                if self.__my_ed > 0 and self.__mz_ed > 0:
                    ry = self.__my_ed / self.mn_y_rd if self.mn_y_rd != 0 else float('inf')
                    rz = self.__mz_ed / self.mn_z_rd if self.mn_z_rd != 0 else float('inf')
                    fv = (f"[My,Ed/MN,y,Rd]^α + [Mz,Ed/MN,z,Rd]^β = "
                          f"[{ry:.4f}]^{self.alpha:.2f} + "
                          f"[{rz:.4f}]^{self.beta:.2f} = "
                          f"{r:.4f} ≤ 1.0 → {status}")
                elif self.__my_ed > 0:
                    fv = (f"My,Ed / MN,y,Rd = {self.__my_ed:.2f} / "
                          f"{self.mn_y_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
                elif self.__mz_ed > 0:
                    fv = (f"Mz,Ed / MN,z,Rd = {self.__mz_ed:.2f} / "
                          f"{self.mn_z_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
                else:
                    fv = (f"n = Ned / Npl,Rd = {self.__ned:.2f} / "
                          f"{self.npl_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
            else:
                sigma_n = self.__ned / self.__A if self.__A != 0 else 0
                sigma_my = self.__my_ed / self.__Wel_y if self.__Wel_y != 0 else 0
                sigma_mz = self.__mz_ed / self.__Wel_z if self.__Wel_z != 0 else 0
                sigma = sigma_n + sigma_my + sigma_mz
                fy_red = self.__fy / self.__gamma_m0 if self.__gamma_m0 != 0 else 0
                fv = (f"σ = {sigma_n:.2f} + {sigma_my:.2f} + {sigma_mz:.2f} "
                      f"= {sigma:.2f} MPa / {fy_red:.2f} MPa = "
                      f"{r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="Vérification §6.2.10",
            formula="Combinaison M + V + N ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.10",
            is_check=True,
            limit=1.0,
        )

    # ==================================================================
    # Rapport complet
    # ==================================================================

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes
        de la vérification §6.2.10.
        """
        fc = FormulaCollection(
            title="Vérification combinée M + V + N",
            ref="EC3-1-1 — §6.2.10",
        )

        # Étape 1 : Cisaillement
        fc.add(self.get_rho(with_values=with_values))

        # Étape 2 : Moment réduit par cisaillement
        fc.add(self.get_mv_y_rd(with_values=with_values))

        # Étape 3 : Effort normal
        fc.add(self.get_n(with_values=with_values))
        fc.add(self.get_a(with_values=with_values))

        # Étape 4 : Moments réduits par N
        if self.__my_ed > 0:
            fc.add(self.get_mn_y_rd(with_values=with_values))
        if self.__mz_ed > 0:
            fc.add(self.get_mn_z_rd(with_values=with_values))

        # Étape 5 : Vérification finale
        fc.add(self.get_verif(with_values=with_values))

        return fc

    def __repr__(self) -> str:
        return (f"CombinedAll(Ned={self.__ned:.2f}, "
                f"My,Ed={self.__my_ed:.2f}, Mz,Ed={self.__mz_ed:.2f}, "
                f"Ved={self.__ved:.2f}, ρ={self.rho:.4f}, "
                f"n={self.n:.4f}, taux={self.verif:.4f}, ok={self.is_ok})")


# ======================================================================
#  Debug
# ======================================================================

if __name__ == "__main__":

    print("=" * 70)
    print("COMBINED.PY — Vérification combinée M + V + N")
    print("IPE 300, S235, Ned=200kN, My=80kN·m, Ved=150kN")
    print("=" * 70)

    # IPE 300 — propriétés
    ipe300 = dict(
        A=5381.0,           # mm²
        Av_z=2568.0,        # mm² (aire de cisaillement z)
        Wpl_y=628400.0,     # mm³
        Wpl_z=125200.0,     # mm³
        Wel_y=557100.0,     # mm³
        Wel_z=80500.0,      # mm³
        b=150.0,            # mm
        tf=10.7,            # mm
        tw=7.1,             # mm
        hw=278.6,           # mm
        h=300.0,            # mm
    )
    s235 = dict(
        fy=235.0,           # MPa
        gamma_m0=1.0,
    )

    Ned = 200e3     # 200 kN → N
    My_ed = 80e6    # 80 kN·m → N·mm
    Ved = 150e3     # 150 kN → N

    # --- Test 1 : CombinedBendingShear ---
    print("\n--- §6.2.8 : Flexion + Cisaillement ---")
    bs = CombinedBendingShear(
        My_ed=My_ed, Ved=Ved,
        section_class=1,
        **ipe300, **s235,
    )
    print(bs)
    rpt_bs = bs.report(with_values=True)
    for fr in rpt_bs.results:
        print(f"  {fr.name}: {fr.formula_values}")

    # --- Test 2 : CombinedBendingAxial ---
    print("\n--- §6.2.9 : Flexion + Effort normal ---")
    ba = CombinedBendingAxial(
        Ned=Ned, My_ed=My_ed,
        section_class=1,
        section_type="I",
        **ipe300, **s235,
    )
    print(ba)
    rpt_ba = ba.report(with_values=True)
    for fr in rpt_ba.results:
        print(f"  {fr.name}: {fr.formula_values}")

    # --- Test 3 : CombinedAll — §6.2.10 ---
    print("\n--- §6.2.10 : Combinaison complète M + V + N ---")
    ca = CombinedAll(
        Ned=Ned, My_ed=My_ed, Ved=Ved,
        section_class=1,
        section_type="I",
        **ipe300, **s235,
    )
    print(ca)
    rpt_ca = ca.report(with_values=True)
    for fr in rpt_ca.results:
        print(f"  {fr.name}: {fr.formula_values}")

    # --- Test 4 : Biaxial complet ---
    print("\n--- §6.2.10 : Biaxial Ned=200kN, My=80kN·m, Mz=10kN·m, Ved=150kN ---")
    ca2 = CombinedAll(
        Ned=Ned, My_ed=My_ed, Mz_ed=10e6, Ved=Ved,
        section_class=1,
        section_type="I",
        **ipe300, **s235,
    )
    print(ca2)
    rpt_ca2 = ca2.report(with_values=True)
    for fr in rpt_ca2.results:
        print(f"  {fr.name}: {fr.formula_values}")

    print("\n" + "=" * 70)
    print("FIN DES TESTS COMBINED.PY")
    print("=" * 70)
