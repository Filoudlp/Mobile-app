#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification à la compression selon EC3-1-1 §6.2.4

Résistance plastique en compression uniquement.
Le flambement est traité séparément dans buckling.py.
"""
__all__ = ['Compression']

from typing import TypeVar, Optional
from core.formula import FormulaResult, FormulaCollection

SecMatSteel = TypeVar('SecMatSteel')

# TODO — Implémentation future :
# - Sections de classe 4 : Nc,Rd = Aeff · fy / γM0
# - Compression + flambement → voir buckling.py


class Compression:
    """
    Vérification à la compression — EC3-1-1 §6.2.4

    Calcule la résistance plastique en compression Nc,Rd et vérifie
    que l'effort de compression de calcul Ned ne la dépasse pas.

    :param Ned:      Effort normal de traction de calcul [N]
    :param sec_mat:  Objet section_material (fy, fu, gamma_m0, gamma_m, A, Anet)
    :param kwargs:   Surcharge manuelle des paramètres
    """

    def __init__(self, Ned: float,
                 sec_mat: Optional[SecMatSteel] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        Ned : float
            Effort de compression de calcul [N] (stocké en valeur absolue).
        :param sec_mat:  Objet section_material (fy, fu, gamma_m0, gamma_m, A, Anet)
        **kwargs
            Valeurs alternatives : fy, gamma_m0, A.
        """
        self.__ned = abs(Ned)

        # --- Matériau ---
        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__gamma_m0 = sec_mat.gamma_m0 if sec_mat else kwargs.get("gamma_m0", 1.0)

        # --- Section ---
        self.__A = sec_mat.A if sec_mat else kwargs.get("A", 0.0)

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def ned(self) -> float:
        """Effort de compression de calcul [N]."""
        return self.__ned

    @property
    def nc_rd(self) -> float:
        """Nc,Rd = A · fy / γM0  [N] — §6.2.4 (2)."""
        if self.__gamma_m0 == 0:
            return 0.0
        return self.__A * self.__fy / self.__gamma_m0

    def get_nc_rd(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour Nc,Rd — §6.2.4 (2)."""
        r = self.nc_rd
        fv = ""
        if with_values:
            fv = (f"Nc,Rd = {self.__A:.2f} × {self.__fy:.2f} / "
                  f"{self.__gamma_m0} = {r:.2f} N")
        return FormulaResult(
            name="Nc,Rd",
            formula="Nc,Rd = A · fy / γM0",
            formula_values=fv,
            result=r,
            unit="N",
            ref="EC3-1-1 — §6.2.4 (2)",
        )

    # ------------------------------------------------------------------
    # Vérification
    # ------------------------------------------------------------------

    @property
    def verif(self) -> float:
        """Taux de travail Ned / Nc,Rd."""
        if self.nc_rd == 0:
            return float('inf')
        return round(self.__ned / self.nc_rd, 4)

    @property
    def is_ok(self) -> bool:
        """True si Ned / Nc,Rd ≤ 1.0."""
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification Ned / Nc,Rd ≤ 1.0."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (f"Ned / Nc,Rd = {self.__ned:.2f} / {self.nc_rd:.2f} "
                  f"= {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="Ned/Nc,Rd",
            formula="Ned / Nc,Rd ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §6.2.4 (1)",
            is_check=True,
        )

    # ------------------------------------------------------------------
    # Rapport
    # ------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection regroupant toutes les étapes."""
        fc = FormulaCollection(
            title="Vérification à la compression",
            ref="EC3-1-1 — §6.2.4",
        )
        fc.add(self.get_nc_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (f"Compression(Ned={self.__ned:.2f}, Nc,Rd={self.nc_rd:.2f}, "
                f"taux={self.verif:.4f}, ok={self.is_ok})")


# ----------------------------------------------------------------------
# Debug
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # IPE 300, S235, Ned = 500 kN
    c = Compression(
        Ned=500e3,
        A=5381,       # mm²  (IPE 300)
        fy=235,       # MPa  (S235)
        gamma_m0=1.0,
    )
    print(c)
    print(c.report(with_values=True))
