#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Charge de neige sur toiture — combinaison s = μ · Ce · Ct · sk (ou sAd).

EN 1991-1-3 §5.2(3)P, éq. (5.1)/(5.2) — même formule reprise par la SIA 261
§5.2.2, éq. (9).

Coefficients d'exposition Ce — Tableau 5.1 EN 1991-1-3, MAIS la France
(NF EN 1991-1-3/NA) et la Suisse (SIA 261) redéfinissent chacune leur propre
table : ne pas réutiliser la table EC "de base" pour ces deux pays.
"""

__all__ = ['RoofSnowLoad', 'CE_TABLE_FR', 'CE_TABLE_CH']

from typing import Optional
from core.formula import FormulaResult, FormulaCollection

# ---------------------------------------------------------------------------
# Ce — Coefficient d'exposition
# ---------------------------------------------------------------------------

#: France — NF EN 1991-1-3/NA, remplace le Tableau 5.1 EC (pas d'option
#: "site balayé" à 0,8 en France : seulement normal / abrité).
CE_TABLE_FR = {
    "normal": 1.0,
    "abrite": 1.25,
}

#: Suisse — SIA 261 §5.2.2 (mêmes 3 options que l'EC "de base", valeurs
#: identiques : 0,8 / 1,0 / 1,2).
CE_TABLE_CH = {
    "expose": 0.8,
    "normal": 1.0,
    "abrite": 1.2,
}


class RoofSnowLoad:
    """
    Combine coefficient de forme, exposition, effet thermique et charge au
    sol pour obtenir la charge de neige de calcul sur toiture s [kN/m²].

    :param mu: Coefficient de forme (μ1 ou μ2, voir ``shape_coefficient``).
    :param sk: Charge caractéristique de neige au sol [kN/m²]
        (voir ``ground_snow_load``). Utiliser ``sk=sAd`` pour le cas
        accidentel (charge exceptionnelle, France uniquement).
    :param Ce: Coefficient d'exposition (Tableau Ce du pays concerné).
    :param Ct: Coefficient thermique (1,0 sauf toiture à forte
        transmittance thermique).
    """

    def __init__(self, mu: float, sk: float, Ce: float = 1.0, Ct: float = 1.0) -> None:
        self.__mu = mu
        self.__sk = sk
        self.__Ce = Ce
        self.__Ct = Ct

    @property
    def mu(self) -> float:
        return self.__mu

    @property
    def sk(self) -> float:
        return self.__sk

    @property
    def Ce(self) -> float:
        return self.__Ce

    @property
    def Ct(self) -> float:
        return self.__Ct

    @property
    def s(self) -> float:
        """s = μ · Ce · Ct · sk [kN/m²]."""
        return round(self.__mu * self.__Ce * self.__Ct * self.__sk, 4)

    def get_s(self, with_values: bool = False) -> FormulaResult:
        r = self.s
        fv = ""
        if with_values:
            fv = (
                f"s = {self.__mu:.4f} × {self.__Ce:.2f} × {self.__Ct:.2f} × "
                f"{self.__sk:.4f} = {r:.4f} kN/m²"
            )
        return FormulaResult(
            name="s",
            formula="s = μ · Ce · Ct · sk",
            formula_values=fv,
            result=r,
            unit="kN/m²",
            ref="EN 1991-1-3 — §5.2(3)P / SIA 261 — §5.2.2",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Charge de neige sur toiture",
            ref="EN 1991-1-3 / SIA 261",
        )
        fc.add(self.get_s(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"RoofSnowLoad(mu={self.__mu:.4f}, sk={self.__sk:.4f}kN/m², "
            f"Ce={self.__Ce}, Ct={self.__Ct}, s={self.s:.4f}kN/m²)"
        )


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    r = RoofSnowLoad(mu=0.8, sk=0.60, Ce=CE_TABLE_FR["normal"], Ct=1.0)
    print(f"{r!r}")
    print(r.report(with_values=True))
