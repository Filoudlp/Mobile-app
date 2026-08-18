#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define reinforcement steel material properties according to EC2.

    References:
        - EN 1992-1-1 (Eurocode 2) — §3.2, Table C.1, Annexe C

    Supported National Annexes:
        - FR : France (default)
        - BE : Belgique
        - UK : Royaume-Uni
"""

__all__ = ['MatReinforcement']

from dataclasses import dataclass
from typing import Optional

from core.mat.materials import Material
from core.formula import FormulaResult
from core.coefficient import NationalAnnex, Country
from enum import Enum


# =============================================================================
# Classes de ductilité — EC2 Annexe C, Table C.1
# =============================================================================

@dataclass(frozen=True)
class _DuctilityData:
    """
    Propriétés mécaniques associées à une classe de ductilité.

    :param k_min: Rapport ft/fy minimal (ft = k × fy) [-]
    :param epsilon_uk: Déformation ultime caractéristique minimale [-]
    """
    k_min: float
    epsilon_uk: float


_DUCTILITY_CLASSES: dict[str, _DuctilityData] = {
    "A": _DuctilityData(k_min=1.05, epsilon_uk=25e-3),
    "B": _DuctilityData(k_min=1.08, epsilon_uk=50e-3),
    "C": _DuctilityData(k_min=1.15, epsilon_uk=75e-3),
}

class SteelDiagram(Enum):
    """Type de diagramme contrainte-déformation — EC2 §3.2.7"""
    HORIZONTAL = "horizontal"   # palier horizontal à fyd
    INCLINED   = "inclined"     # branche inclinée avec écrouissage

    @classmethod
    def validate(cls, value) -> "SteelDiagram":
        if isinstance(value, cls):
            return value
        if value not in cls.__members__:
            raise ValueError(
                f"Diagramme '{value}' non supporté. "
                f"Choix possibles : {list(cls.__members__.keys())}"
            )
        return cls[value]

# =============================================================================
# Classe principale
# =============================================================================

class MatReinforcement(Material):
    """
    Armature pour béton armé selon l'EC2 §3.2 et Annexe C.

    Hérite de Material (E, nu, alpha).

    Deux modes d'utilisation :
        >>> ha = MatReinforcement(fyk=500, ductility_class="B")
        >>> ha = MatReinforcement(fyk=500, ductility_class="B", country="UK")

    :param fyk: Limite d'élasticité caractéristique [MPa]
    :param ductility_class: Classe de ductilité ("A", "B" ou "C")
    :param Es: Module d'Young des armatures [MPa] — défaut 200 000
    :param nu: Coefficient de Poisson [-] — défaut 0.3
    :param alpha: Coefficient de dilatation thermique [K⁻¹] — défaut 10e-6
    :param country: Code Annexe Nationale — défaut "FR"
    :param name: Nom libre pour affichage — défaut auto-généré
    """

    _DEFAULT_E = 200000.0       # MPa
    _DEFAULT_NU = 0.3
    _DEFAULT_ALPHA = 10e-6      # K⁻¹
    _DEFAULT_RHO = 7850.0       # kg/m³

    def __init__(
        self,
        fyk: float,
        ductility_class: str = "B",
        country: str = "FR",
        coefficients: Optional[SteelCoefficients] = None,
        diagram: SteelDiagram = SteelDiagram.INCLINED,
    ) -> None:
        # ----- Validation classe de ductilité -----
        ductility_class = ductility_class.upper()
        if ductility_class not in _DUCTILITY_CLASSES:
            raise ValueError(
                f"Classe de ductilité '{ductility_class}' inconnue. "
                f"Choix possibles : {list(_DUCTILITY_CLASSES.keys())}"
            )

        # ----- Validation AN -----
        self._country = country.upper()
        if coefficients is not None:
            self._coefficients = coefficients
        else:
            self._coefficients = self._get_coefficients(self._country)

        # ----- Appel constructeur parent -----
        super().__init__(
            name=f"B{int(fyk)}{ductility_class}",
            E=self._DEFAULT_E,
            nu=self._DEFAULT_NU,
            rho=self._DEFAULT_RHO)

        # ----- Attributs privés -----
        self._fyk: float = fyk
        self._Es: float = self._DEFAULT_E
        self._ductility_class: str = ductility_class
        self._country: str = country

        # Données de ductilité
        ductility = _DUCTILITY_CLASSES[ductility_class]
        self._k: float = ductility.k_min
        self._epsilon_uk: float = ductility.epsilon_uk

        # Nom pour affichage
        self._name: str = f"B{int(fyk)}{ductility_class}"

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

    # =================================================================
    # Setters dynamiques
    # =================================================================

    @property
    def diagram(self) -> SteelDiagram:
        return self._diagram

    @diagram.setter
    def diagram(self, value: SteelDiagram):
        self._diagram = SteelDiagram.validate(value)

    @property
    def fyk(self) -> float:
        """Limite d'élasticité caractéristique [MPa]"""
        return self._fyk

    @fyk.setter
    def fyk(self, value: float) -> None:
        """Met à jour fyk → fyd, ftk, ftd, εyd se recalculent automatiquement."""
        self._fyk = value
        self._name = f"B{int(value)}{self._ductility_class}"

    @property
    def Es(self) -> float:
        """Module d'Young des armatures [MPa]"""
        return self._Es

    @property
    def ductility_class(self) -> str:
        """Classe de ductilité (A, B ou C)"""
        return self._ductility_class

    @ductility_class.setter
    def ductility_class(self, value: str) -> None:
        """Met à jour la classe de ductilité → k, εuk se recalculent."""
        value = value.upper()
        if value not in _DUCTILITY_CLASSES:
            raise ValueError(
                f"Classe de ductilité '{value}' inconnue. "
                f"Choix possibles : {list(_DUCTILITY_CLASSES.keys())}"
            )
        self._ductility_class = value
        ductility = _DUCTILITY_CLASSES[value]
        self._k = ductility.k_min
        self._epsilon_uk = ductility.epsilon_uk
        self._name = f"B{int(self._fyk)}{value}"

    @property
    def country(self) -> str:
        """Code Annexe Nationale"""
        return self._country

    @country.setter
    def country(self, value: str) -> None:
        """Change l'Annexe Nationale → γs se met à jour."""
        self._country = value.upper()
        self._coefficients = self._get_coefficients(self._country)

    @property
    def name(self) -> str:
        """Nom de l'armature"""
        return self._name

    # =================================================================
    # Propriétés caractéristiques (EC2 §3.2.7, Table C.1)
    # =================================================================

    # ---- fyk ----

    @property
    def fyk_report(self) -> FormulaResult:
        return FormulaResult(
            name="fyk",
            formula="fyk = limite d'élasticité caractéristique",
            formula_values=f"fyk = {self._fyk:.2f}",
            result=self._fyk,
            unit="MPa",
            ref="EC2 — Table C.1",
        )

    # ---- Es ----

    @property
    def Es_report(self) -> FormulaResult:
        return FormulaResult(
            name="Es",
            formula="Es = module d'Young des armatures",
            formula_values=f"Es = {self._Es:.0f}",
            result=self._Es,
            unit="MPa",
            ref="EC2 — §3.2.7(4)",
        )

    # ---- k (ft/fy) ----

    @property
    def k(self) -> float:
        """Rapport minimal (ft/fy)k selon classe de ductilité [-] — EC2 Table C.1"""
        return self._k

    @property
    def k_report(self) -> FormulaResult:
        return FormulaResult(
            name="k",
            formula="k = (ft/fy)k — valeur minimale selon classe de ductilité",
            formula_values=f"k(classe {self._ductility_class}) = {self._k:.2f}",
            result=self._k,
            unit="-",
            ref="EC2 — Table C.1",
        )

    # ---- ftk ----

    @property
    def ftk(self) -> float:
        """Résistance à la traction caractéristique ftk = k × fyk [MPa] — EC2 Table C.1"""
        return self._k * self._fyk

    @property
    def ftk_report(self) -> FormulaResult:
        return FormulaResult(
            name="ftk",
            formula="ftk = k × fyk",
            formula_values=f"ftk = {self._k:.2f} × {self._fyk:.2f} = {self.ftk:.2f}",
            result=self.ftk,
            unit="MPa",
            ref="EC2 — Table C.1",
        )

    # ---- epsilon_uk ----

    @property
    def epsilon_uk(self) -> float:
        """Déformation ultime caractéristique minimale [-] — EC2 Table C.1"""
        return self._epsilon_uk

    @property
    def epsilon_uk_report(self) -> FormulaResult:
        return FormulaResult(
            name="εuk",
            formula="εuk = valeur minimale selon classe de ductilité",
            formula_values=f"εuk(classe {self._ductility_class}) = {self._epsilon_uk * 1000:.1f} ‰",
            result=self._epsilon_uk,
            unit="-",
            ref="EC2 — Table C.1",
        )

    # =================================================================
    # Propriétés de calcul (dépendent de l'AN)
    # =================================================================

    # ---- gamma_s ----

    @property
    def gamma_s(self) -> float:
        """Coefficient partiel armatures [-]"""
        return self._coefficients.ec2.gamma_s

    @property
    def gamma_s_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="γs",
            formula="γs = coefficient partiel armatures",
            formula_values=f"γs = {c.ec2.gamma_s:.2f}",
            result=c.ec2.gamma_s,   
            unit="-",
            ref=f"EC2 — §2.4.2.4 — AN {c.country}",
        )

    # ---- fyd ----

    @property
    def fyd(self) -> float:
        """Résistance de calcul fyd = fyk / γs [MPa] — EC2 §3.2.7(2)"""
        return self._fyk / self._coefficients.ec2.gamma_s

    @property
    def fyd_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="fyd",
            formula="fyd = fyk / γs",
            formula_values=f"fyd = {self._fyk:.2f} / {c.ec2.gamma_s:.2f} = {self.fyd:.2f}",
            result=self.fyd,
            unit="MPa",
            ref=f"EC2 — §3.2.7(2) — AN {c.country}",
        )

    # ---- ftd ----

    @property
    def ftd(self) -> float:
        """Résistance ultime de calcul ftd = ftk / γs [MPa]"""
        return self.ftk / self._coefficients.ec2.gamma_s

    @property
    def ftd_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="ftd",
            formula="ftd = ftk / γs",
            formula_values=f"ftd = {self.ftk:.2f} / {c.ec2.gamma_s:.2f} = {self.ftd:.2f}",
            result=self.ftd,
            unit="MPa",
            ref=f"EC2 — §3.2.7(2) — AN {c.country}",
        )

    # ---- epsilon_ud ----

    @property
    def epsilon_ud(self) -> float:
        """Déformation ultime de calcul εud = 0.9 × εuk [-] — EC2 §3.2.7(2)"""
        return 0.9 * self._epsilon_uk

    @property
    def epsilon_ud_report(self) -> FormulaResult:
        return FormulaResult(
            name="εud",
            formula="εud = 0.9 × εuk",
            formula_values=f"εud = 0.9 × {self._epsilon_uk * 1000:.1f}‰ = {self.epsilon_ud * 1000:.1f} ‰",
            result=self.epsilon_ud,
            unit="-",
            ref="EC2 — §3.2.7(2)",
        )

    # ---- epsilon_yd ----

    @property
    def epsilon_yd(self) -> float:
        """Déformation élastique de calcul εyd = fyd / Es [-] — EC2 §3.2.7(4)"""
        if self._Es == 0:
            return 0.0
        return self.fyd / self._Es

    @property
    def epsilon_yd_report(self) -> FormulaResult:
        return FormulaResult(
            name="εyd",
            formula="εyd = fyd / Es",
            formula_values=f"εyd = {self.fyd:.2f} / {self._Es:.0f} = {self.epsilon_yd * 1000:.4f} ‰",
            result=self.epsilon_yd,
            unit="-",
            ref="EC2 — §3.2.7(4)",
        )

    # ---- sigma_sc ----

    def sigma_sc(self, epsilon_sc: float) -> float:
        """
        Contrainte de calcul dans l'acier comprimé σsc [MPa] — EC2 §3.2.7

        :param epsilon_sc: Déformation de calcul dans l'acier comprimé [-]
        :return:           Contrainte σsc [MPa]
        """
        if epsilon_sc < 0:
            raise ValueError(f"εsc doit être positif, reçu : {epsilon_sc}")

        # Domaine élastique
        if epsilon_sc <= self.epsilon_yd:
            return self._Es * epsilon_sc

        # Domaine plastique — diagramme horizontal
        if self._diagram == SteelDiagram.HORIZONTAL:
            return self.fyd

        # Domaine plastique — diagramme incliné (écrouissage)
        if epsilon_sc >= self.epsilon_ud:
            return self._k * self.fyd  # plafonné à εud

        return self.fyd * (
            1 + (self._k - 1)
            * (epsilon_sc - self.epsilon_yd)
            / (self.epsilon_ud - self.epsilon_yd)
        )


    def sigma_sc_report(self, epsilon_sc: float, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σsc — EC2 §3.2.7"""
        r = self.sigma_sc(epsilon_sc)  # epsilon_sc passé en paramètre

        if epsilon_sc <= self.epsilon_yd:
            formula = "σsc = Es · εsc"
            fv = (
                f"σsc = {self._Es:.0f} × {epsilon_sc * 1000:.4f}‰"
                f" = {r:.2f} MPa  (domaine élastique)"
            ) if with_values else ""

        elif self._diagram == SteelDiagram.HORIZONTAL:
            formula = "σsc = fyd"
            fv = (
                f"σsc = fyd = {r:.2f} MPa  (domaine plastique — diagramme horizontal)"
            ) if with_values else ""

        elif epsilon_sc >= self.epsilon_ud:
            formula = "σsc = k · fyd"
            fv = (
                f"σsc = {self._k:.2f} × {self.fyd:.2f}"
                f" = {r:.2f} MPa  (plafonné à εud)"
            ) if with_values else ""

        else:
            formula = "σsc = fyd · [1 + (k-1) · (εsc - εyd) / (εud - εyd)]"
            fv = (
                f"σsc = {self.fyd:.2f} × [1 + ({self._k:.2f} - 1)"
                f" × ({epsilon_sc * 1000:.4f}‰ - {self.epsilon_yd * 1000:.4f}‰)"
                f" / ({self.epsilon_ud * 1000:.4f}‰ - {self.epsilon_yd * 1000:.4f}‰)]"
                f" = {r:.2f} MPa  (écrouissage)"
            ) if with_values else ""

        return FormulaResult(
            name="σsc",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — §3.2.7",
        )


    # =================================================================
    # Rapport complet
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        """Renvoie la liste de tous les FormulaResult pour un rapport complet."""
        return [
            self.fyk_report,
            self.Es_report,
            self.k_report,
            self.ftk_report,
            self.epsilon_uk_report,
            self.gamma_s_report,
            self.fyd_report,
            self.ftd_report,
            self.epsilon_ud_report,
            self.epsilon_yd_report,
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"MatReinforcement(fyk={self._fyk}, ductility_class='{self._ductility_class}', "
            f"country='{self._country}')"
        )

    def __str__(self) -> str:
        lines = [
            f"{'=' * 65}",
            f"  Armature {self._name} — Classe {self._ductility_class} — AN {self._country}",
            f"{'=' * 65}",
        ]
        for r in self.all_reports():
            lines.append(f"  {r.formula_values:55s} [{r.unit}]  ({r.ref})")
        lines.append(f"{'=' * 65}")
        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    # --- Armature classique B500B ---
    ha = MatReinforcement(fyk=500, ductility_class="B")
    print(ha)

    # --- Accès individuel ---
    print(f"\nfyd = {ha.fyd:.2f} MPa")
    print(ha.fyd_report)

    print(f"\nεyd = {ha.epsilon_yd * 1000:.4f} ‰")
    print(ha.epsilon_yd_report)

    print(f"\nftk = {ha.ftk:.2f} MPa")
    print(ha.ftk_report)

    # --- Changement de ductilité ---
    print("\n--- Passage en classe C ---")
    ha.ductility_class = "C"
    print(f"k   = {ha.k}")
    print(f"εuk = {ha.epsilon_uk * 1000:.1f} ‰")
    print(ha)

    # --- Changement AN ---
    print("\n--- Passage AN UK ---")
    ha.country = "UK"
    print(ha.fyd_report)

    # --- Itération rapport ---
    print("\n--- Rapport complet ---")
    for r in ha.all_reports():
        print(f"  {r.name:12s} = {r.result:12.4f} {r.unit:5s}  |  {r.ref}")