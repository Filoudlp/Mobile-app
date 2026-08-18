#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification à la flexion selon EC3-1-1 §6.2.5
et flexion biaxiale selon §6.2.9 (sans effort normal).

Couvre les sections de classes 1, 2 et 3.
"""
__all__ = ['Bending']

import math
from typing import TypeVar, Optional
from core.formula import FormulaResult, FormulaCollection

SecMatSteel = TypeVar('SecMatSteel')

# TODO — Implémentation future :
# - Sections de classe 4 : Mc,Rd = Weff · fy / γM0
# - Prise en compte des trous de boulons dans les semelles tendues §6.2.5 (4)-(6)
# - Flexion déviée avec section non symétrique
# - Déversement → voir buckling.py


class Bending:
    """
    Vérification à la flexion — EC3-1-1 §6.2.5 & §6.2.9 (N = 0)

    Calcule les moments résistants élastiques et plastiques dans les
    deux plans, détermine Mc,Rd selon la classe de section, et réalise
    la vérification biaxiale §6.2.9(6) sans effort normal.
    """

    def __init__(self, My_ed: float = 0.0, Mz_ed: float = 0.0,
                 sec_mat: Optional[SecMatSteel] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        My_ed : float
            Moment de calcul autour de y [N·mm] (valeur absolue).
        Mz_ed : float
            Moment de calcul autour de z [N·mm] (valeur absolue).
        section_class : int
            Classe de section (1, 2 ou 3).
        :param sec_mat:  Objet section_material (fy, fu, gamma_m0, gamma_m, A, Anet)
        **kwargs
            Valeurs alternatives : fy, gamma_m0, Wel_y, Wel_z,
            Wpl_y, Wpl_z, section_type, alpha, beta.
        """
        self.__my_ed = abs(My_ed)
        self.__mz_ed = abs(Mz_ed)
        self.__section_class = sec_mat.section_class if sec_mat else 1

        # --- Matériau ---
        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__gamma_m0 = sec_mat.gamma_m0 if sec_mat else kwargs.get("gamma_m0", 1.0)

        # --- Section ---
        self.__Wel_y = sec_mat.Wel_y if sec_mat else kwargs.get("Wel_y", 0.0)
        self.__Wel_z = sec_mat.Wel_z if sec_mat else kwargs.get("Wel_z", 0.0)
        self.__Wpl_y = sec_mat.Wpl_y if sec_mat else kwargs.get("Wpl_y", 0.0)
        self.__Wpl_z = sec_mat.Wpl_z if sec_mat else kwargs.get("Wpl_z", 0.0)

        # --- Exposants d'interaction biaxiale §6.2.9.1(6) — Tableau (n=0) ---
        section_type = (sec_mat.section_type if sec_mat and hasattr(sec_mat, "section_type")
                         else kwargs.get("section_type", None))
        self.__section_type = section_type.upper() if section_type else None
        self.__alpha = kwargs.get("alpha", None)
        self.__beta = kwargs.get("beta", None)

    # ==================================================================
    # Moments résistants élastiques
    # ==================================================================

    @property
    def mel_y_rd(self) -> float:
        """Mel,y,Rd = Wel,y · fy / γM0  [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wel_y * self.__fy / self.__gamma_m0

    def get_mel_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mel,y,Rd."""
        r = self.mel_y_rd
        fv = ""
        if with_values:
            fv = (f"Mel,y,Rd = {self.__Wel_y:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N·mm")
        return FormulaResult(
            name="Mel,y,Rd",
            formula="Mel,y,Rd = Wel,y · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.5 (2)",
        )

    @property
    def mel_z_rd(self) -> float:
        """Mel,z,Rd = Wel,z · fy / γM0  [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wel_z * self.__fy / self.__gamma_m0

    def get_mel_z_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mel,z,Rd."""
        r = self.mel_z_rd
        fv = ""
        if with_values:
            fv = (f"Mel,z,Rd = {self.__Wel_z:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N·mm")
        return FormulaResult(
            name="Mel,z,Rd",
            formula="Mel,z,Rd = Wel,z · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.5 (2)",
        )

    # ==================================================================
    # Moments résistants plastiques
    # ==================================================================

    @property
    def mpl_y_rd(self) -> float:
        """Mpl,y,Rd = Wpl,y · fy / γM0  [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wpl_y * self.__fy / self.__gamma_m0

    def get_mpl_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mpl,y,Rd."""
        r = self.mpl_y_rd
        fv = ""
        if with_values:
            fv = (f"Mpl,y,Rd = {self.__Wpl_y:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N·mm")
        return FormulaResult(
            name="Mpl,y,Rd",
            formula="Mpl,y,Rd = Wpl,y · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.5 (2)",
        )

    @property
    def mpl_z_rd(self) -> float:
        """Mpl,z,Rd = Wpl,z · fy / γM0  [N·mm]."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__Wpl_z * self.__fy / self.__gamma_m0

    def get_mpl_z_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mpl,z,Rd."""
        r = self.mpl_z_rd
        fv = ""
        if with_values:
            fv = (f"Mpl,z,Rd = {self.__Wpl_z:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N·mm")
        return FormulaResult(
            name="Mpl,z,Rd",
            formula="Mpl,z,Rd = Wpl,z · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.5 (2)",
        )

    # ==================================================================
    # Moment résistant de calcul selon la classe
    # ==================================================================

    @property
    def mc_y_rd(self) -> float:
        """Mc,y,Rd selon la classe de section [N·mm]."""
        if self.__section_class <= 2:
            return self.mpl_y_rd
        return self.mel_y_rd

    def get_mc_y_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mc,y,Rd."""
        r = self.mc_y_rd
        if self.__section_class <= 2:
            formula = "Mc,y,Rd = Wpl,y · fy / γM0  (classe 1 ou 2)"
            w = self.__Wpl_y
        else:
            formula = "Mc,y,Rd = Wel,y · fy / γM0  (classe 3)"
            w = self.__Wel_y
        fv = ""
        if with_values:
            fv = (f"Mc,y,Rd = {w:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N·mm  "
                  f"(classe {self.__section_class})")
        return FormulaResult(
            name="Mc,y,Rd",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.5 (2)",
        )

    @property
    def mc_z_rd(self) -> float:
        """Mc,z,Rd selon la classe de section [N·mm]."""
        if self.__section_class <= 2:
            return self.mpl_z_rd
        return self.mel_z_rd

    def get_mc_z_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mc,z,Rd."""
        r = self.mc_z_rd
        if self.__section_class <= 2:
            formula = "Mc,z,Rd = Wpl,z · fy / γM0  (classe 1 ou 2)"
            w = self.__Wpl_z
        else:
            formula = "Mc,z,Rd = Wel,z · fy / γM0  (classe 3)"
            w = self.__Wel_z
        fv = ""
        if with_values:
            fv = (f"Mc,z,Rd = {w:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N·mm  "
                  f"(classe {self.__section_class})")
        return FormulaResult(
            name="Mc,z,Rd",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC3-1-1 — §6.2.5 (2)",
        )

    # ==================================================================
    # Vérifications uniaxiales
    # ==================================================================

    @property
    def verif_my(self) -> float:
        """Taux de travail My,Ed / Mc,y,Rd."""
        if self.mc_y_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.mc_y_rd, 4)

    def get_verif_my(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour My,Ed / Mc,y,Rd ≤ 1.0."""
        r = self.verif_my
        ok = r <= 1.0
        fv = ""
        if with_values:
            status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
            fv = (f"My,Ed / Mc,y,Rd = {self.__my_ed:.2f} / "
                  f"{self.mc_y_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="My,Ed/Mc,y,Rd",
            formula="My,Ed / Mc,y,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.5 (1)",
            is_check=True,
        )

    @property
    def verif_mz(self) -> float:
        """Taux de travail Mz,Ed / Mc,z,Rd."""
        if self.mc_z_rd == 0:
            return float('inf')
        return round(self.__mz_ed / self.mc_z_rd, 4)

    def get_verif_mz(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Mz,Ed / Mc,z,Rd ≤ 1.0."""
        r = self.verif_mz
        ok = r <= 1.0
        fv = ""
        if with_values:
            status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
            fv = (f"Mz,Ed / Mc,z,Rd = {self.__mz_ed:.2f} / "
                  f"{self.mc_z_rd:.2f} = {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="Mz,Ed/Mc,z,Rd",
            formula="Mz,Ed / Mc,z,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.5 (1)",
            is_check=True,
        )

    # ==================================================================
    # Flexion biaxiale — §6.2.9.1 (6), sans effort normal (n = 0)
    # ==================================================================

    @property
    def exponents(self) -> tuple:
        """
        (α, β) — exposants de l'interaction biaxiale, Tableau §6.2.9.1(6).

        Valeurs pour n = N,Ed/Npl,Rd = 0 (pas d'effort normal ici) :
            - I / H              : α = 2, β = 1  (β = max(5n, 1))
            - Tubes circulaires  : α = β = 2
            - Tubes rectangulaires (RHS/SHS) : α = β = 1.66
            - Autres / inconnu   : α = β = 1  (sommation linéaire, conservatif)

        Surchargeable via les kwargs ``alpha`` / ``beta`` du constructeur.
        """
        if self.__alpha is not None and self.__beta is not None:
            return (self.__alpha, self.__beta)
        st = self.__section_type
        if st in ("I", "H"):
            return (2.0, 1.0)
        if st == "CHS":
            return (2.0, 2.0)
        if st in ("RHS", "SHS"):
            return (1.66, 1.66)
        return (1.0, 1.0)

    @property
    def verif_biaxial(self) -> float:
        """
        (My,Ed/Mc,y,Rd)^α + (Mz,Ed/Mc,z,Rd)^β  — doit être ≤ 1.0.
        Ref: EC3-1-1 — §6.2.9.1 (6)
        """
        alpha, beta = self.exponents
        my_ratio = self.__my_ed / self.mc_y_rd if self.mc_y_rd > 0 else 0.0
        mz_ratio = self.__mz_ed / self.mc_z_rd if self.mc_z_rd > 0 else 0.0
        return round(my_ratio ** alpha + mz_ratio ** beta, 4)

    def get_verif_biaxial(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour l'interaction biaxiale ≤ 1.0."""
        r = self.verif_biaxial
        alpha, beta = self.exponents
        ok = r <= 1.0
        fv = ""
        if with_values:
            status = "OK ✓" if ok else "NON VÉRIFIÉ ✗"
            my_ratio = self.__my_ed / self.mc_y_rd if self.mc_y_rd > 0 else 0.0
            mz_ratio = self.__mz_ed / self.mc_z_rd if self.mc_z_rd > 0 else 0.0
            fv = (
                f"({my_ratio:.4f})^{alpha:.2f} + ({mz_ratio:.4f})^{beta:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="Interaction biaxiale",
            formula="(My,Ed/Mc,y,Rd)^α + (Mz,Ed/Mc,z,Rd)^β ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.9.1 (6)",
            is_check=True,
        )

    # ==================================================================
    # Synthèse
    # ==================================================================

    @property
    def is_ok(self) -> bool:
        """True si toutes les vérifications sont satisfaites."""
        checks = []
        if self.__my_ed > 0:
            checks.append(self.verif_my <= 1.0)
        if self.__mz_ed > 0:
            checks.append(self.verif_mz <= 1.0)
        if self.__my_ed > 0 and self.__mz_ed > 0:
            checks.append(self.verif_biaxial <= 1.0)
        return all(checks) if checks else True

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection avec toutes les étapes du calcul."""
        fc = FormulaCollection(
            title="Vérification à la flexion",
            ref="EC3-1-1 — §6.2.5 / §6.2.9",
        )
        fc.add(self.get_mc_y_rd(with_values=with_values))
        fc.add(self.get_mc_z_rd(with_values=with_values))
        if self.__my_ed > 0:
            fc.add(self.get_verif_my(with_values=with_values))
        if self.__mz_ed > 0:
            fc.add(self.get_verif_mz(with_values=with_values))
        if self.__my_ed > 0 and self.__mz_ed > 0:
            fc.add(self.get_verif_biaxial(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (f"Bending(My,Ed={self.__my_ed:.2f}, Mz,Ed={self.__mz_ed:.2f}, "
                f"Mc,y,Rd={self.mc_y_rd:.2f}, Mc,z,Rd={self.mc_z_rd:.2f}, "
                f"ok={self.is_ok})")


# ----------------------------------------------------------------------
# Debug
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # IPE 300, S235
    # Propriétés : Wpl_y=628.4e3 mm³, Wpl_z=125.2e3 mm³
    #              Wel_y=557.1e3 mm³, Wel_z=80.5e3 mm³

    print("=" * 60)
    print("CAS 1 : Flexion uniaxiale My = 80 kN·m")
    print("=" * 60)
    b1 = Bending(
        My_ed=80e6,
        section_class=1,
        fy=235,
        gamma_m0=1.0,
        Wpl_y=628.4e3,
        Wpl_z=125.2e3,
        Wel_y=557.1e3,
        Wel_z=80.5e3,
        section_type="I",
    )
    print(b1)
    print(b1.report(with_values=True))
