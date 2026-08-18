#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define concrete material properties according to EC2.

    References:
        - EN 1992-1-1 (Eurocode 2) — Table 3.1

    Supported National Annexes:
        - FR : France (default)
        - BE : Belgique
        - UK : Royaume-Uni
"""

__all__ = ['MatConcrete']

import math
from dataclasses import dataclass
from typing import Optional

from core.mat.materials import Material
from core.formula import FormulaResult
from core.coefficient import NationalAnnex, Country


# =============================================================================
# MatConcrete
# =============================================================================

class MatConcrete(Material):
    """
    Béton selon EC2 — EN 1992-1-1, Table 3.1.

    :param fck: Résistance caractéristique sur cylindre à 28j [MPa]
    :param country: Code pays de l'Annexe Nationale ("FR", "BE", "UK")
    :param coefficients: Coefficients personnalisés (prioritaire sur country)
    """
    _BA_TYPE = {8: "C8/10", 12: "C12/15", 16: "C16/20",
               20: "C20/25", 25: "C25/30",
               30: "C30/37", 35: "C35/45",
               40: "C40/50", 45: "C45/55",
               50: "C50/60", 55: "C55/67",
               60: "C60/75", 70: "C70/85",
               80: "C80/95", 90: "C90/105",
               100: "C100/115"}
    
    _DEFAULT_NU = 0.2
    _DEFAULT_ALPHA = 12e-6      # K⁻¹
    _DEFAULT_RHO = 2500.0       # kg/m³

    def __init__(self, fck: float, country: str = "FR",
                 coefficients: Optional[ConcreteCoefficients] = None) -> None:

        self._fck = fck
        self._country = country.upper()

        if coefficients is not None:
            self._coefficients = coefficients
        else:
            self._coefficients = self._get_coefficients(self._country)

        # Calcul des propriétés intrinsèques (indépendantes de l'AN)
        self._internal_propserty(fck)

        super().__init__(
            name= self._BA_TYPE[self._fck] if self._fck in self._BA_TYPE else f"C{self._fck:.0f}",
            E=self._ecm,
            nu=self._DEFAULT_NU,
            rho=self._DEFAULT_RHO,
        )
    
    def _internal_propserty(self, fck : float) -> None:
        """Met à jour les propriétés intrinsèques du béton en fonction de fck."""
        self._fcm = fck + 8
        self._fctm = self._calc_fctm()
        self._fctk_005 = 0.7 * self._fctm
        self._fctk_095 = 1.3 * self._fctm
        self._ecm = 22000 * (self._fcm / 10) ** 0.3
        self._epsilon_c1 = min(0.7 * self._fcm ** 0.31, 2.8) / 1000
        self._epsilon_cu1 = min(3.5, 2.8 + 27 * ((98 - self._fcm) / 100) ** 4) / 1000
        self._epsilon_c2 = (2.0 if self.fck <= 50 else max(2.0, 2.0 + 0.085 * (self._fck - 50) ** 0.53)) / 1000
        self._epsilon_cu2 = min(3.5, 2.6 + 35 * ((90 - self._fck) / 100) ** 4) / 1000
        self._n_parabole = max(2.0, 1.4 + 23.4 * ((90 - self._fck) / 100) ** 4)
        self._epsilon_c3 = max(1.75, 1.75 + 0.55 * (self._fck - 50) / 40) / 1000
        self._epsilon_cu3 = min(3.5, 2.6 + 35 * ((90 - self._fck) / 100) ** 4) / 1000

    # ---- helpers internes ----

    @staticmethod
    def _get_coefficients(country: str) -> ConcreteCoefficients:
        country = country.upper()
        if country not in Country.__members__.keys():
            raise ValueError(
                f"Annexe Nationale '{country}' non supportée. "
                f"Choix possibles : {list(Country.__members__.keys())}"
            )
        return NationalAnnex.from_country(Country[country])

    def _calc_fctm(self) -> float:
        if self._fck <= 50:
            return 0.30 * self._fck ** (2 / 3)
        return 2.12 * math.log(1 + self._fcm / 10)

    # ---- country (dynamique) ----

    @property
    def country(self) -> str:
        return self._country

    @country.setter
    def country(self, value: str) -> None:
        self._country = value.upper()
        self._coefficients = self._get_coefficients(self._country)

    @property
    def coefficients(self) -> ConcreteCoefficients:
        return self._coefficients

    # =================================================================
    # Propriétés intrinsèques (indépendantes de l'AN)
    # =================================================================

    @property
    def fck(self) -> float:
        return self._fck

    @fck.setter
    def fck(self, value: float) -> None:
        self._fck = value
        # Recalcul des propriétés intrinsèques
        self._internal_propserty(value)

    @property
    def fcm(self) -> float:
        return self._fcm

    @property
    def fcm_report(self) -> FormulaResult:
        return FormulaResult(
            name="fcm",
            formula="fcm = fck + 8",
            formula_values=f"fcm = {self._fck:.2f} + 8 = {self._fcm:.2f}",
            result=self._fcm,
            unit="MPa",
            ref="EC2 — Table 3.1",
        )

    # ---- fctm ----

    @property
    def fctm(self) -> float:
        return self._fctm

    @property
    def fctm_report(self) -> FormulaResult:
        if self._fck <= 50:
            formula = "fctm = 0.30 × fck^(2/3)"
            formula_values = f"fctm = 0.30 × {self._fck:.2f}^(2/3) = {self._fctm:.2f}"
        else:
            formula = "fctm = 2.12 × ln(1 + fcm/10)"
            formula_values = f"fctm = 2.12 × ln(1 + {self._fcm:.2f}/10) = {self._fctm:.2f}"
        return FormulaResult(
            name="fctm",
            formula=formula,
            formula_values=formula_values,
            result=self._fctm,
            unit="MPa",
            ref="EC2 — Table 3.1",
        )

    # ---- fctk_005 ----

    @property
    def fctk_005(self) -> float:
        return self._fctk_005

    @property
    def fctk_005_report(self) -> FormulaResult:
        return FormulaResult(
            name="fctk_005",
            formula="fctk,0.05 = 0.7 × fctm",
            formula_values=f"fctk,0.05 = 0.7 × {self._fctm:.2f} = {self._fctk_005:.2f}",
            result=self._fctk_005,
            unit="MPa",
            ref="EC2 — Table 3.1",
        )

    # ---- fctk_095 ----

    @property
    def fctk_095(self) -> float:
        return self._fctk_095

    @property
    def fctk_095_report(self) -> FormulaResult:
        return FormulaResult(
            name="fctk_095",
            formula="fctk,0.95 = 1.3 × fctm",
            formula_values=f"fctk,0.95 = 1.3 × {self._fctm:.2f} = {self._fctk_095:.2f}",
            result=self._fctk_095,
            unit="MPa",
            ref="EC2 — Table 3.1",
        )

    # ---- Ecm ----

    @property
    def ecm(self) -> float:
        return self._ecm

    @property
    def ecm_report(self) -> FormulaResult:
        return FormulaResult(
            name="Ecm",
            formula="Ecm = 22000 × (fcm/10)^0.3",
            formula_values=f"Ecm = 22000 × ({self._fcm:.2f}/10)^0.3 = {self._ecm:.2f}",
            result=self._ecm,
            unit="MPa",
            ref="EC2 — Table 3.1",
        )

    # ---- epsilon_c1 ----

    @property
    def epsilon_c1(self) -> float:
        return self._epsilon_c1

    @property
    def epsilon_c1_report(self) -> FormulaResult:
        raw = min(0.7 * self._fcm ** 0.31, 2.8)
        return FormulaResult(
            name="εc1",
            formula="εc1 = min(0.7 × fcm^0.31 ; 2.8) ‰",
            formula_values=f"εc1 = min(0.7 × {self._fcm:.2f}^0.31 ; 2.8) = {raw:.2f} ‰",
            result=self._epsilon_c1,
            unit="‰",
            ref="EC2 — Table 3.1",
        )

    # ---- epsilon_cu1 ----

    @property
    def epsilon_cu1(self) -> float:
        return self._epsilon_cu1

    @property
    def epsilon_cu1_report(self) -> FormulaResult:
        return FormulaResult(
            name="εcu1",
            formula="εcu1 = min(3.5 ; 2.8 + 27 × ((98 - fcm)/100)^4) ‰",
            formula_values=f"εcu1 = min(3.5 ; 2.8 + 27 × ((98 - {self._fcm:.2f})/100)^4) = {self._epsilon_cu1 * 1000:.2f} ‰",
            result=self._epsilon_cu1,
            unit="‰",
            ref="EC2 — Table 3.1",
        )

    # ---- epsilon_c2 ----

    @property
    def epsilon_c2(self) -> float:
        return self._epsilon_c2

    @property
    def epsilon_c2_report(self) -> FormulaResult:
        return FormulaResult(
            name="εc2",
            formula="εc2 = max(2.0 ; 2.0 + 0.085 × (fck - 50)^0.53) ‰",
            formula_values=f"εc2 = max(2.0 ; 2.0 + 0.085 × ({self._fck:.2f} - 50)^0.53) = {self._epsilon_c2 * 1000:.2f} ‰",
            result=self._epsilon_c2,
            unit="‰",
            ref="EC2 — Table 3.1",
        )

    # ---- epsilon_cu2 ----

    @property
    def epsilon_cu2(self) -> float:
        return self._epsilon_cu2

    @property
    def epsilon_cu2_report(self) -> FormulaResult:
        return FormulaResult(
            name="εcu2",
            formula="εcu2 = min(3.5 ; 2.6 + 35 × ((90 - fck)/100)^4) ‰",
            formula_values=f"εcu2 = min(3.5 ; 2.6 + 35 × ((90 - {self._fck:.2f})/100)^4) = {self._epsilon_cu2 * 1000:.2f} ‰",
            result=self._epsilon_cu2,
            unit="‰",
            ref="EC2 — Table 3.1",
        )

    # ---- epsilon_c3 ----

    @property
    def epsilon_c3(self) -> float:
        return self._epsilon_c3

    @property
    def epsilon_c3_report(self) -> FormulaResult:
        return FormulaResult(
            name="εc3",
            formula="εc3 = max(1.75 ; 1.75 + 0.55 × (fck - 50)/40) ‰",
            formula_values=f"εc3 = max(1.75 ; 1.75 + 0.55 × ({self._fck:.2f} - 50)/40) = {self._epsilon_c3 * 1000:.2f} ‰",
            result=self._epsilon_c3,
            unit="‰",
            ref="EC2 — Table 3.1",
        )

    # ---- epsilon_cu3 ----

    @property
    def epsilon_cu3(self) -> float:
        return self._epsilon_cu3

    @property
    def epsilon_cu3_report(self) -> FormulaResult:
        return FormulaResult(
            name="εcu3",
            formula="εcu3 = min(3.5 ; 2.6 + 35 × ((90 - fck)/100)^4) ‰",
            formula_values=f"εcu3 = min(3.5 ; 2.6 + 35 × ((90 - {self._fck:.2f})/100)^4) = {self._epsilon_cu3 * 1000:.2f} ‰",
            result=self._epsilon_cu3,
            unit="‰",
            ref="EC2 — Table 3.1",
        )

    # ---- n (exposant parabole) ----

    @property
    def n_parabole(self) -> float:
        return self._n_parabole

    @property
    def n_parabole_report(self) -> FormulaResult:
        if self._fck <= 50:
            formula = "n = 2.0"
            formula_values = f"n = 2.0"
        else:
            formula = "n = max(2.0 ; 1.4 + 23.4 × ((90 - fck)/100)^4)"
            formula_values = f"n = max(2.0 ; 1.4 + 23.4 × ((90 - {self._fck:.2f})/100)^4) = {self._n_parabole:.2f}" 

        return FormulaResult(
            name="n",
            formula=formula,
            formula_values=formula_values,
            result=self._n_parabole,
            unit="-",
            ref="EC2 — Table 3.1",
        )

    # =================================================================
    # Propriétés dépendantes de l'AN
    # =================================================================

    # ---- fcd ----

    @property
    def fcd(self) -> float:
        return self._coefficients.ec2.alpha_cc * self._fck / self._coefficients.ec2.gamma_c

    @property
    def fcd_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="fcd",
            formula="fcd = αcc × fck / γc",
            formula_values=(
                f"fcd = {c.ec2.alpha_cc} × {self._fck:.2f} / {c.ec2.gamma_c} "
                f"= {self.fcd:.2f}"
            ),
            result=self.fcd,
            unit="MPa",
            ref=f"EC2 — 3.1.6(1) — AN {c.country}",
        )

    # ---- fctd ----

    @property
    def fctd(self) -> float:
        return self._coefficients.ec2.alpha_ct * self._fctk_005 / self._coefficients.ec2.gamma_c

    @property
    def fctd_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="fctd",
            formula="fctd = αct × fctk,0.05 / γc",
            formula_values=(
                f"fctd = {c.ec2.alpha_ct} × {self._fctk_005:.2f} / {c.ec2   .gamma_c} "
                f"= {self.fctd:.2f}"
            ),
            result=self.fctd,
            unit="MPa",
            ref=f"EC2 — 3.1.6(2)P — AN {c.country}",
        )

    # =================================================================
    # Méthode utilitaire : toutes les formules d'un coup
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        """Renvoie la liste de tous les FormulaResult pour un rapport complet."""
        return [
            self.fcm_report,
            self.fctm_report,
            self.fctk_005_report,
            self.fctk_095_report,
            self.ecm_report,
            self.epsilon_c1_report,
            self.epsilon_cu1_report,
            self.epsilon_c2_report,
            self.epsilon_cu2_report,
            self.epsilon_c3_report,
            self.epsilon_cu3_report,
            self.n_parabole_report,
            self.fcd_report,
            self.fctd_report,
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"MatConcrete(fck={self._fck}, country='{self._country}', "
            f"fcd={self.fcd:.2f}, fctd={self.fctd:.2f})"
        )

    def __str__(self) -> str:
        lines = [
            f"{'=' * 60}",
            f"  Béton {self.name} — AN {self._country}",
            f"{'=' * 60}",
        ]
        for r in self.all_reports():
            lines.append(f"  {r.formula_values:50s} [{r.unit}]  ({r.ref})")
        lines.append(f"{'=' * 60}")
        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    c30 = MatConcrete(fck=30, country="FR")
    print(c30)

    # Accès individuel
    print("\n--- Accès individuel ---")
    print(f"fcd = {c30.fcd:.2f} MPa")
    f = c30.fcd_report
    print(f"  Formule    : {f.formula}")
    print(f"  Valeurs    : {f.formula_values}")
    print(f"  Résultat   : {f.result:.2f} {f.unit}")
    print(f"  Référence  : {f.ref}")

    # Changement AN
    print("\n--- Passage en BE ---")
    c30.country = "BE"
    print(c30.fcd_report)

    # Itération pour rapport
    print("\n--- Rapport complet ---")
    for r in c30.all_reports():
        print(f"  {r.name:12s} = {r.result:10.4f} {r.unit:5s}  |  {r.ref}")
