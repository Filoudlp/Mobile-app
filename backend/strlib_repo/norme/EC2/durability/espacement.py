#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification de l'espacement minimal entre armatures selon EC2-1-1 §8.2

Détermine la distance libre minimale entre barres parallèles afin
d'assurer un bétonnage et une adhérence corrects.
"""
__all__ = ['Spacing']

from typing import TypeVar, Optional
from core.formula import FormulaResult, FormulaCollection

SecMatConcrete = TypeVar('SecMatConcrete')

# TODO — Implémentation future :
# - Espacement pour barres en paquets §8.9.1
# - Espacement maximal des armatures de peau §7.3.3


class Spacing:
    """
    Vérification de l'espacement minimal entre armatures — EC2-1-1 §8.2

    Calcule la distance libre minimale entre barres parallèles :
        a_min = max(k1 · φ ; dg + k2 ; 20 mm)

    où :
        - φ      : diamètre de la barre [mm]
        - dg     : diamètre maximal du granulat [mm]
        - k1, k2 : coefficients de l'Annexe Nationale (recommandés : k1=1, k2=5 mm)

    :param a:        Distance libre réelle entre barres [mm]
    :param phi:      Diamètre de la barre [mm]
    :param sec_mat:  Objet section_material (dg, k1, k2)
    :param kwargs:   Surcharge manuelle des paramètres
    """

    def __init__(self, a: float, phi: float,
                 sec_mat: Optional[SecMatConcrete] = None,
                 **kwargs) -> None:
        """
        Paramètres
        ----------
        a : float
            Distance libre réelle entre barres parallèles [mm].
        phi : float
            Diamètre de la barre considérée [mm].
        sec_mat : SecMatConcrete, optional
            Objet section_material béton (dg, k1, k2).
        **kwargs
            Valeurs alternatives : dg, k1, k2.
        """
        self.__a = abs(a)
        self.__phi = abs(phi)

        # --- Matériau / granulat ---
        self.__dg = sec_mat.dg if sec_mat else kwargs.get("dg", 16.0)

        # --- Coefficients Annexe Nationale (recommandés) ---
        self.__k1 = sec_mat.k1 if sec_mat else kwargs.get("k1", 1.0)
        self.__k2 = sec_mat.k2 if sec_mat else kwargs.get("k2", 5.0)

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def a(self) -> float:
        """Distance libre réelle entre barres [mm]."""
        return self.__a

    @property
    def phi(self) -> float:
        """Diamètre de la barre [mm]."""
        return self.__phi

    @property
    def a_min(self) -> float:
        """a_min = max(k1·φ ; dg + k2 ; 20 mm)  [mm] — §8.2 (2)."""
        return max(self.__k1 * self.__phi,
                   self.__dg + self.__k2,
                   20.0)

    def get_a_min(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour a_min — §8.2 (2)."""
        r = self.a_min
        fv = ""
        if with_values:
            fv = (f"a_min = max({self.__k1} × {self.__phi:.2f} ; "
                  f"{self.__dg:.2f} + {self.__k2:.2f} ; 20) "
                  f"= max({self.__k1 * self.__phi:.2f} ; "
                  f"{self.__dg + self.__k2:.2f} ; 20) "
                  f"= {r:.2f} mm")
        return FormulaResult(
            name="a_min",
            formula="a_min = max(k1·φ ; dg + k2 ; 20 mm)",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2-1-1 — §8.2 (2)",
        )

    # ------------------------------------------------------------------
    # Vérification
    # ------------------------------------------------------------------

    @property
    def verif(self) -> float:
        """Taux de travail a_min / a."""
        if self.__a == 0:
            return float('inf')
        return round(self.a_min / self.__a, 4)

    @property
    def is_ok(self) -> bool:
        """True si a ≥ a_min."""
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification a ≥ a_min."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (f"a_min / a = {self.a_min:.2f} / {self.__a:.2f} "
                  f"= {r:.4f} ≤ 1.0 → {status}")
        return FormulaResult(
            name="a_min/a",
            formula="a_min / a ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2-1-1 — §8.2 (1)",
            is_check=True,
        )

    # ------------------------------------------------------------------
    # Rapport
    # ------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection regroupant toutes les étapes."""
        fc = FormulaCollection(
            title="Vérification de l'espacement minimal entre armatures",
            ref="EC2-1-1 — §8.2",
        )
        fc.add(self.get_a_min(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (f"Spacing(a={self.__a:.2f}, phi={self.__phi:.2f}, "
                f"a_min={self.a_min:.2f}, taux={self.verif:.4f}, "
                f"ok={self.is_ok})")


if __name__ == "__main__":
    # Debug zone
    s = Spacing(a=30, phi=20, dg=16, k1=1.0, k2=5.0)
    print(s)
    print(s.report(with_values=True))
