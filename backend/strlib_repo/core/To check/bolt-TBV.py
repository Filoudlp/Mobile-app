#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define bolt material properties according to EC3-1-8.

    References:
        - EN 1993-1-8 — Table 3.1

    Supported National Annexes:
        - FR (default), BE, UK
"""

__all__ = ['MatBolt', 'BoltCoefficients']

from dataclasses import dataclass
from typing import Optional

from mat.materials import Material
from formula import FormulaResult


# =============================================================================
# Coefficients nationaux — EC3-1-8 §2.2
# =============================================================================

@dataclass
class BoltCoefficients:
    """
    Coefficients partiels pour les assemblages boulonnés.

    :param gamma_m2: Coefficient partiel résistance des boulons [-]
    :param country: Code pays
    """
    gamma_m2: float = 1.25
    country: str = "FR"


_NATIONAL_ANNEX_REGISTRY: dict[str, BoltCoefficients] = {
    "FR": BoltCoefficients(gamma_m2=1.25, country="FR"),
    "BE": BoltCoefficients(gamma_m2=1.25, country="BE"),
    "UK": BoltCoefficients(gamma_m2=1.25, country="UK"),
}


# =============================================================================
# Registre des classes de boulons — EC3-1-8 Table 3.1
# =============================================================================

@dataclass
class _BoltGradeData:
    """
    Propriétés mécaniques d'une classe de boulon.

    :param fyb: Limite d'élasticité nominale [MPa]
    :param fub: Résistance ultime nominale [MPa]
    """
    fyb: float
    fub: float


_BOLT_GRADES: dict[str, _BoltGradeData] = {
    "4.6":  _BoltGradeData(fyb=240,  fub=400),
    "4.8":  _BoltGradeData(fyb=320,  fub=400),
    "5.6":  _BoltGradeData(fyb=300,  fub=500),
    "5.8":  _BoltGradeData(fyb=400,  fub=500),
    "6.8":  _BoltGradeData(fyb=480,  fub=600),
    "8.8":  _BoltGradeData(fyb=640,  fub=800),
    "10.9": _BoltGradeData(fyb=900,  fub=1000),
}


# =============================================================================
# Classe principale
# =============================================================================

class MatBolt(Material):
    """
    Matériau boulon selon EC3-1-8 Table 3.1.

    Deux modes d'instanciation :
        - Par classe :  MatBolt(grade="8.8")
        - Par valeurs :  MatBolt(fyb=640, fub=800)

    :param grade: Classe du boulon ("4.6", "8.8", "10.9", etc.)
    :param fyb: Limite d'élasticité nominale [MPa]
    :param fub: Résistance ultime nominale [MPa]
    :param country: Code pays pour l'Annexe Nationale
    :param name: Nom libre
    """
    _DEFAULT_E = 210000.0       # MPa
    _DEFAULT_NU = 0.3
    _DEFAULT_ALPHA = 12e-6      # K⁻¹
    _DEFAULT_RHO = 7850.0       # kg/m³

    def __init__(
        self,
        grade: Optional[str] = None,
        fyb: Optional[float] = None,
        fub: Optional[float] = None,
        country: str = "FR",
        name: Optional[str] = None,
    ) -> None:

        # --- Résolution grade / valeurs manuelles ---
        if fyb is not None and fub is not None:
            self._fyb = fyb
            self._fub = fub
            self._grade = grade or "Custom"
        elif grade is not None:
            grade_upper = grade.upper().replace(",", ".")
            if grade_upper not in _BOLT_GRADES:
                raise ValueError(
                    f"Classe '{grade}' inconnue. "
                    f"Classes disponibles : {list(_BOLT_GRADES.keys())}"
                )
            data = _BOLT_GRADES[grade_upper]
            self._fyb = data.fyb
            self._fub = data.fub
            self._grade = grade_upper
        else:
            raise ValueError(
                "Fournir soit grade ('8.8'), soit (fyb + fub)."
            )

        # --- Nom ---
        self._name = name or f"Boulon {self._grade}"

        # --- AN ---
        self._country = country.upper()
        self._coefficients = self._get_coefficients(self._country)

        # --- Init parent ---
        super().__init__(name=self._name, E=_DEFAULT_E, nu=_DEFAULT_NU, alpha=_DEFAULT_ALPHA, rho=_DEFAULT_RHO)

    # =================================================================
    # Gestion Annexe Nationale
    # =================================================================

    @staticmethod
    def _get_coefficients(country: str) -> BoltCoefficients:
        if country not in _NATIONAL_ANNEX_REGISTRY:
            raise ValueError(
                f"AN '{country}' non supporté. "
                f"Disponibles : {list(_NATIONAL_ANNEX_REGISTRY.keys())}"
            )
        return _NATIONAL_ANNEX_REGISTRY[country]

    @property
    def country(self) -> str:
        return self._country

    @country.setter
    def country(self, value: str) -> None:
        self._country = value.upper()
        self._coefficients = self._get_coefficients(self._country)

    # =================================================================
    # Propriétés caractéristiques
    # =================================================================

    @property
    def grade(self) -> str:
        return self._grade

    @grade.setter
    def grade(self, value: str) -> None:
        """Redéfinir les propriétés mécaniques si on change de classe."""
        value_upper = value.upper().replace(",", ".")
        if value_upper not in _BOLT_GRADES:
            raise ValueError(
                f"Classe '{value}' inconnue. "
                f"Classes disponibles : {list(_BOLT_GRADES.keys())}"
            )
        data = _BOLT_GRADES[value_upper]
        self._fyb = data.fyb
        self._fub = data.fub
        self._grade = value_upper
        self._name = f"Boulon {self._grade}"

    # ---- fyb ----

    @property
    def fyb(self) -> float:
        """Limite d'élasticité nominale [MPa] — EC3-1-8 Table 3.1"""
        return self._fyb

    @property
    def fyb_report(self) -> FormulaResult:
        return FormulaResult(
            name="fyb",
            formula="fyb — EC3-1-8 Table 3.1",
            formula_values=f"fyb(classe {self._grade}) = {self._fyb:.2f}",
            result=self._fyb,
            unit="MPa",
            ref="EC3-1-8 — Table 3.1",
        )

    # ---- fub ----

    @property
    def fub(self) -> float:
        """Résistance ultime nominale [MPa] — EC3-1-8 Table 3.1"""
        return self._fub

    @property
    def fub_report(self) -> FormulaResult:
        return FormulaResult(
            name="fub",
            formula="fub — EC3-1-8 Table 3.1",
            formula_values=f"fub(classe {self._grade}) = {self._fub:.2f}",
            result=self._fub,
            unit="MPa",
            ref="EC3-1-8 — Table 3.1",
        )

    # =================================================================
    # Propriétés de calcul
    # =================================================================

    # ---- gamma_m2 ----

    @property
    def gamma_m2(self) -> float:
        return self._coefficients.gamma_m2

    @property
    def gamma_m2_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="γM2",
            formula="γM2 = coefficient partiel boulons",
            formula_values=f"γM2 = {c.gamma_m2:.2f}",
            result=c.gamma_m2,
            unit="-",
            ref=f"EC3-1-8 — §2.2 — AN {c.country}",
        )

    # =================================================================
    # Rapport complet
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        return [
            self.fyb_report,
            self.fub_report,
            self.gamma_m2_report,
        ]

    # =================================================================
    # Représentation
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"MatBolt(grade='{self._grade}', fyb={self._fyb}, "
            f"fub={self._fub}, country='{self._country}')"
        )

    def __str__(self) -> str:
        lines = [
            f"{'=' * 60}",
            f"  {self._name} — AN {self._country}",
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

    # --- Par classe ---
    b88 = MatBolt(grade="8.8")
    print(b88)

    # --- Par valeurs ---
    custom = MatBolt(fyb=900, fub=1000, name="Boulon spécial")
    print(custom)

    # --- Accès ---
    print(f"\nfyb = {b88.fyb} MPa")
    print(f"fub = {b88.fub} MPa")
    print(f"γM2 = {b88.gamma_m2}")

    # --- Changement AN ---
    b88.country = "UK"
    print(f"\nγM2 (UK) = {b88.gamma_m2}")
    print(b88.gamma_m2_report)

    # --- Rapport ---
    print("\n--- Rapport complet ---")
    for r in b88.all_reports():
        print(f"  {r.name:8s} = {r.result:10.2f} {r.unit:5s}  |  {r.ref}")
