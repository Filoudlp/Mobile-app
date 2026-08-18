#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC2 — Vérification à l'effort tranchant (EN 1992-1-1 §6.2)
============================================================

Couvre :
  • §6.2.2  Résistance sans armature d'effort tranchant (VRd,c)
  • §6.2.3  Modèle à treillis — armatures transversales (VRd,s, VRd,max)
  • §6.2.3  Dimensionnement Asw/s, dispositions constructives §9.2.2
  • §6.2.4  Cisaillement jonction table/âme (sections en T)
  • §6.2.2(6) / §6.2.3(8)  Réduction près de l'appui

Unités : N, mm, MPa (N/mm²)
"""

__all__ = [
    "EffortTranchant",
    "v_rd_c",
    "v_rd_s",
    "v_rd_max",
    "asw_requis",
]

import math
from typing import TypeVar, Optional

from core.formula import FormulaResult, FormulaCollection

sec_mat_rc = TypeVar("sec_mat_rc")
national_annex = TypeVar("national_annex")


# ═══════════════════════════════════════════════════════════════════════════════
#  Classe principale
# ═══════════════════════════════════════════════════════════════════════════════

class EffortTranchant:
    """
    Vérification à l'effort tranchant d'une section rectangulaire ou en T
    en béton armé (sans précontrainte) — EN 1992-1-1 §6.2.

    Paramètres
    ----------
    Ved : float
        Effort tranchant de calcul [N].
    sec : sec_mat_rc, optional
        Objet ``SecMatRC`` portant géométrie + matériaux.
    na : national_annex, optional
        Objet ``NationalAnnex`` pour les paramètres d'annexe nationale.
    **kwargs :
        Surcharge individuelle de chaque propriété (voir ci-dessous).

    Kwargs principaux
    -----------------
    bw, d, h, b, beff, hf       : géométrie  [mm]
    fck, fcd, fctm, fctk_005    : béton      [MPa]
    fyk, fyd, fywd               : acier      [MPa]
    As_l                         : armature longitudinale tendue [mm²]
    Ned                          : effort normal concomitant [N] (>0 = compression)
    Asw, s, alpha                : armatures transversales [mm², mm, °]
    cot_theta                    : cotangente θ imposée (sinon calcul auto)
    av                           : distance charge – appui [mm] (réduction §6.2.2(6))
    is_T                         : True si section en T
    gamma_c, gamma_s             : coefficients partiels
    alpha_cc                     : coefficient αcc
    k1_vrdc                      : coefficient k1 dans VRd,c (défaut 0.15)
    cot_theta_min, cot_theta_max : bornes cotθ du NA (défaut 1.0 / 2.5)
    alpha_cw                     : coefficient αcw (défaut 1.0)
    """

    # ── constructeur ──────────────────────────────────────────────────────

    def __init__(
        self,
        Ved: float,
        sec: Optional[sec_mat_rc] = None,
        na: Optional[national_annex] = None,
        **kwargs,
    ) -> None:

        self.__ved_raw = abs(Ved)

        # --- géométrie ---
        self.__bw: float = self._g(sec, "bw", kwargs, 0.0)
        self.__d: float = self._g(sec, "d", kwargs, 0.0)
        self.__h: float = self._g(sec, "h", kwargs, 0.0)
        self.__b: float = self._g(sec, "b", kwargs, self.__bw)
        self.__beff: float = self._g(sec, "beff", kwargs, self.__b)
        self.__hf: float = self._g(sec, "hf", kwargs, 0.0)
        self.__is_T: bool = self._g(sec, "is_T", kwargs, self.__hf > 0)

        # --- béton ---
        self.__fck: float = self._g(sec, "fck", kwargs, 0.0)
        self.__alpha_cc: float = self._g(sec, "alpha_cc", kwargs, 1.0)
        self.__gamma_c: float = self._na(na, "gamma_c", kwargs, 1.5)
        self.__fcd: float = self._g(sec, "fcd", kwargs,
                                     self.__alpha_cc * self.__fck / self.__gamma_c
                                     if self.__gamma_c else 0.0)
        self.__fctm: float = self._g(sec, "fctm", kwargs, 0.0)
        self.__fctk_005: float = self._g(sec, "fctk_005", kwargs, 0.0)

        # --- acier ---
        self.__fyk: float = self._g(sec, "fyk", kwargs, 500.0)
        self.__gamma_s: float = self._na(na, "gamma_s", kwargs, 1.15)
        self.__fyd: float = self._g(sec, "fyd", kwargs,
                                     self.__fyk / self.__gamma_s
                                     if self.__gamma_s else 0.0)
        self.__fywd: float = self._g(sec, "fywd", kwargs, self.__fyd)

        # --- armatures longitudinales ---
        self.__As_l: float = self._g(sec, "As_l", kwargs, 0.0)

        # --- effort normal concomitant (>0 = compression) ---
        self.__Ned: float = kwargs.get("Ned", 0.0)

        # --- armatures transversales (optionnel) ---
        self.__Asw: Optional[float] = kwargs.get("Asw", None)
        self.__s: Optional[float] = kwargs.get("s", None)
        self.__alpha_deg: float = kwargs.get("alpha", 90.0)

        # --- cotθ (optionnel, sinon auto) ---
        self.__cot_theta_user: Optional[float] = kwargs.get("cot_theta", None)

        # --- réduction près de l'appui ---
        self.__av: Optional[float] = kwargs.get("av", None)

        # --- paramètres NA ---
        self.__k1_vrdc: float = self._na(na, "k1_vrdc", kwargs, 0.15)
        self.__cot_theta_min: float = self._na(na, "cot_theta_min", kwargs, 1.0)
        self.__cot_theta_max: float = self._na(na, "cot_theta_max", kwargs, 2.5)
        self.__alpha_cw: float = self._na(na, "alpha_cw", kwargs, 1.0)

        # --- section en T : jonction table/âme §6.2.4 ---
        self.__delta_x: Optional[float] = kwargs.get("delta_x", None)
        self.__cot_theta_f: Optional[float] = kwargs.get("cot_theta_f", None)

    # ── helpers lecture attributs ─────────────────────────────────────────

    @staticmethod
    def _g(sec, attr: str, kw: dict, default):
        """Lit sec.attr, puis kw[attr], sinon default."""
        if sec is not None and hasattr(sec, attr):
            return getattr(sec, attr)
        return kw.get(attr, default)

    @staticmethod
    def _na(na, attr: str, kw: dict, default):
        """Lit na.ec2.attr, puis kw[attr], sinon default."""
        if na is not None:
            ec2 = getattr(na, "ec2", na)
            if hasattr(ec2, attr):
                return getattr(ec2, attr)
        return kw.get(attr, default)

    # ═══════════════════════════════════════════════════════════════════════
    #  Propriétés géométriques / matériaux dérivées
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def ved_raw(self) -> float:
        """Effort tranchant brut (avant réduction éventuelle) [N]"""
        return self.__ved_raw

    @property
    def beta_av(self) -> float:
        """Coefficient de réduction β = av/(2d) — §6.2.2(6). Vaut 1.0 si non applicable."""
        if self.__av is not None and self.__d > 0:
            return max(min(self.__av / (2.0 * self.__d), 1.0), 0.25)
        return 1.0

    def get_beta_av(self, with_values: bool = False) -> FormulaResult:
        r = self.beta_av
        fv = ""
        if with_values:
            if self.__av is not None and self.__d > 0:
                fv = (f"β = av / (2·d) = {self.__av:.1f} / (2×{self.__d:.1f}) "
                      f"= {self.__av / (2.0 * self.__d):.4f} → β = {r:.4f}")
            else:
                fv = "β = 1.0 (pas de réduction)"
        return FormulaResult(
            name="β",
            formula="β = av / (2·d)  [0.25 ≤ β ≤ 1.0]",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2.2(6)",
        )

    @property
    def ved(self) -> float:
        """Effort tranchant de calcul (après réduction éventuelle) [N]"""
        return self.__ved_raw * self.beta_av

    def get_ved(self, with_values: bool = False) -> FormulaResult:
        r = self.ved
        fv = ""
        if with_values:
            if abs(self.beta_av - 1.0) > 1e-9:
                fv = (f"Ved,red = β · Ved = {self.beta_av:.4f} × "
                      f"{self.__ved_raw:.2f} = {r:.2f} N")
            else:
                fv = f"Ved = {r:.2f} N (pas de réduction)"
        return FormulaResult(
            name="Ved",
            formula="Ved,red = β · Ved",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC2 — §6.2.2(6)",
        )

    @property
    def Ac(self) -> float:
        """Aire brute de la section [mm²]"""
        if self.__is_T:
            return self.__bw * self.__h + (self.__beff - self.__bw) * self.__hf
        return self.__b * self.__h

    @property
    def z(self) -> float:
        """Bras de levier simplifié z = 0.9·d [mm]"""
        return 0.9 * self.__d

    # ═══════════════════════════════════════════════════════════════════════
    #  A — RÉSISTANCE SANS ARMATURE D'EFFORT TRANCHANT  (§6.2.2)
    # ═══════════════════════════════════════════════════════════════════════

    # --- k ---
    @property
    def k_factor(self) -> float:
        """k = min(1 + √(200/d) , 2.0) — d en mm — §6.2.2(1)"""
        if self.__d <= 0:
            return 2.0
        return min(1.0 + math.sqrt(200.0 / self.__d), 2.0)

    def get_k_factor(self, with_values: bool = False) -> FormulaResult:
        r = self.k_factor
        fv = ""
        if with_values:
            fv = (f"k = min(1 + √(200/{self.__d:.1f}) , 2.0) "
                  f"= min({1.0 + math.sqrt(200.0 / self.__d) if self.__d > 0 else 2.0:.4f} , 2.0) "
                  f"= {r:.4f}")
        return FormulaResult(
            name="k",
            formula="k = min(1 + √(200/d) , 2.0)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2.2(1)",
        )

    # --- ρl ---
    @property
    def rho_l(self) -> float:
        """ρl = min(As_l / (bw·d) , 0.02) — §6.2.2(1)"""
        if self.__bw <= 0 or self.__d <= 0:
            return 0.0
        return min(self.__As_l / (self.__bw * self.__d), 0.02)

    def get_rho_l(self, with_values: bool = False) -> FormulaResult:
        r = self.rho_l
        fv = ""
        if with_values:
            raw = self.__As_l / (self.__bw * self.__d) if (self.__bw > 0 and self.__d > 0) else 0.0
            fv = (f"ρl = min(As_l/(bw·d) , 0.02) = min({self.__As_l:.2f}/({self.__bw:.1f}×{self.__d:.1f}) , 0.02) "
                  f"= min({raw:.6f} , 0.02) = {r:.6f}")
        return FormulaResult(
            name="ρl",
            formula="ρl = min(As_l / (bw·d) , 0.02)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2.2(1)",
        )

    # --- σcp ---
    @property
    def sigma_cp(self) -> float:
        """σcp = min(Ned/Ac , 0.2·fcd) [MPa] — §6.2.2(1)"""
        if self.Ac <= 0:
            return 0.0
        return min(self.__Ned / self.Ac, 0.2 * self.__fcd)

    def get_sigma_cp(self, with_values: bool = False) -> FormulaResult:
        r = self.sigma_cp
        fv = ""
        if with_values:
            sig_raw = self.__Ned / self.Ac if self.Ac > 0 else 0.0
            fv = (f"σcp = min(Ned/Ac , 0.2·fcd) = min({self.__Ned:.2f}/{self.Ac:.2f} , "
                  f"0.2×{self.__fcd:.2f}) = min({sig_raw:.4f} , {0.2 * self.__fcd:.4f}) "
                  f"= {r:.4f} MPa")
        return FormulaResult(
            name="σcp",
            formula="σcp = min(Ned / Ac , 0.2·fcd)",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — §6.2.2(1)",
        )

    # --- CRd,c ---
    @property
    def CRd_c(self) -> float:
        """CRd,c = 0.18 / γc — valeur recommandée §6.2.2(1)"""
        if self.__gamma_c == 0:
            return 0.0
        return 0.18 / self.__gamma_c

    def get_CRd_c(self, with_values: bool = False) -> FormulaResult:
        r = self.CRd_c
        fv = ""
        if with_values:
            fv = f"CRd,c = 0.18 / γc = 0.18 / {self.__gamma_c} = {r:.6f}"
        return FormulaResult(
            name="CRd,c",
            formula="CRd,c = 0.18 / γc",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2.2(1)",
        )

    # --- νmin ---
    @property
    def v_min(self) -> float:
        """νmin = 0.035 · k^(3/2) · fck^(1/2) — §6.2.2(1)"""
        return 0.035 * self.k_factor ** 1.5 * self.__fck ** 0.5

    def get_v_min(self, with_values: bool = False) -> FormulaResult:
        r = self.v_min
        fv = ""
        if with_values:
            fv = (f"νmin = 0.035 · k^(3/2) · fck^(1/2) = 0.035 × {self.k_factor:.4f}^1.5 "
                  f"× {self.__fck:.2f}^0.5 = {r:.6f} MPa")
        return FormulaResult(
            name="νmin",
            formula="νmin = 0.035 · k^(3/2) · fck^(1/2)",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — §6.2.2(1)",
        )

    # --- VRd,c ---
    @property
    def v_rd_c(self) -> float:
        """VRd,c = max(VRd,c_calc , VRd,c_min) [N] — §6.2.2(1)"""
        k = self.k_factor
        rho = self.rho_l
        sig = self.sigma_cp
        bw = self.__bw
        d = self.__d
        CRd = self.CRd_c
        k1 = self.__k1_vrdc

        v_main = CRd * k * (100.0 * rho * self.__fck) ** (1.0 / 3.0) + k1 * sig
        v_mini = self.v_min + k1 * sig

        return max(v_main, v_mini) * bw * d

    @property
    def _v_rd_c_main(self) -> float:
        """Composante principale de VRd,c (avant prise de max) [N]"""
        k = self.k_factor
        rho = self.rho_l
        sig = self.sigma_cp
        CRd = self.CRd_c
        k1 = self.__k1_vrdc
        v_main = CRd * k * (100.0 * rho * self.__fck) ** (1.0 / 3.0) + k1 * sig
        return v_main * self.__bw * self.__d

    @property
    def _v_rd_c_min(self) -> float:
        """Composante minimale de VRd,c [N]"""
        sig = self.sigma_cp
        k1 = self.__k1_vrdc
        v_mini = self.v_min + k1 * sig
        return v_mini * self.__bw * self.__d

    def get_v_rd_c(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd_c
        fv = ""
        if with_values:
            v1 = self._v_rd_c_main
            v2 = self._v_rd_c_min
            fv = (
                f"VRd,c = [CRd,c·k·(100·ρl·fck)^(1/3) + k1·σcp]·bw·d\n"
                f"      = [{self.CRd_c:.6f}×{self.k_factor:.4f}×(100×{self.rho_l:.6f}×{self.__fck:.2f})^(1/3) "
                f"+ {self.__k1_vrdc}×{self.sigma_cp:.4f}]×{self.__bw:.1f}×{self.__d:.1f}\n"
                f"      = {v1:.2f} N\n"
                f"VRd,c,min = (νmin + k1·σcp)·bw·d = ({self.v_min:.6f} + "
                f"{self.__k1_vrdc}×{self.sigma_cp:.4f})×{self.__bw:.1f}×{self.__d:.1f} = {v2:.2f} N\n"
                f"VRd,c = max({v1:.2f} ; {v2:.2f}) = {r:.2f} N"
            )
        return FormulaResult(
            name="VRd,c",
            formula="VRd,c = max([CRd,c·k·(100·ρl·fck)^(1/3)+k1·σcp]·bw·d , (νmin+k1·σcp)·bw·d)",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC2 — §6.2.2(1)",
        )

    @property
    def armature_requise(self) -> bool:
        """True si des armatures d'effort tranchant sont nécessaires (Ved > VRd,c)"""
        return self.ved > self.v_rd_c

    # ═══════════════════════════════════════════════════════════════════════
    #  B — MODÈLE À TREILLIS  (§6.2.3)
    # ═══════════════════════════════════════════════════════════════════════

    # --- ν1 ---
    @property
    def nu_1(self) -> float:
        """ν1 = 0.6 · (1 - fck/250) — §6.2.3(3) Note 1"""
        return 0.6 * (1.0 - self.__fck / 250.0)

    def get_nu_1(self, with_values: bool = False) -> FormulaResult:
        r = self.nu_1
        fv = ""
        if with_values:
            fv = f"ν1 = 0.6 × (1 - {self.__fck:.2f}/250) = {r:.6f}"
        return FormulaResult(
            name="ν1",
            formula="ν1 = 0.6 · (1 - fck/250)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2.3(3) Note 1",
        )

    # --- angles ---
    @property
    def _alpha_rad(self) -> float:
        return math.radians(self.__alpha_deg)

    @property
    def _cot_alpha(self) -> float:
        a = self._alpha_rad
        if abs(math.sin(a)) < 1e-12:
            return float("inf")
        return math.cos(a) / math.sin(a)

    @property
    def _sin_alpha(self) -> float:
        return math.sin(self._alpha_rad)

    # --- VRd,max en fonction de cotθ ---
    def _v_rd_max_cot(self, cot_theta: float) -> float:
        """VRd,max pour un cotθ donné [N] — §6.2.3(3)"""
        z = self.z
        bw = self.__bw
        acw = self.__alpha_cw
        nu1 = self.nu_1
        fcd = self.__fcd

        if abs(self.__alpha_deg - 90.0) < 1e-6:
            # cadres droits
            tan_theta = 1.0 / cot_theta if cot_theta != 0 else float("inf")
            denom = cot_theta + tan_theta
            if denom == 0:
                return 0.0
            return acw * bw * z * nu1 * fcd / denom
        else:
            # armatures inclinées
            cot_alpha = self._cot_alpha
            denom = 1.0 + cot_theta ** 2
            if denom == 0:
                return 0.0
            return acw * bw * z * nu1 * fcd * (cot_theta + cot_alpha) / denom

    # --- cotθ optimal ---
    @property
    def cot_theta(self) -> float:
        """
        cotθ utilisé pour le calcul.

        • Si fourni par l'utilisateur → borné entre cot_min et cot_max.
        • Sinon → cotθ optimal = max cotθ tel que Ved ≤ VRd,max(θ).
          Si Ved > VRd,max(θ=45°) → cot_theta = cot_min (bielle la plus raide).
        """
        if self.__cot_theta_user is not None:
            return max(self.__cot_theta_min,
                       min(self.__cot_theta_user, self.__cot_theta_max))

        # recherche du cotθ optimal (le plus grand possible)
        cot_max = self.__cot_theta_max
        cot_min = self.__cot_theta_min
        ved = self.ved

        # vérifier d'abord si VRd,max au cotθ max est suffisant
        if self._v_rd_max_cot(cot_max) >= ved:
            return cot_max

        # vérifier si même à cotθ min c'est insuffisant
        if self._v_rd_max_cot(cot_min) < ved:
            return cot_min  # section insuffisante

        # dichotomie
        lo, hi = cot_min, cot_max
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if self._v_rd_max_cot(mid) >= ved:
                lo = mid
            else:
                hi = mid
        return round(lo, 6)

    def get_cot_theta(self, with_values: bool = False) -> FormulaResult:
        r = self.cot_theta
        fv = ""
        if with_values:
            if self.__cot_theta_user is not None:
                fv = (f"cotθ imposé = {self.__cot_theta_user} → borné "
                      f"[{self.__cot_theta_min} ; {self.__cot_theta_max}] → cotθ = {r:.6f}")
            else:
                fv = (f"cotθ optimal tel que Ved ≤ VRd,max(θ) "
                      f"avec cotθ ∈ [{self.__cot_theta_min} ; {self.__cot_theta_max}] → cotθ = {r:.6f}")
        return FormulaResult(
            name="cotθ",
            formula="max cotθ tel que Ved ≤ VRd,max(θ) , cotθ ∈ [cot_min ; cot_max]",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2.3(2)",
        )

    @property
    def theta_deg(self) -> float:
        """Angle θ en degrés"""
        return math.degrees(math.atan(1.0 / self.cot_theta)) if self.cot_theta != 0 else 90.0

    # --- VRd,max ---
    @property
    def v_rd_max(self) -> float:
        """VRd,max [N] — §6.2.3(3)"""
        return self._v_rd_max_cot(self.cot_theta)

    def get_v_rd_max(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd_max
        fv = ""
        if with_values:
            cot = self.cot_theta
            if abs(self.__alpha_deg - 90.0) < 1e-6:
                tan_t = 1.0 / cot if cot != 0 else float("inf")
                fv = (
                    f"VRd,max = αcw·bw·z·ν1·fcd / (cotθ+tanθ)\n"
                    f"        = {self.__alpha_cw}×{self.__bw:.1f}×{self.z:.1f}×{self.nu_1:.6f}×{self.__fcd:.2f}"
                    f" / ({cot:.6f}+{tan_t:.6f})\n"
                    f"        = {r:.2f} N"
                )
            else:
                cot_a = self._cot_alpha
                fv = (
                    f"VRd,max = αcw·bw·z·ν1·fcd·(cotθ+cotα)/(1+cot²θ)\n"
                    f"        = {self.__alpha_cw}×{self.__bw:.1f}×{self.z:.1f}×{self.nu_1:.6f}"
                    f"×{self.__fcd:.2f}×({cot:.6f}+{cot_a:.4f})/(1+{cot ** 2:.6f})\n"
                    f"        = {r:.2f} N"
                )
        return FormulaResult(
            name="VRd,max",
            formula="VRd,max = αcw·bw·z·ν1·fcd / (cotθ+tanθ)  [cadres droits]",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC2 — §6.2.3(3)",
        )

    # --- VRd,s ---
    @property
    def v_rd_s(self) -> float:
        """VRd,s [N] — §6.2.3(3) — nécessite Asw et s."""
        if self.__Asw is None or self.__s is None or self.__s == 0:
            return 0.0
        z = self.z
        cot = self.cot_theta
        if abs(self.__alpha_deg - 90.0) < 1e-6:
            return (self.__Asw / self.__s) * z * self.__fywd * cot
        else:
            cot_a = self._cot_alpha
            sin_a = self._sin_alpha
            return (self.__Asw / self.__s) * z * self.__fywd * (cot + cot_a) * sin_a

    def get_v_rd_s(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd_s
        fv = ""
        if with_values:
            if self.__Asw is not None and self.__s is not None and self.__s > 0:
                cot = self.cot_theta
                if abs(self.__alpha_deg - 90.0) < 1e-6:
                    fv = (
                        f"VRd,s = (Asw/s)·z·fywd·cotθ\n"
                        f"      = ({self.__Asw:.2f}/{self.__s:.1f})×{self.z:.1f}×{self.__fywd:.2f}×{cot:.6f}\n"
                        f"      = {r:.2f} N"
                    )
                else:
                    cot_a = self._cot_alpha
                    sin_a = self._sin_alpha
                    fv = (
                        f"VRd,s = (Asw/s)·z·fywd·(cotθ+cotα)·sinα\n"
                        f"      = ({self.__Asw:.2f}/{self.__s:.1f})×{self.z:.1f}×{self.__fywd:.2f}"
                        f"×({cot:.6f}+{cot_a:.4f})×{sin_a:.4f}\n"
                        f"      = {r:.2f} N"
                    )
            else:
                fv = "VRd,s non calculable (Asw ou s non fourni)"
        return FormulaResult(
            name="VRd,s",
            formula="VRd,s = (Asw/s)·z·fywd·cotθ  [cadres droits]",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC2 — §6.2.3(3)",
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  C — DIMENSIONNEMENT DES ARMATURES TRANSVERSALES  (§6.2.3 + §9.2.2)
    # ═══════════════════════════════════════════════════════════════════════

    # --- Asw/s requis ---
    @property
    def asw_s_req(self) -> float:
        """(Asw/s)_req = Ved / (z·fywd·cotθ) [mm²/mm] — cadres droits"""
        z = self.z
        cot = self.cot_theta
        denom = z * self.__fywd * cot
        if denom == 0:
            return float("inf")
        if abs(self.__alpha_deg - 90.0) < 1e-6:
            return self.ved / denom
        else:
            sin_a = self._sin_alpha
            cot_a = self._cot_alpha
            denom2 = z * self.__fywd * (cot + cot_a) * sin_a
            if denom2 == 0:
                return float("inf")
            return self.ved / denom2

    def get_asw_s_req(self, with_values: bool = False) -> FormulaResult:
        r = self.asw_s_req
        fv = ""
        if with_values:
            cot = self.cot_theta
            fv = (
                f"(Asw/s)_req = Ved / (z·fywd·cotθ) = {self.ved:.2f} / "
                f"({self.z:.1f}×{self.__fywd:.2f}×{cot:.6f}) = {r:.6f} mm²/mm"
            )
        return FormulaResult(
            name="(Asw/s)_req",
            formula="(Asw/s)_req = Ved / (z·fywd·cotθ)",
            formula_values=fv,
            result=r,
            unit="mm²/mm",
            ref="EC2 — §6.2.3(3)",
        )

    # --- ρw,min ---
    @property
    def rho_w_min(self) -> float:
        """ρw,min = 0.08·√fck / fyk — §9.2.2(5)"""
        if self.__fyk == 0:
            return 0.0
        return 0.08 * math.sqrt(self.__fck) / self.__fyk

    def get_rho_w_min(self, with_values: bool = False) -> FormulaResult:
        r = self.rho_w_min
        fv = ""
        if with_values:
            fv = (f"ρw,min = 0.08·√fck/fyk = 0.08×√{self.__fck:.2f}/{self.__fyk:.2f} "
                  f"= {r:.6f}")
        return FormulaResult(
            name="ρw,min",
            formula="ρw,min = 0.08 · √fck / fyk",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §9.2.2(5)",
        )

    # --- (Asw/s)_min ---
    @property
    def asw_s_min(self) -> float:
        """(Asw/s)_min = ρw,min · bw [mm²/mm] — §9.2.2(5)"""
        return self.rho_w_min * self.__bw

    def get_asw_s_min(self, with_values: bool = False) -> FormulaResult:
        r = self.asw_s_min
        fv = ""
        if with_values:
            fv = (f"(Asw/s)_min = ρw,min · bw = {self.rho_w_min:.6f} × {self.__bw:.1f} "
                  f"= {r:.6f} mm²/mm")
        return FormulaResult(
            name="(Asw/s)_min",
            formula="(Asw/s)_min = ρw,min · bw",
            formula_values=fv,
            result=r,
            unit="mm²/mm",
            ref="EC2 — §9.2.2(5)",
        )

    # --- Asw/s de calcul (enveloppe) ---
    @property
    def asw_s_calc(self) -> float:
        """max((Asw/s)_req , (Asw/s)_min) [mm²/mm]"""
        return max(self.asw_s_req, self.asw_s_min)

    def get_asw_s_calc(self, with_values: bool = False) -> FormulaResult:
        r = self.asw_s_calc
        fv = ""
        if with_values:
            fv = (f"(Asw/s)_calc = max((Asw/s)_req ; (Asw/s)_min) "
                  f"= max({self.asw_s_req:.6f} ; {self.asw_s_min:.6f}) = {r:.6f} mm²/mm")
        return FormulaResult(
            name="(Asw/s)_calc",
            formula="(Asw/s)_calc = max((Asw/s)_req , (Asw/s)_min)",
            formula_values=fv,
            result=r,
            unit="mm²/mm",
            ref="EC2 — §6.2.3 / §9.2.2",
        )

    # --- espacement max longitudinal ---
    @property
    def s_l_max(self) -> float:
        """s_l,max = 0.75·d·(1+cotα) [mm] — §9.2.2(6)"""
        cot_a = self._cot_alpha if abs(self.__alpha_deg - 90.0) > 1e-6 else 0.0
        return 0.75 * self.__d * (1.0 + cot_a)

    def get_s_l_max(self, with_values: bool = False) -> FormulaResult:
        r = self.s_l_max
        fv = ""
        if with_values:
            fv = (f"s_l,max = 0.75·d·(1+cotα) = 0.75×{self.__d:.1f}×(1+{self._cot_alpha if abs(self.__alpha_deg - 90.0) > 1e-6 else 0.0:.4f})"
                  f" = {r:.1f} mm")
        return FormulaResult(
            name="s_l,max",
            formula="s_l,max = 0.75 · d · (1 + cotα)",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2 — §9.2.2(6)",
        )

    # --- espacement max transversal ---
    @property
    def s_t_max(self) -> float:
        """s_t,max = min(0.75·d , 600) [mm] — §9.2.2(8)"""
        return min(0.75 * self.__d, 600.0)

    def get_s_t_max(self, with_values: bool = False) -> FormulaResult:
        r = self.s_t_max
        fv = ""
        if with_values:
            fv = (f"s_t,max = min(0.75·d , 600) = min(0.75×{self.__d:.1f} , 600) "
                  f"= {r:.1f} mm")
        return FormulaResult(
            name="s_t,max",
            formula="s_t,max = min(0.75·d , 600)",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2 — §9.2.2(8)",
        )

    # --- effort de décalage ΔFtd ---
    @property
    def delta_ftd(self) -> float:
        """ΔFtd = 0.5·Ved·(cotθ - cotα) [N] — §6.2.3(7)"""
        cot_a = self._cot_alpha if abs(self.__alpha_deg - 90.0) > 1e-6 else 0.0
        return 0.5 * self.ved * (self.cot_theta - cot_a)

    def get_delta_ftd(self, with_values: bool = False) -> FormulaResult:
        r = self.delta_ftd
        fv = ""
        if with_values:
            cot_a = self._cot_alpha if abs(self.__alpha_deg - 90.0) > 1e-6 else 0.0
            fv = (f"ΔFtd = 0.5·Ved·(cotθ - cotα) = 0.5×{self.ved:.2f}×({self.cot_theta:.6f} - {cot_a:.4f})"
                  f" = {r:.2f} N")
        return FormulaResult(
            name="ΔFtd",
            formula="ΔFtd = 0.5 · Ved · (cotθ - cotα)",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC2 — §6.2.3(7)",
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  D — CISAILLEMENT JONCTION TABLE/ÂME  (§6.2.4) — section en T
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def _delta_x(self) -> float:
        """Longueur Δx pour le calcul du flux de cisaillement. Par défaut = z/2."""
        if self.__delta_x is not None and self.__delta_x > 0:
            return self.__delta_x
        return self.z / 2.0 if self.z > 0 else 1.0

    @property
    def _cot_theta_f(self) -> float:
        """cotθf pour la table. Défaut = 1.0 (θf=45°), valeur conservative."""
        if self.__cot_theta_f is not None:
            return max(1.0, min(self.__cot_theta_f, 2.0))
        return 1.0

    @property
    def v_ed_flange(self) -> float:
        """
        Flux de cisaillement longitudinal dans la table vEd [N/mm²] — §6.2.4(3)

        Approche simplifiée :
            ΔFd = (beff - bw)/(2·beff) · Ved · z / Δx  ... simplifié en :
            vEd = ΔFd / (hf · Δx)

        On utilise : vEd ≈ Ved · (beff - bw) / (2 · beff) / hf
        (approche conservative par variation linéaire de l'effort normal dans la table
        sur une demi-portée de cisaillement Δx = z/2)
        """
        if not self.__is_T or self.__hf <= 0 or self.__beff <= 0:
            return 0.0
        # ΔFd sur Δx : ΔFd/Δx ≈ Ved · (beff-bw)/(2·beff·z) * z  = Ved · (beff-bw)/(2·beff)
        # ... plus précisément :
        #   Effort dans une aile (demi-table) : Fd = σ_table · hf · (beff-bw)/2
        #   Variation sur Δx : ΔFd ≈ Ved/z · (beff - bw)·hf / (2·beff) · Δx   (proportionnel)
        # Puis vEd = ΔFd / (hf · Δx) = Ved · (beff - bw) / (2 · z · beff)

        z = self.z
        if z == 0:
            return 0.0
        return self.ved * (self.__beff - self.__bw) / (2.0 * z * self.__beff)

    def get_v_ed_flange(self, with_values: bool = False) -> FormulaResult:
        r = self.v_ed_flange
        fv = ""
        if with_values:
            if self.__is_T and self.__hf > 0:
                fv = (
                    f"vEd = Ved·(beff-bw)/(2·z·beff)\n"
                    f"    = {self.ved:.2f}×({self.__beff:.1f}-{self.__bw:.1f})"
                    f"/(2×{self.z:.1f}×{self.__beff:.1f})\n"
                    f"    = {r:.6f} N/mm² ({r:.4f} MPa)"
                )
            else:
                fv = "Section non en T — vEd = 0"
        return FormulaResult(
            name="vEd,table",
            formula="vEd = Ved·(beff - bw) / (2·z·beff)",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — §6.2.4(3)",
        )

    @property
    def v_rd_flange_no_reinf(self) -> float:
        """
        Résistance sans armature transversale de table :
        k · fctd  avec k = 0.4 (table comprimée) — §6.2.4(4) simplifié.
        fctd = fctk_005 / γc  (ou αct·fctk,0.05/γc — αct souvent = 1.0)
        """
        if self.__gamma_c == 0 or self.__fctk_005 == 0:
            return 0.0
        fctd = self.__fctk_005 / self.__gamma_c
        return 0.4 * fctd  # k = 0.4 pour table comprimée (valeur conservatrice)

    def get_v_rd_flange_no_reinf(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd_flange_no_reinf
        fv = ""
        if with_values:
            fctd = self.__fctk_005 / self.__gamma_c if self.__gamma_c else 0.0
            fv = (f"vRd,table = k·fctd = 0.4 × fctk_005/γc = 0.4 × {self.__fctk_005:.2f}/{self.__gamma_c}"
                  f" = 0.4 × {fctd:.4f} = {r:.4f} MPa")
        return FormulaResult(
            name="vRd,table",
            formula="vRd,table = k · fctd  (k=0.4)",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — §6.2.4(4)",
        )

    @property
    def armature_table_requise(self) -> bool:
        """True si vEd > vRd (armature de couture table/âme nécessaire)"""
        if not self.__is_T:
            return False
        return self.v_ed_flange > self.v_rd_flange_no_reinf

    # --- Asf/sf (armature de couture) ---
    @property
    def asf_sf_req(self) -> float:
        """(Asf/sf)_req = vEd·hf / (fyd·cotθf) [mm²/mm] — §6.2.4(4)"""
        if not self.__is_T or self.__hf <= 0:
            return 0.0
        cot_f = self._cot_theta_f
        denom = self.__fyd * cot_f
        if denom == 0:
            return float("inf")
        return self.v_ed_flange * self.__hf / denom

    def get_asf_sf_req(self, with_values: bool = False) -> FormulaResult:
        r = self.asf_sf_req
        fv = ""
        if with_values:
            cot_f = self._cot_theta_f
            fv = (f"(Asf/sf)_req = vEd·hf/(fyd·cotθf) = {self.v_ed_flange:.6f}×{self.__hf:.1f}"
                  f"/({self.__fyd:.2f}×{cot_f:.4f}) = {r:.6f} mm²/mm")
        return FormulaResult(
            name="(Asf/sf)_req",
            formula="(Asf/sf)_req = vEd · hf / (fyd · cotθf)",
            formula_values=fv,
            result=r,
            unit="mm²/mm",
            ref="EC2 — §6.2.4(4)",
        )

    # --- VRd,max table ---
    @property
    def v_rd_max_flange(self) -> float:
        """vRd,max,table = ν·fcd·sinθf·cosθf [MPa] — §6.2.4(4)"""
        if not self.__is_T:
            return 0.0
        nu = self.nu_1
        cot_f = self._cot_theta_f
        theta_f = math.atan(1.0 / cot_f) if cot_f != 0 else math.pi / 2.0
        return nu * self.__fcd * math.sin(theta_f) * math.cos(theta_f)

    def get_v_rd_max_flange(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd_max_flange
        fv = ""
        if with_values:
            cot_f = self._cot_theta_f
            theta_f = math.atan(1.0 / cot_f) if cot_f != 0 else math.pi / 2.0
            fv = (
                f"vRd,max,table = ν1·fcd·sinθf·cosθf = {self.nu_1:.6f}×{self.__fcd:.2f}"
                f"×sin({math.degrees(theta_f):.1f}°)×cos({math.degrees(theta_f):.1f}°) = {r:.4f} MPa"
            )
        return FormulaResult(
            name="vRd,max,table",
            formula="vRd,max,table = ν1 · fcd · sinθf · cosθf",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — §6.2.4(4)",
        )

    @property
    def flange_ok(self) -> bool:
        """True si la table est vérifiée (vEd ≤ vRd,max,table)"""
        if not self.__is_T:
            return True
        return self.v_ed_flange <= self.v_rd_max_flange

    # ═══════════════════════════════════════════════════════════════════════
    #  VÉRIFICATIONS GLOBALES
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def v_rd(self) -> float:
        """
        Résistance à l'effort tranchant de calcul VRd [N].

        • Si Ved ≤ VRd,c → VRd = VRd,c
        • Sinon → VRd = min(VRd,s , VRd,max)
        """
        if not self.armature_requise:
            return self.v_rd_c
        vrs = self.v_rd_s
        vrm = self.v_rd_max
        if vrs > 0:
            return min(vrs, vrm)
        # pas d'armature fournie → on retourne VRd,max (pour dimensionnement)
        return vrm

    def get_v_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd
        fv = ""
        if with_values:
            if not self.armature_requise:
                fv = f"Ved ≤ VRd,c → VRd = VRd,c = {r:.2f} N"
            else:
                vrs = self.v_rd_s
                vrm = self.v_rd_max
                if vrs > 0:
                    fv = (f"VRd = min(VRd,s ; VRd,max) = min({vrs:.2f} ; {vrm:.2f}) "
                          f"= {r:.2f} N")
                else:
                    fv = f"Asw/s non fourni → VRd = VRd,max = {r:.2f} N"
        return FormulaResult(
            name="VRd",
            formula="VRd = VRd,c si Ved ≤ VRd,c , sinon min(VRd,s ; VRd,max)",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC2 — §6.2",
        )

    @property
    def verif(self) -> float:
        """Taux de travail Ved / VRd"""
        if self.v_rd == 0:
            return float("inf")
        return round(self.ved / self.v_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si Ved ≤ VRd (et bielle OK et table OK)"""
        ok = self.verif <= 1.0
        if self.__is_T:
            ok = ok and self.flange_ok
        return ok

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (f"Ved / VRd = {self.ved:.2f} / {self.v_rd:.2f} "
                  f"= {r:.4f} ≤ 1.0 → {status}")
            if self.__is_T:
                fl_status = "OK ✓" if self.flange_ok else "NON VÉRIFIÉ ✗"
                fv += f"\nJonction table/âme : vEd={self.v_ed_flange:.4f} ≤ vRd,max={self.v_rd_max_flange:.4f} → {fl_status}"
        return FormulaResult(
            name="Ved/VRd",
            formula="Ved / VRd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §6.2",
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  REPORT
    # ═══════════════════════════════════════════════════════════════════════

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes du calcul.
        """
        fc = FormulaCollection(
            title="Vérification à l'effort tranchant",
            ref="EC2 — §6.2",
        )

        # Réduction près de l'appui
        if self.__av is not None:
            fc.add(self.get_beta_av(with_values=with_values))
        fc.add(self.get_ved(with_values=with_values))

        # §6.2.2 — sans armature
        fc.add(self.get_k_factor(with_values=with_values))
        fc.add(self.get_rho_l(with_values=with_values))
        fc.add(self.get_sigma_cp(with_values=with_values))
        fc.add(self.get_CRd_c(with_values=with_values))
        fc.add(self.get_v_min(with_values=with_values))
        fc.add(self.get_v_rd_c(with_values=with_values))

        # §6.2.3 — avec armature (si nécessaire)
        if self.armature_requise:
            fc.add(self.get_nu_1(with_values=with_values))
            fc.add(self.get_cot_theta(with_values=with_values))
            fc.add(self.get_v_rd_max(with_values=with_values))

            if self.__Asw is not None and self.__s is not None:
                fc.add(self.get_v_rd_s(with_values=with_values))

            # Dimensionnement
            fc.add(self.get_asw_s_req(with_values=with_values))
            fc.add(self.get_rho_w_min(with_values=with_values))
            fc.add(self.get_asw_s_min(with_values=with_values))
            fc.add(self.get_asw_s_calc(with_values=with_values))
            fc.add(self.get_s_l_max(with_values=with_values))
            fc.add(self.get_s_t_max(with_values=with_values))
            fc.add(self.get_delta_ftd(with_values=with_values))

        # §6.2.4 — section en T
        if self.__is_T and self.__hf > 0:
            fc.add(self.get_v_ed_flange(with_values=with_values))
            fc.add(self.get_v_rd_flange_no_reinf(with_values=with_values))
            if self.armature_table_requise:
                fc.add(self.get_asf_sf_req(with_values=with_values))
            fc.add(self.get_v_rd_max_flange(with_values=with_values))

        # Résultat global
        fc.add(self.get_v_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))

        return fc

    # ═══════════════════════════════════════════════════════════════════════
    #  REPR
    # ═══════════════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return (
            f"EffortTranchant(Ved={self.ved:.2f}, VRd,c={self.v_rd_c:.2f}, "
            f"VRd,max={self.v_rd_max:.2f}, VRd,s={self.v_rd_s:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  FONCTIONS STANDALONE
# ═══════════════════════════════════════════════════════════════════════════════

def v_rd_c(
    bw: float,
    d: float,
    fck: float,
    As_l: float,
    Ned: float = 0.0,
    Ac: Optional[float] = None,
    gamma_c: float = 1.5,
    k1: float = 0.15,
    alpha_cc: float = 1.0,
) -> float:
    """
    Calcul rapide de VRd,c [N] — EN 1992-1-1 §6.2.2(1).

    Paramètres
    ----------
    bw    : largeur de l'âme [mm]
    d     : hauteur utile [mm]
    fck   : résistance caractéristique du béton [MPa]
    As_l  : section d'armature longitudinale tendue [mm²]
    Ned   : effort normal concomitant [N] (>0 = compression, défaut 0)
    Ac    : aire brute de la section [mm²] (défaut = bw·d/0.9 ≈ bw·h)
    gamma_c : coefficient partiel béton (défaut 1.5)
    k1    : coefficient k1 (défaut 0.15)
    alpha_cc : coefficient αcc (défaut 1.0)

    Retour
    ------
    VRd,c [N]
    """
    if bw <= 0 or d <= 0 or gamma_c == 0:
        return 0.0

    if Ac is None:
        # estimation : h ≈ d / 0.9
        Ac = bw * d / 0.9

    fcd = alpha_cc * fck / gamma_c
    k = min(1.0 + math.sqrt(200.0 / d), 2.0)
    rho_l = min(As_l / (bw * d), 0.02)
    sigma_cp = min(Ned / Ac, 0.2 * fcd) if Ac > 0 else 0.0
    CRd_c = 0.18 / gamma_c

    v_main = CRd_c * k * (100.0 * rho_l * fck) ** (1.0 / 3.0) + k1 * sigma_cp
    v_min_val = 0.035 * k ** 1.5 * fck ** 0.5 + k1 * sigma_cp

    return max(v_main, v_min_val) * bw * d


def v_rd_s(
    Asw: float,
    s: float,
    d: float,
    fywd: float,
    cot_theta: float = 2.5,
    alpha_deg: float = 90.0,
) -> float:
    """
    Calcul rapide de VRd,s [N] — EN 1992-1-1 §6.2.3(3).

    Paramètres
    ----------
    Asw       : section d'un cadre [mm²] (ex. 2 brins HA8 → 2×50.3)
    s         : espacement des cadres [mm]
    d         : hauteur utile [mm]
    fywd      : limite élastique de calcul des cadres [MPa]
    cot_theta : cotangente de l'angle des bielles (défaut 2.5)
    alpha_deg : angle des armatures d'effort tranchant [°] (défaut 90 = cadres droits)

    Retour
    ------
    VRd,s [N]
    """
    if s <= 0 or d <= 0:
        return 0.0

    z = 0.9 * d
    alpha_rad = math.radians(alpha_deg)

    if abs(alpha_deg - 90.0) < 1e-6:
        return (Asw / s) * z * fywd * cot_theta
    else:
        sin_a = math.sin(alpha_rad)
        cot_a = math.cos(alpha_rad) / sin_a if abs(sin_a) > 1e-12 else 0.0
        return (Asw / s) * z * fywd * (cot_theta + cot_a) * sin_a


def v_rd_max(
    bw: float,
    d: float,
    fck: float,
    cot_theta: float = 2.5,
    alpha_deg: float = 90.0,
    alpha_cw: float = 1.0,
    gamma_c: float = 1.5,
    alpha_cc: float = 1.0,
) -> float:
    """
    Calcul rapide de VRd,max [N] — EN 1992-1-1 §6.2.3(3).

    Paramètres
    ----------
    bw        : largeur de l'âme [mm]
    d         : hauteur utile [mm]
    fck       : résistance caractéristique du béton [MPa]
    cot_theta : cotangente de l'angle des bielles (défaut 2.5)
    alpha_deg : angle des armatures d'effort tranchant [°] (défaut 90)
    alpha_cw  : coefficient αcw (défaut 1.0, sans précontrainte)
    gamma_c   : coefficient partiel béton (défaut 1.5)
    alpha_cc  : coefficient αcc (défaut 1.0)

    Retour
    ------
    VRd,max [N]
    """
    if bw <= 0 or d <= 0 or gamma_c == 0:
        return 0.0

    z = 0.9 * d
    fcd = alpha_cc * fck / gamma_c
    nu1 = 0.6 * (1.0 - fck / 250.0)

    if abs(alpha_deg - 90.0) < 1e-6:
        # cadres droits
        tan_theta = 1.0 / cot_theta if cot_theta != 0 else float("inf")
        denom = cot_theta + tan_theta
        if denom == 0:
            return 0.0
        return alpha_cw * bw * z * nu1 * fcd / denom
    else:
        # armatures inclinées
        alpha_rad = math.radians(alpha_deg)
        sin_a = math.sin(alpha_rad)
        cot_a = math.cos(alpha_rad) / sin_a if abs(sin_a) > 1e-12 else 0.0
        denom = 1.0 + cot_theta ** 2
        if denom == 0:
            return 0.0
        return alpha_cw * bw * z * nu1 * fcd * (cot_theta + cot_a) / denom


def asw_requis(
    Ved: float,
    d: float,
    fywd: float,
    cot_theta: float = 2.5,
    alpha_deg: float = 90.0,
    fck: float = 25.0,
    fyk: float = 500.0,
    bw: float = 0.0,
) -> dict:
    """
    Dimensionnement rapide des armatures transversales — §6.2.3 + §9.2.2.

    Paramètres
    ----------
    Ved       : effort tranchant de calcul [N]
    d         : hauteur utile [mm]
    fywd      : limite élastique de calcul des cadres [MPa]
    cot_theta : cotangente de l'angle des bielles (défaut 2.5)
    alpha_deg : angle des armatures [°] (défaut 90)
    fck       : résistance caractéristique béton [MPa] (pour ρw,min)
    fyk       : limite élastique caractéristique acier [MPa] (pour ρw,min)
    bw        : largeur de l'âme [mm] (pour Asw/s min)

    Retour
    ------
    dict avec clés :
        - 'asw_s_req'  : (Asw/s) requis [mm²/mm]
        - 'asw_s_min'  : (Asw/s) minimum §9.2.2 [mm²/mm]
        - 'asw_s_calc' : max des deux [mm²/mm]
        - 'rho_w_min'  : taux minimal ρw,min [-]
        - 's_l_max'    : espacement longitudinal max [mm]
        - 's_t_max'    : espacement transversal max [mm]
        - 'delta_ftd'  : effort de décalage [N]
    """
    Ved = abs(Ved)
    z = 0.9 * d
    alpha_rad = math.radians(alpha_deg)

    # --- (Asw/s) requis ---
    if abs(alpha_deg - 90.0) < 1e-6:
        denom = z * fywd * cot_theta
        asw_s_req = Ved / denom if denom > 0 else float("inf")
    else:
        sin_a = math.sin(alpha_rad)
        cot_a = math.cos(alpha_rad) / sin_a if abs(sin_a) > 1e-12 else 0.0
        denom = z * fywd * (cot_theta + cot_a) * sin_a
        asw_s_req = Ved / denom if denom > 0 else float("inf")

    # --- ρw,min et (Asw/s)_min ---
    rho_w_min = 0.08 * math.sqrt(fck) / fyk if fyk > 0 else 0.0
    asw_s_min = rho_w_min * bw

    # --- (Asw/s) de calcul ---
    asw_s_calc = max(asw_s_req, asw_s_min)

    # --- espacements max ---
    cot_a = 0.0
    if abs(alpha_deg - 90.0) > 1e-6:
        sin_a = math.sin(alpha_rad)
        cot_a = math.cos(alpha_rad) / sin_a if abs(sin_a) > 1e-12 else 0.0
    s_l_max = 0.75 * d * (1.0 + cot_a)
    s_t_max = min(0.75 * d, 600.0)

    # --- effort de décalage ---
    delta_ftd = 0.5 * Ved * (cot_theta - cot_a)

    return {
        "asw_s_req": asw_s_req,
        "asw_s_min": asw_s_min,
        "asw_s_calc": asw_s_calc,
        "rho_w_min": rho_w_min,
        "s_l_max": s_l_max,
        "s_t_max": s_t_max,
        "delta_ftd": delta_ftd,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  BLOC DE DÉMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("=" * 80)
    print("  EFFORT TRANCHANT — EN 1992-1-1 §6.2  —  Démonstration")
    print("=" * 80)

    # ──────────────────────────────────────────────────────────────────────
    #  CAS 1 : Ved < VRd,c  →  pas d'armature requise
    # ──────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 80)
    print("  CAS 1 : Faible effort tranchant — pas d'armature requise")
    print("─" * 80)

    cas1 = EffortTranchant(
        Ved=30_000,       # 30 kN
        bw=300,           # mm
        d=450,            # mm
        h=500,            # mm
        fck=25,           # MPa (C25/30)
        fyk=500,          # MPa (B500B)
        As_l=804,         # mm² (4 HA16)
        fctk_005=1.8,     # MPa
        gamma_c=1.5,
        gamma_s=1.15,
    )

    print(f"\n{cas1}")
    print(f"  Armature transversale requise : {cas1.armature_requise}")
    print(f"  VRd,c = {cas1.v_rd_c / 1000:.2f} kN")
    print(f"  Ved   = {cas1.ved / 1000:.2f} kN")
    print(f"  Taux  = {cas1.verif:.4f}  →  {'OK ✓' if cas1.is_ok else 'NON ✗'}")

    rapport1 = cas1.report(with_values=True)
    print(f"\n  Rapport ({len(rapport1)} étapes) :")
    for fr in rapport1:
        print(f"    • {fr.name} = {fr.result:.4f} {fr.unit}  [{fr.ref}]")
        if fr.formula_values:
            for line in fr.formula_values.split("\n"):
                print(f"        {line}")

    # ──────────────────────────────────────────────────────────────────────
    #  CAS 2 : Dimensionnement des cadres (cotθ optimal)
    # ──────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 80)
    print("  CAS 2 : Dimensionnement des armatures transversales")
    print("─" * 80)

    cas2 = EffortTranchant(
        Ved=250_000,      # 250 kN
        bw=300,           # mm
        d=540,            # mm
        h=600,            # mm
        fck=30,           # MPa (C30/37)
        fyk=500,          # MPa
        As_l=1_257,       # mm² (4 HA20)
        fctk_005=2.0,     # MPa
        gamma_c=1.5,
        gamma_s=1.15,
    )

    print(f"\n{cas2}")
    print(f"  Armature requise : {cas2.armature_requise}")
    print(f"  VRd,c    = {cas2.v_rd_c / 1000:.2f} kN")
    print(f"  cotθ opt = {cas2.cot_theta:.4f}  (θ = {cas2.theta_deg:.1f}°)")
    print(f"  VRd,max  = {cas2.v_rd_max / 1000:.2f} kN")
    print(f"  (Asw/s)_req  = {cas2.asw_s_req:.4f} mm²/mm")
    print(f"  (Asw/s)_min  = {cas2.asw_s_min:.4f} mm²/mm")
    print(f"  (Asw/s)_calc = {cas2.asw_s_calc:.4f} mm²/mm")
    print(f"  s_l,max      = {cas2.s_l_max:.1f} mm")
    print(f"  s_t,max      = {cas2.s_t_max:.1f} mm")
    print(f"  ΔFtd         = {cas2.delta_ftd / 1000:.2f} kN")

    # Proposition de ferraillage
    Asw_prop = 2 * 50.27  # 2 brins HA8 = 100.5 mm²
    s_prop = Asw_prop / cas2.asw_s_calc
    s_prop = min(s_prop, cas2.s_l_max)
    s_prop = 25 * math.floor(s_prop / 25)  # arrondi à 25 mm inférieur
    print(f"\n  → Proposition : HA8 — 2 brins, s = {s_prop:.0f} mm")
    print(f"    Asw/s fourni = {Asw_prop / s_prop:.4f} mm²/mm "
          f"≥ {cas2.asw_s_calc:.4f} mm²/mm → "
          f"{'OK ✓' if Asw_prop / s_prop >= cas2.asw_s_calc else 'NON ✗'}")

    # ──────────────────────────────────────────────────────────────────────
    #  CAS 3 : Vérification d'un ferraillage existant
    # ──────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 80)
    print("  CAS 3 : Vérification d'un ferraillage existant (Asw, s donnés)")
    print("─" * 80)

    cas3 = EffortTranchant(
        Ved=320_000,      # 320 kN
        bw=350,           # mm
        d=510,            # mm
        h=560,            # mm
        fck=30,           # MPa
        fyk=500,          # MPa
        As_l=1_571,       # mm² (5 HA20)
        fctk_005=2.0,     # MPa
        gamma_c=1.5,
        gamma_s=1.15,
        # --- ferraillage transversal existant ---
        Asw=2 * 50.27,   # 2 brins HA8 = 100.5 mm²
        s=175,            # mm
    )

    print(f"\n{cas3}")
    print(f"  VRd,c   = {cas3.v_rd_c / 1000:.2f} kN")
    print(f"  cotθ    = {cas3.cot_theta:.4f}  (θ = {cas3.theta_deg:.1f}°)")
    print(f"  VRd,s   = {cas3.v_rd_s / 1000:.2f} kN")
    print(f"  VRd,max = {cas3.v_rd_max / 1000:.2f} kN")
    print(f"  VRd     = {cas3.v_rd / 1000:.2f} kN")
    print(f"  Taux    = {cas3.verif:.4f}  →  {'OK ✓' if cas3.is_ok else 'NON ✗'}")

    # ──────────────────────────────────────────────────────────────────────
    #  CAS 4 : Section en T — jonction table/âme §6.2.4
    # ──────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 80)
    print("  CAS 4 : Section en T — vérification jonction table/âme (§6.2.4)")
    print("─" * 80)

    cas4 = EffortTranchant(
        Ved=400_000,      # 400 kN
        bw=250,           # mm  (âme)
        beff=1200,        # mm  (largeur efficace de table)
        hf=120,           # mm  (épaisseur de la table)
        d=650,            # mm
        h=700,            # mm
        fck=30,           # MPa
        fyk=500,          # MPa
        As_l=2_413,       # mm² (3 HA32)
        fctk_005=2.0,     # MPa
        gamma_c=1.5,
        gamma_s=1.15,
        is_T=True,
        # ferraillage transversal
        Asw=2 * 78.54,   # 2 brins HA10 = 157.1 mm²
        s=200,            # mm
        cot_theta_f=1.5,  # angle bielles dans la table
    )

    print(f"\n{cas4}")
    print(f"  Section en T : bw={250} mm, beff={1200} mm, hf={120} mm")
    print(f"  VRd,c    = {cas4.v_rd_c / 1000:.2f} kN")
    print(f"  cotθ     = {cas4.cot_theta:.4f}  (θ = {cas4.theta_deg:.1f}°)")
    print(f"  VRd,s    = {cas4.v_rd_s / 1000:.2f} kN")
    print(f"  VRd,max  = {cas4.v_rd_max / 1000:.2f} kN")
    print(f"\n  --- Jonction table/âme (§6.2.4) ---")
    print(f"  vEd,table         = {cas4.v_ed_flange:.4f} MPa")
    print(f"  vRd (sans arm.)   = {cas4.v_rd_flange_no_reinf:.4f} MPa")
    print(f"  Arm. table req.   = {cas4.armature_table_requise}")
    if cas4.armature_table_requise:
        print(f"  (Asf/sf)_req      = {cas4.asf_sf_req:.6f} mm²/mm")
    print(f"  vRd,max,table     = {cas4.v_rd_max_flange:.4f} MPa")
    print(f"  Table OK          = {cas4.flange_ok}")
    print(f"\n  Taux global = {cas4.verif:.4f}  →  {'OK ✓' if cas4.is_ok else 'NON ✗'}")

    # Rapport complet
    rapport4 = cas4.report(with_values=True)
    print(f"\n  Rapport complet ({len(rapport4)} étapes) :")
    for fr in rapport4:
        print(f"    • {fr.name} = {fr.result:.4f} {fr.unit}  [{fr.ref}]")

    # ──────────────────────────────────────────────────────────────────────
    #  Fonctions standalone
    # ──────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 80)
    print("  Fonctions standalone")
    print("─" * 80)

    vrdc = v_rd_c(bw=300, d=450, fck=25, As_l=804)
    print(f"\n  v_rd_c(bw=300, d=450, fck=25, As_l=804) = {vrdc / 1000:.2f} kN")

    vrds = v_rd_s(Asw=100.5, s=200, d=540, fywd=434.78, cot_theta=2.5)
    print(f"  v_rd_s(Asw=100.5, s=200, d=540, fywd=434.78, cotθ=2.5) = {vrds / 1000:.2f} kN")

    vrdm = v_rd_max(bw=300, d=540, fck=30, cot_theta=2.5)
    print(f"  v_rd_max(bw=300, d=540, fck=30, cotθ=2.5) = {vrdm / 1000:.2f} kN")

    dim = asw_requis(Ved=250_000, d=540, fywd=434.78, cot_theta=2.5, fck=30, fyk=500, bw=300)
    print(f"\n  asw_requis(Ved=250kN, d=540, fywd=434.78, cotθ=2.5) :")
    for k, v in dim.items():
        print(f"    {k:15s} = {v:.6f}")

    print("\n" + "=" * 80)
    print("  Fin de la démonstration")
    print("=" * 80)
