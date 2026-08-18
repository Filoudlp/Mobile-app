#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Éléments comprimés en béton armé — SIA 262:2013, chiffre 4.3.7.

Vérification unitaire indépendante (même principe que
``norme.EC2.elu.compression``).

La SIA 262 traite les effets du second ordre par une approche
d'excentricités cumulées, équivalente dans son principe à la méthode de
la courbure nominale de l'EN 1992-1-1 §5.8.8 — mais avec ses propres
expressions :

    M_d  = N_d · e_d                                          éq. (72)
    e_d  = e_0d + e_1d + e_2d                                 éq. (73)

    e_0d = max( α_i·l/2 ; d/30 )   imperfections               éq. (74)
        α_i = max( 1/200 ; 0,01/√l )   avec l en m             éq. (17)
    e_1d = M_d/N_d                 premier ordre               éq. (75)
    e_2d = χ_d·l²/c                déformation                 éq. (76)
        c = π²                                                 éq. (80)

    χ_d = 2·f_sd / (E_s·(d − d'))  courbure approchée          éq. (77)
        « L'influence du fluage et du retrait est déjà incluse dans
        l'équation (77) » — §4.3.7.8. Il n'y a donc PAS de coefficient
        de fluage séparé à appliquer, contrairement au Kφ de l'EC2.

    Une valeur plus précise de la courbure peut être obtenue par le plan
    de déformation (éq. 78) — hors périmètre de cette version, qui
    retient l'approche approchée du §4.3.7.8.

Module d'élasticité — §4.2.2.4, éq. (33) :
    E_cd = E_cm/γ_cE  avec γ_cE = 1,2 pour les effets du second ordre.

Acier d'armature — Tableau 9 : f_sd = 435 MPa (B500A/B/C), E_s = 205 GPa.

⚠ Écarts notables vs EN 1992-1-1 (à ne pas confondre) :
    - E_s = 205 GPa en SIA contre 200 GPa en EC2.
    - La courbure χ_d de l'éq. (77) intègre déjà fluage et retrait.
    - e_0d combine imperfections ET excentricité minimale en une seule
      expression (max de deux termes), là où l'EC2 sépare ei (§5.2) et
      e0,min = max(h/30 ; 20 mm) (§6.1).
"""

__all__ = ['GAMMA_CE_SIA', 'ES_SIA', 'CompressedElementSIA']

import math
from typing import Optional

from core.formula import FormulaResult, FormulaCollection

#: γcE pour les effets du second ordre — SIA 262 §4.2.2.4.
GAMMA_CE_SIA = 1.2

#: Module d'élasticité de l'acier d'armature — SIA 262 Figure 16.
ES_SIA = 205000.0


class CompressedElementSIA:
    """
    Élément comprimé — SIA 262 §4.3.7.

    :param Nd: Effort normal de calcul [N] (compression, valeur absolue).
    :param Md_1: Moment du premier ordre [N·mm].
    :param l: Longueur de flambage de l'élément [mm].
    :param d: Hauteur utile [mm].
    :param d_prime: Distance du lit comprimé à la fibre comprimée [mm].
    :param fsd: Limite d'écoulement de calcul de l'armature [MPa].
    :param Es: Module d'élasticité de l'acier [MPa] (205 000 par défaut).
    :param c: Constante d'intégration (π² par défaut — éq. 80).
    """

    def __init__(
        self,
        Nd: float = 0.0,
        Md_1: float = 0.0,
        l: float = 0.0,
        d: float = 0.0,
        d_prime: float = 0.0,
        fsd: float = 435.0,
        Es: float = ES_SIA,
        c: Optional[float] = None,
    ) -> None:
        self.__nd = abs(Nd)
        self.__md1 = abs(Md_1)
        self.__l = l
        self.__d = d
        self.__d_prime = d_prime
        self.__fsd = fsd
        self.__Es = Es
        self.__c = c if c is not None else math.pi ** 2

    # ------------------------------------------------------------------
    #  Imperfections — éq. (17) et (74)
    # ------------------------------------------------------------------
    @property
    def alpha_i(self) -> float:
        """α_i = max(1/200 ; 0,01/√l)  avec l en m — éq. (17)."""
        l_m = self.__l / 1000.0
        if l_m <= 0:
            return 1.0 / 200.0
        return max(1.0 / 200.0, 0.01 / math.sqrt(l_m))

    @property
    def e_0d(self) -> float:
        """e_0d = max(α_i·l/2 ; d/30) [mm] — éq. (74)."""
        return max(self.alpha_i * self.__l / 2.0, self.__d / 30.0)

    # ------------------------------------------------------------------
    #  Premier ordre — éq. (75)
    # ------------------------------------------------------------------
    @property
    def e_1d(self) -> float:
        """e_1d = M_d/N_d [mm] — éq. (75)."""
        return self.__md1 / self.__nd if self.__nd else 0.0

    # ------------------------------------------------------------------
    #  Déformation — éq. (76) et (77)
    # ------------------------------------------------------------------
    @property
    def chi_d(self) -> float:
        """χ_d = 2·f_sd/(E_s·(d − d')) [1/mm] — éq. (77).
        Fluage et retrait déjà inclus (§4.3.7.8)."""
        denom = self.__Es * (self.__d - self.__d_prime)
        return 2.0 * self.__fsd / denom if denom > 0 else 0.0

    @property
    def e_2d(self) -> float:
        """e_2d = χ_d·l²/c [mm] — éq. (76)."""
        if self.__c == 0:
            return 0.0
        return self.chi_d * self.__l ** 2 / self.__c

    # ------------------------------------------------------------------
    #  Résultante — éq. (72) et (73)
    # ------------------------------------------------------------------
    @property
    def e_d(self) -> float:
        """e_d = e_0d + e_1d + e_2d [mm] — éq. (73)."""
        return self.e_0d + self.e_1d + self.e_2d

    @property
    def Md(self) -> float:
        """M_d = N_d·e_d [N·mm] — éq. (72)."""
        return self.__nd * self.e_d

    # ------------------------------------------------------------------
    #  FormulaResult
    # ------------------------------------------------------------------
    def get_e_0d(self, with_values: bool = False) -> FormulaResult:
        r = self.e_0d
        fv = ""
        if with_values:
            t1 = self.alpha_i * self.__l / 2.0
            t2 = self.__d / 30.0
            fv = (
                f"e_0d = max(α_i·l/2 ; d/30) = max({self.alpha_i:.5f} × "
                f"{self.__l:.0f}/2 ; {self.__d:.0f}/30) = "
                f"max({t1:.2f} ; {t2:.2f}) = {r:.2f} mm"
            )
        return FormulaResult(
            name="e_0d", formula="e_0d = max(α_i·l/2 ; d/30)",
            formula_values=fv, result=r, unit="mm",
            ref="SIA 262 — §4.3.7.5, éq. (74)",
        )

    def get_e_1d(self, with_values: bool = False) -> FormulaResult:
        r = self.e_1d
        fv = (
            f"e_1d = {self.__md1:.0f}/{self.__nd:.0f} = {r:.2f} mm"
        ) if with_values else ""
        return FormulaResult(
            name="e_1d", formula="e_1d = M_d / N_d",
            formula_values=fv, result=r, unit="mm",
            ref="SIA 262 — §4.3.7.6, éq. (75)",
        )

    def get_e_2d(self, with_values: bool = False) -> FormulaResult:
        r = self.e_2d
        fv = ""
        if with_values:
            fv = (
                f"χ_d = 2 × {self.__fsd:.0f}/({self.__Es:.0f} × "
                f"({self.__d:.0f} − {self.__d_prime:.0f})) = {self.chi_d:.3e} 1/mm "
                f"→ e_2d = {self.chi_d:.3e} × {self.__l:.0f}²/{self.__c:.4f} "
                f"= {r:.2f} mm"
            )
        return FormulaResult(
            name="e_2d", formula="e_2d = χ_d·l²/c ,  χ_d = 2·f_sd/(E_s·(d−d'))",
            formula_values=fv, result=r, unit="mm",
            ref="SIA 262 — §4.3.7.7/§4.3.7.8, éq. (76)/(77)",
        )

    def get_Md(self, with_values: bool = False) -> FormulaResult:
        r = self.Md
        fv = ""
        if with_values:
            fv = (
                f"e_d = {self.e_0d:.2f} + {self.e_1d:.2f} + {self.e_2d:.2f} "
                f"= {self.e_d:.2f} mm  →  M_d = {self.__nd:.0f} × "
                f"{self.e_d:.2f} = {r:.0f} N·mm"
            )
        return FormulaResult(
            name="M_d", formula="M_d = N_d·e_d ,  e_d = e_0d + e_1d + e_2d",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 262 — §4.3.7.3/§4.3.7.4, éq. (72)/(73)",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Élément comprimé — excentricités du second ordre",
            ref="SIA 262 — §4.3.7",
        )
        fc.add(self.get_e_0d(with_values=with_values))
        fc.add(self.get_e_1d(with_values=with_values))
        fc.add(self.get_e_2d(with_values=with_values))
        fc.add(self.get_Md(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"CompressedElementSIA(e_0d={self.e_0d:.2f}, e_1d={self.e_1d:.2f}, "
            f"e_2d={self.e_2d:.2f}, e_d={self.e_d:.2f}mm, "
            f"M_d={self.Md / 1e6:.2f}kN·m)"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 66
    print(f"\n{sep}\n  Poteau 300×400, l = 3,5 m, N_d = 900 kN, M_d1 = 20 kN·m\n{sep}")
    el = CompressedElementSIA(
        Nd=900e3, Md_1=20e6, l=3500.0, d=350.0, d_prime=50.0, fsd=435.0,
    )
    print(f"  {el!r}")
    print(el.report(with_values=True))
    print(f"\n{'=' * 66}\n  FIN DES TESTS\n{'=' * 66}")
