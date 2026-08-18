#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Voilement par cisaillement de l'âme — EN 1993-1-5 §5.

Vérification unitaire indépendante (même principe que ``elu.shear`` /
``elu.bending``) : accepte soit un ``sec_mat``, soit des ``**kwargs``
(fy, hw, tw, …).

Déclenchement — §5.1(2) :
    Vérification requise si  hw/tw > 72·ε/η      (âme non raidie)
                          ou hw/tw > 31·ε/η·√kτ  (âme raidie)
    avec ε = √(235/fy) et η = 1,20 (aciers ≤ S460) ou 1,00 (au-delà).

Résistance — §5.2 :
    Vb,Rd = Vbw,Rd + Vbf,Rd  ≤  η·fyw·hw·tw / (√3·γM1)      (5.1)
    Vbw,Rd = χw·fyw·hw·tw / (√3·γM1)                        (5.2)

    La contribution des semelles Vbf,Rd (§5.4) est hors périmètre de cette
    version : elle est négligée (Vbf,Rd = 0), ce qui est sécuritaire.

Contribution de l'âme — §5.3, Tableau 5.1 :
    λ̄w = hw / (86,4·tw·ε)          (5.5)  raidisseurs d'appui seulement
    λ̄w = hw / (37,4·tw·ε·√kτ)      (5.6)  avec raidisseurs intermédiaires

    Montant d'extrémité RIGIDE :
        λ̄w < 0,83/η          → χw = η
        0,83/η ≤ λ̄w < 1,08   → χw = 0,83/λ̄w
        λ̄w ≥ 1,08            → χw = 1,37/(0,7 + λ̄w)
    Montant d'extrémité NON RIGIDE :
        λ̄w < 0,83/η          → χw = η
        λ̄w ≥ 0,83/η          → χw = 0,83/λ̄w

Coefficient de voilement kτ — Annexe A.3 (âme sans raidisseur longitudinal) :
    kτ = 5,34 + 4,00·(hw/a)²   si a/hw ≥ 1
    kτ = 4,00 + 5,34·(hw/a)²   si a/hw < 1
    (a = espacement des raidisseurs transversaux ; sans raidisseur
    intermédiaire, a → ∞ donne kτ = 5,34.)
    Ces expressions coïncident avec la figure 8 de la SIA 263 §4.5.4 —
    les deux normes se recoupent sur ce point.
"""

__all__ = ['ShearBuckling', 'k_tau', 'eta_shear']

import math
from typing import Optional, TypeVar

from core.formula import FormulaResult, FormulaCollection

SecMatSteel = TypeVar('SecMatSteel')


def eta_shear(fy: float) -> float:
    """η — §5.1(2) NOTE 2 : 1,20 jusqu'à S460 inclus, 1,00 au-delà."""
    return 1.20 if fy <= 460.0 else 1.00


def k_tau(hw: float, a: Optional[float] = None) -> float:
    """
    Coefficient de voilement par cisaillement kτ — Annexe A.3.

    :param hw: Hauteur de l'âme [mm].
    :param a: Espacement des raidisseurs transversaux [mm].
        ``None`` ou 0 = pas de raidisseur intermédiaire → kτ = 5,34.
    """
    if not a or a <= 0 or hw <= 0:
        return 5.34
    alpha = a / hw
    if alpha >= 1.0:
        return 5.34 + 4.00 / alpha ** 2
    return 4.00 + 5.34 / alpha ** 2


class ShearBuckling:
    """
    Vérification au voilement par cisaillement de l'âme — EN 1993-1-5 §5.

    :param Ved: Effort tranchant de calcul [N] (valeur absolue).
    :param sec_mat: Objet section-matériau (fy, hw, tw, gamma_m1).
    :param a: Espacement des raidisseurs transversaux [mm] (None = aucun).
    :param rigid_end_post: ``True`` si montant d'extrémité rigide (§9.3.1).
    :param kwargs: Valeurs alternatives — fy, hw, tw, gamma_m1.
    """

    def __init__(
        self,
        Ved: float = 0.0,
        sec_mat: Optional[SecMatSteel] = None,
        a: Optional[float] = None,
        rigid_end_post: bool = True,
        **kwargs,
    ) -> None:
        self.__ved = abs(Ved)
        self.__a = a
        self.__rigid_end_post = rigid_end_post

        # --- Matériau ---
        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__gamma_m1 = (
            sec_mat.gamma_m1 if sec_mat else kwargs.get("gamma_m1", 1.0)
        )

        # --- Section ---
        if sec_mat is not None and hasattr(sec_mat, "hw"):
            self.__hw = sec_mat.hw
        else:
            self.__hw = kwargs.get("hw", 0.0)
        self.__tw = sec_mat.tw if sec_mat else kwargs.get("tw", 0.0)

    # ==================================================================
    # Paramètres de base
    # ==================================================================

    @property
    def ved(self) -> float:
        """Effort tranchant de calcul [N]."""
        return self.__ved

    @property
    def hw(self) -> float:
        """Hauteur de l'âme [mm]."""
        return self.__hw

    @property
    def tw(self) -> float:
        """Épaisseur de l'âme [mm]."""
        return self.__tw

    @property
    def epsilon(self) -> float:
        """ε = √(235/fy)."""
        if self.__fy <= 0:
            return 0.0
        return math.sqrt(235.0 / self.__fy)

    @property
    def eta(self) -> float:
        """η — §5.1(2)."""
        return eta_shear(self.__fy)

    @property
    def k_tau(self) -> float:
        """Coefficient de voilement kτ — Annexe A.3."""
        return k_tau(self.__hw, self.__a)

    @property
    def is_stiffened(self) -> bool:
        """True si des raidisseurs transversaux intermédiaires existent."""
        return bool(self.__a and self.__a > 0)

    # ==================================================================
    # Déclenchement de la vérification — §5.1(2)
    # ==================================================================

    @property
    def slenderness(self) -> float:
        """Élancement d'âme hw/tw."""
        if self.__tw == 0:
            return float('inf')
        return self.__hw / self.__tw

    @property
    def slenderness_limit(self) -> float:
        """Limite au-delà de laquelle le voilement doit être vérifié."""
        if self.eta == 0:
            return float('inf')
        if self.is_stiffened:
            return 31.0 * self.epsilon / self.eta * math.sqrt(self.k_tau)
        return 72.0 * self.epsilon / self.eta

    @property
    def is_required(self) -> bool:
        """True si la vérification au voilement est requise — §5.1(2)."""
        return self.slenderness > self.slenderness_limit

    def get_required(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour le critère de déclenchement."""
        limit_txt = (
            "31·ε/η·√kτ" if self.is_stiffened else "72·ε/η"
        )
        fv = ""
        if with_values:
            verdict = (
                "vérification REQUISE" if self.is_required
                else "vérification NON requise (âme trapue)"
            )
            fv = (
                f"hw/tw = {self.__hw:.1f} / {self.__tw:.2f} = "
                f"{self.slenderness:.2f}  vs  {limit_txt} = "
                f"{self.slenderness_limit:.2f} → {verdict}"
            )
        return FormulaResult(
            name="hw/tw",
            formula=f"Voilement à vérifier si hw/tw > {limit_txt}",
            formula_values=fv,
            result=round(self.slenderness, 4),
            unit="-",
            ref="EN 1993-1-5 — §5.1 (2)",
        )

    # ==================================================================
    # Élancement réduit λ̄w — §5.3 (3)
    # ==================================================================

    @property
    def lambda_bar_w(self) -> float:
        """λ̄w — formules (5.5) / (5.6)."""
        denom_base = self.__tw * self.epsilon
        if denom_base == 0:
            return float('inf')
        if self.is_stiffened:
            return self.__hw / (37.4 * denom_base * math.sqrt(self.k_tau))
        return self.__hw / (86.4 * denom_base)

    def get_lambda_bar_w(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour λ̄w."""
        r = self.lambda_bar_w
        if self.is_stiffened:
            formula = "λ̄w = hw / (37,4·tw·ε·√kτ)"
            ref = "EN 1993-1-5 — §5.3 (3), éq. (5.6)"
            fv = (
                f"λ̄w = {self.__hw:.1f} / (37,4 × {self.__tw:.2f} × "
                f"{self.epsilon:.4f} × √{self.k_tau:.3f}) = {r:.4f}"
            ) if with_values else ""
        else:
            formula = "λ̄w = hw / (86,4·tw·ε)"
            ref = "EN 1993-1-5 — §5.3 (3), éq. (5.5)"
            fv = (
                f"λ̄w = {self.__hw:.1f} / (86,4 × {self.__tw:.2f} × "
                f"{self.epsilon:.4f}) = {r:.4f}"
            ) if with_values else ""
        return FormulaResult(
            name="λ̄w",
            formula=formula,
            formula_values=fv,
            result=round(r, 4),
            unit="-",
            ref=ref,
        )

    # ==================================================================
    # Facteur de réduction χw — Tableau 5.1
    # ==================================================================

    @property
    def chi_w(self) -> float:
        """χw — contribution de l'âme, Tableau 5.1."""
        lam = self.lambda_bar_w
        eta = self.eta
        if eta == 0 or lam == 0:
            return 0.0
        if lam < 0.83 / eta:
            return eta
        if self.__rigid_end_post:
            if lam < 1.08:
                return 0.83 / lam
            return 1.37 / (0.7 + lam)
        return 0.83 / lam

    def get_chi_w(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour χw."""
        r = self.chi_w
        lam = self.lambda_bar_w
        eta = self.eta
        post = "rigide" if self.__rigid_end_post else "non rigide"
        fv = ""
        if with_values:
            if lam < 0.83 / eta:
                branch = f"λ̄w = {lam:.4f} < 0,83/η = {0.83 / eta:.4f} → χw = η = {r:.4f}"
            elif self.__rigid_end_post and lam >= 1.08:
                branch = (
                    f"λ̄w = {lam:.4f} ≥ 1,08 (montant rigide) → "
                    f"χw = 1,37/(0,7 + {lam:.4f}) = {r:.4f}"
                )
            else:
                branch = (
                    f"λ̄w = {lam:.4f} → χw = 0,83/{lam:.4f} = {r:.4f}"
                )
            fv = branch
        return FormulaResult(
            name="χw",
            formula=f"χw — Tableau 5.1 (montant d'extrémité {post})",
            formula_values=fv,
            result=round(r, 4),
            unit="-",
            ref="EN 1993-1-5 — §5.3, Tableau 5.1",
        )

    # ==================================================================
    # Résistances — §5.2
    # ==================================================================

    @property
    def vbw_rd(self) -> float:
        """Vbw,Rd = χw·fyw·hw·tw / (√3·γM1)  [N] — éq. (5.2)."""
        if self.__gamma_m1 == 0:
            return 0.0
        return (
            self.chi_w * self.__fy * self.__hw * self.__tw
            / (math.sqrt(3) * self.__gamma_m1)
        )

    @property
    def v_cap(self) -> float:
        """Plafond η·fyw·hw·tw / (√3·γM1)  [N] — éq. (5.1)."""
        if self.__gamma_m1 == 0:
            return 0.0
        return (
            self.eta * self.__fy * self.__hw * self.__tw
            / (math.sqrt(3) * self.__gamma_m1)
        )

    @property
    def vb_rd(self) -> float:
        """
        Vb,Rd = Vbw,Rd + Vbf,Rd ≤ plafond  [N] — éq. (5.1).

        Vbf,Rd (contribution des semelles, §5.4) négligée — sécuritaire.
        """
        return min(self.vbw_rd, self.v_cap)

    def get_vbw_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Vbw,Rd."""
        r = self.vbw_rd
        fv = ""
        if with_values:
            fv = (
                f"Vbw,Rd = {self.chi_w:.4f} × {self.__fy:.1f} × "
                f"{self.__hw:.1f} × {self.__tw:.2f} / (√3 × "
                f"{self.__gamma_m1}) = {r:.2f} N"
            )
        return FormulaResult(
            name="Vbw,Rd",
            formula="Vbw,Rd = χw·fyw·hw·tw / (√3·γM1)",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EN 1993-1-5 — §5.2 (1), éq. (5.2)",
        )

    def get_vb_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Vb,Rd (avec plafond)."""
        r = self.vb_rd
        fv = ""
        if with_values:
            capped = self.vbw_rd > self.v_cap
            note = (
                f" (plafonné à η·fyw·hw·tw/(√3·γM1) = {self.v_cap:.2f} N)"
                if capped else ""
            )
            fv = f"Vb,Rd = {r:.2f} N{note}"
        return FormulaResult(
            name="Vb,Rd",
            formula="Vb,Rd = Vbw,Rd (+ Vbf,Rd négligé) ≤ η·fyw·hw·tw/(√3·γM1)",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EN 1993-1-5 — §5.2 (1), éq. (5.1)",
        )

    # ==================================================================
    # Vérification
    # ==================================================================

    @property
    def verif(self) -> float:
        """Taux de travail η3 = Ved / Vb,Rd."""
        if self.vb_rd == 0:
            return float('inf')
        return round(self.__ved / self.vb_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si Ved / Vb,Rd ≤ 1,0."""
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Ved / Vb,Rd ≤ 1,0 — §5.5."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"η3 = Ved / Vb,Rd = {self.__ved:.2f} / {self.vb_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="Ved/Vb,Rd",
            formula="η3 = Ved / Vb,Rd ≤ 1,0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EN 1993-1-5 — §5.5 (1)",
            is_check=True,
            limit=1.0,
        )

    # ==================================================================
    # Rapport
    # ==================================================================

    def report(self, with_values: bool = True) -> FormulaCollection:
        """FormulaCollection regroupant toutes les étapes."""
        fc = FormulaCollection(
            title="Voilement par cisaillement de l'âme",
            ref="EN 1993-1-5 — §5",
        )
        fc.add(self.get_required(with_values=with_values))
        if not self.is_required:
            return fc
        fc.add(self.get_lambda_bar_w(with_values=with_values))
        fc.add(self.get_chi_w(with_values=with_values))
        fc.add(self.get_vbw_rd(with_values=with_values))
        fc.add(self.get_vb_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"ShearBuckling(hw/tw={self.slenderness:.1f}, "
            f"requis={self.is_required}, λ̄w={self.lambda_bar_w:.4f}, "
            f"χw={self.chi_w:.4f}, Vb,Rd={self.vb_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 60

    print(f"\n{sep}")
    print("  CAS 1 : IPE 300 (âme trapue) — vérification non requise")
    print(sep)
    sb1 = ShearBuckling(Ved=200e3, fy=235.0, hw=278.6, tw=7.1, gamma_m1=1.0)
    print(f"  {sb1!r}")
    print(sb1.report(with_values=True))

    print(f"\n{sep}")
    print("  CAS 2 : PRS âme élancée hw=1200, tw=6 — sans raidisseur")
    print(sep)
    sb2 = ShearBuckling(Ved=400e3, fy=355.0, hw=1200.0, tw=6.0, gamma_m1=1.0)
    print(f"  {sb2!r}")
    print(sb2.report(with_values=True))

    print(f"\n{sep}")
    print("  CAS 3 : idem avec raidisseurs transversaux a = 1500 mm")
    print(sep)
    sb3 = ShearBuckling(
        Ved=400e3, fy=355.0, hw=1200.0, tw=6.0, gamma_m1=1.0, a=1500.0,
    )
    print(f"  {sb3!r}")
    print(f"  kτ = {sb3.k_tau:.4f}")
    print(sb3.report(with_values=True))

    print(f"\n{sep}")
    print("  CAS 4 : montant d'extrémité non rigide (même âme que CAS 2)")
    print(sep)
    sb4 = ShearBuckling(
        Ved=400e3, fy=355.0, hw=1200.0, tw=6.0, gamma_m1=1.0,
        rigid_end_post=False,
    )
    print(f"  {sb4!r}")

    print(f"\n{'=' * 60}")
    print("  FIN DES TESTS")
    print(f"{'=' * 60}")
