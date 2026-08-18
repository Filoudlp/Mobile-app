#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification au cisaillement selon EC3-1-1 §6.2.6
et réduction pour torsion selon §6.2.7(9).
"""
__all__ = ['Shear']

import math
from typing import TypeVar, Optional
from core.formula import FormulaResult, FormulaCollection

SecMatSteel = TypeVar('SecMatSteel')

# TODO — Implémentation future :
# - Calcul automatique de Av selon type de section (Tableau §6.2.6 (3))
# - Résistance au voilement par cisaillement §6.2.6 (6) → renvoi vers EC3-1-5
# - Torsion de Saint-Venant + torsion de gauchissement §6.2.7 complet
# - Cisaillement dans les sections ouvertes minces
# - Vérification cisaillement des âmes avec raidisseurs


class Shear:
    """
    Vérification au cisaillement — EC3-1-1 §6.2.6 & §6.2.7

    Calcule la résistance plastique au cisaillement Vpl,Rd, applique
    éventuellement une réduction pour torsion (Vpl,T,Rd) et vérifie
    que l'effort tranchant de calcul Ved ne dépasse pas la résistance.
    """

    def __init__(self, Ved: float = 0.0, axis: str = "z",
                 tau_t_ed: float = 0.0,
                 sec_mat: Optional[SecMatSteel] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        Ved : float
            Effort tranchant de calcul [N] (valeur absolue).
        axis : str
            Direction du cisaillement : "y" ou "z".
        tau_t_ed : float
            Contrainte de cisaillement due à la torsion [MPa].
            0 signifie pas de torsion.
        :param sec_mat:  Objet section_material (fy, fu, gamma_m0, gamma_m, A, Anet)
        **kwargs
            Valeurs alternatives : fy, gamma_m0, Av, Av_y, Av_z, hw, tw.
        """
        self.__ved = abs(Ved)
        self.__axis = axis.lower()
        self.__tau_t_ed = abs(tau_t_ed)

        # --- Matériau ---
        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__gamma_m0 = sec_mat.gamma_m0 if sec_mat else kwargs.get("gamma_m0", 1.0)

        # --- Section : aire de cisaillement ---
        if sec_mat:
            if self.__axis == "y":
                self.__Av = sec_mat.Av_y
            else:
                self.__Av = sec_mat.Av_z
        else:
            # Permet Av directement ou Av_y / Av_z
            self.__Av = kwargs.get("Av", 0.0)
            if self.__Av == 0.0:
                if self.__axis == "y":
                    self.__Av = kwargs.get("Av_y", 0.0)
                else:
                    self.__Av = kwargs.get("Av_z", 0.0)

        self.__hw = sec_mat.hw if sec_mat and hasattr(sec_mat, 'hw') else kwargs.get("hw", 0.0)
        self.__tw = sec_mat.tw if sec_mat else kwargs.get("tw", 0.0)

    # ==================================================================
    # Propriétés de base
    # ==================================================================

    @property
    def ved(self) -> float:
        """Effort tranchant de calcul [N]."""
        return self.__ved

    @property
    def av(self) -> float:
        """Aire de cisaillement [mm²]."""
        return self.__Av

    # ==================================================================
    # Résistance plastique au cisaillement — §6.2.6
    # ==================================================================

    @property
    def vpl_rd(self) -> float:
        """Vpl,Rd = Av · (fy / √3) / γM0  [N] — §6.2.6 (2)."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Av * (self.__fy / math.sqrt(3)) / self.__gamma_m0

    def get_vpl_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Vpl,Rd."""
        r = self.vpl_rd
        fy_sqrt3 = self.__fy / math.sqrt(3)
        fv = ""
        if with_values:
            fv = (f"Vpl,Rd = {self.__Av:.2f} × ({self.__fy:.2f} / √3) / "
                  f"{self.__gamma_m0} = {self.__Av:.2f} × {fy_sqrt3:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N")
        return FormulaResult(
            name="Vpl,Rd",
            formula="Vpl,Rd = Av · (fy / √3) / γM0",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.2.6 (2)",
        )

    # ==================================================================
    # Réduction pour torsion — §6.2.7 (9)
    # ==================================================================

    @property
    def rho_torsion(self) -> float:
        """
        Facteur de réduction pour torsion ρ_t.

        ρ_t = 1 - τ_t,Ed / (fy / (√3 · γM0))
        Minimum 0.
        """
        if self.__tau_t_ed == 0:
            return 1.0
        tau_max = self.__fy / (math.sqrt(3) * self.__gamma_m0)
        if tau_max == 0:
            return 0.0
        return max(1.0 - self.__tau_t_ed / tau_max, 0.0)

    @property
    def vpl_t_rd(self) -> float:
        """Vpl,T,Rd = ρ_t · Vpl,Rd  [N] — §6.2.7 (9)."""
        return self.rho_torsion * self.vpl_rd

    def get_vpl_t_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Vpl,T,Rd."""
        r = self.vpl_t_rd
        fv = ""
        if with_values:
            fv = (f"Vpl,T,Rd = {self.rho_torsion:.4f} × {self.vpl_rd:.2f} "
                  f"= {r:.2f} N")
        return FormulaResult(
            name="Vpl,T,Rd",
            formula="Vpl,T,Rd = ρ_t · Vpl,Rd",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.2.7 (9)",
        )

    def get_rho_torsion(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour le facteur de réduction torsion."""
        r = self.rho_torsion
        tau_max = self.__fy / (math.sqrt(3) * self.__gamma_m0) if self.__gamma_m0 != 0 else 0.0
        fv = ""
        if with_values:
            fv = (f"ρ_t = 1 - τ_t,Ed / (fy / (√3·γM0)) = 1 - "
                  f"{self.__tau_t_ed:.2f} / {tau_max:.2f} = {r:.4f}")
        return FormulaResult(
            name="ρ_t",
            formula="ρ_t = 1 - τ_t,Ed / (fy / (√3·γM0))",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.7 (9)",
        )

    # ==================================================================
    # Résistance de calcul finale
    # ==================================================================

    @property
    def v_rd(self) -> float:
        """Résistance de calcul finale [N]. Vpl,Rd ou Vpl,T,Rd."""
        if self.__tau_t_ed > 0:
            return self.vpl_t_rd
        return self.vpl_rd

    def get_v_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la résistance de calcul V,Rd."""
        r = self.v_rd
        if self.__tau_t_ed > 0:
            name = "Vpl,T,Rd"
            formula = "V,Rd = Vpl,T,Rd  (torsion présente)"
        else:
            name = "Vpl,Rd"
            formula = "V,Rd = Vpl,Rd  (sans torsion)"
        fv = ""
        if with_values:
            fv = f"V,Rd = {r:.2f} N"
        return FormulaResult(
            name=name,
            formula=formula,
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.2.6 / §6.2.7",
        )

    # ==================================================================
    # Vérification
    # ==================================================================

    @property
    def verif(self) -> float:
        """Taux de travail Ved / V,Rd."""
        if self.v_rd == 0:
            return float('inf')
        return round(self.__ved / self.v_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si Ved / V,Rd ≤ 1.0."""
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Ved / V,Rd ≤ 1.0."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (f"Ved / V,Rd = {self.__ved:.2f} / {self.v_rd:.2f} "
                  f"= {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="Ved/V,Rd",
            formula="Ved / V,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.6 (1)",
            is_check=True,
        )

    @property
    def is_high_shear(self) -> bool:
        """True si Ved > 0.5 · Vpl,Rd (cisaillement élevé, utile pour combined.py)."""
        return self.__ved > 0.5 * self.vpl_rd

    # ==================================================================
    # Rapport
    # ==================================================================

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection regroupant toutes les étapes."""
        fc = FormulaCollection(
            title=f"Vérification au cisaillement (axe {self.__axis})",
            ref="EC3-1-1 — §6.2.6 / §6.2.7",
        )
        fc.add(self.get_vpl_rd(with_values=with_values))
        if self.__tau_t_ed > 0:
            fc.add(self.get_rho_torsion(with_values=with_values))
            fc.add(self.get_vpl_t_rd(with_values=with_values))
        fc.add(self.get_v_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (f"Shear(Ved={self.__ved:.2f}, V,Rd={self.v_rd:.2f}, "
                f"taux={self.verif:.4f}, ok={self.is_ok}, "
                f"high_shear={self.is_high_shear})")


# ----------------------------------------------------------------------
# Fonction standalone
# ----------------------------------------------------------------------

def vpl_rd(Av: float, fy: float, gamma_m0: float = 1.0) -> float:
    """
    Calcul rapide de Vpl,Rd sans instancier la classe.

    Parameters
    ----------
    Av : float
        Aire de cisaillement [mm²].
    fy : float
        Limite d'élasticité [MPa].
    gamma_m0 : float
        Coefficient de sécurité γM0 (défaut 1.0).

    Returns
    -------
    float
        Vpl,Rd [N].
    """
    return Av * (fy / math.sqrt(3)) / gamma_m0


# ----------------------------------------------------------------------
# Debug
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # IPE 300, S235
    # Av_z ≈ 2567 mm² (hw · tw = 248.6 × 7.1 ≈ 1765, mais catalogue → ~2567)

    print("=" * 60)
    print("CAS 1 : Cisaillement simple Ved = 200 kN")
    print("=" * 60)
    s1 = Shear(
        Ved=200e3,
        axis="z",
        fy=235,
        gamma_m0=1.0,
        Av=2567,
    )
    print(s1)
    print(s1.report(with_values=True))

    print()
    print("=" * 60)
    print("CAS 2 : Cisaillement + torsion τ_t,Ed = 20 MPa")
    print("=" * 60)
    s2 = Shear(
        Ved=200e3,
        axis="z",
        tau_t_ed=20.0,
        fy=235,
        gamma_m0=1.0,
        Av=2567,
    )
    print(s2)
    print(s2.report(with_values=True))
