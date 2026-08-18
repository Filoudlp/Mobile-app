#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define structural steel material properties according to EC3.

    References:
        - EN 1993-1-1 (Eurocode 3) — Table 3.1

    Supported National Annexes:
        - FR : France (default)
        - BE : Belgique
        - UK : Royaume-Uni
"""

__all__ = ['MatSteel']

from dataclasses import dataclass
from typing import Optional

from core.mat.materials import Material
from core.formula import FormulaResult
from core.coefficient import NationalAnnex, Country


# =============================================================================
# Registre des nuances d'acier — EC3 Table 3.1
# =============================================================================

# EN 1993-1-1 — Tableau 3.1
# Structure : {norme: {nuance: {épaisseur_max: (fy, fu)}}}
# (fy, fu) en [N/mm²] — None si non spécifié par la norme

_STEEL_GRADES: dict[str, dict[str, dict[float, tuple[float, float]]]] = {

    # ----------------------------------------------------------------
    # Aciers laminés à chaud
    # ----------------------------------------------------------------

    "EN 10025-2": {
        "S 235":        {40: (235, 360), 80: (215, 360)},
        "S 275":        {40: (275, 430), 80: (255, 410)},
        "S 355":        {40: (355, 490), 80: (335, 470)},
        "S 450":        {40: (440, 550), 80: (410, 550)},
    },

    "EN 10025-3": {
        "S 275 N/NL":   {40: (275, 390), 80: (255, 370)},
        "S 355 N/NL":   {40: (355, 490), 80: (335, 470)},
        "S 420 N/NL":   {40: (420, 520), 80: (390, 520)},
        "S 460 N/NL":   {40: (460, 540), 80: (430, 540)},
    },

    "EN 10025-4": {
        "S 275 M/ML":   {40: (275, 370), 80: (255, 360)},
        "S 355 M/ML":   {40: (355, 470), 80: (335, 450)},
        "S 420 M/ML":   {40: (420, 520), 80: (390, 500)},
        "S 460 M/ML":   {40: (460, 540), 80: (430, 530)},
    },

    "EN 10025-5": {
        "S 235 W":      {40: (235, 360), 80: (215, 340)},
        "S 355 W":      {40: (355, 490), 80: (335, 490)},
    },

    "EN 10025-6": {
        "S 460 Q/QL/QL1": {40: (460, 570), 80: (440, 550)},
    },

    # ----------------------------------------------------------------
    # Profils creux de construction — à chaud
    # ----------------------------------------------------------------

    "EN 10210-1": {
        "S 235 H":      {40: (235, 360), 80: (215, 340)},
        "S 275 H":      {40: (275, 430), 80: (255, 410)},
        "S 355 H":      {40: (355, 510), 80: (335, 490)},
        "S 275 NH/NLH": {40: (275, 390), 80: (255, 370)},
        "S 355 NH/NLH": {40: (355, 490), 80: (335, 470)},
        "S 420 NH/NHL": {40: (420, 540), 80: (390, 520)},
        "S 460 NH/NLH": {40: (460, 560), 80: (430, 550)},
    },

    # ----------------------------------------------------------------
    # Profils creux de construction — à froid
    # ----------------------------------------------------------------

    "EN 10219-1": {
        "S 235 H":      {40: (235, 360), 80: (None, None)},
        "S 275 H":      {40: (275, 430), 80: (None, None)},
        "S 355 H":      {40: (355, 510), 80: (None, None)},
        "S 275 NH/NLH": {40: (275, 370), 80: (None, None)},
        "S 355 NH/NLH": {40: (355, 470), 80: (None, None)},
        "S 420 NH/NLH": {40: (460, 550), 80: (None, None)},
        "S 275 MH/MLH": {40: (275, 360), 80: (None, None)},
        "S 355 MH/MLH": {40: (355, 470), 80: (None, None)},
        "S 420 MH/MLH": {40: (420, 500), 80: (None, None)},
        "S 460 MH/MLH": {40: (460, 530), 80: (None, None)},
    },
}


def _get_fy_fu(
    grade: str,
    thickness: float,
    norme: str = "EN 10025-2"
) -> tuple[float, float]:
    """
    Retourne (fy, fu) selon la norme, nuance et l'épaisseur.

    Réf : EN 1993-1-1 — Tableau 3.1

    :param grade:     Nuance d'acier (ex: "S355", "S 355", "S355H", "S 355 H")
    :param thickness: Épaisseur de l'élément [mm]
    :param norme:     Norme produit (défaut: "EN 10025-2")
    :return:          Tuple (fy [N/mm²], fu [N/mm²])
    :raises KeyError:  Si la norme n'existe pas
    :raises KeyError:  Si la nuance n'existe pas pour cette norme
    :raises ValueError: Si l'épaisseur est hors limites
    :raises ValueError: Si les valeurs ne sont pas définies pour cette épaisseur
    """
    # Validation norme
    if norme not in _STEEL_GRADES:
        available_normes = list(_STEEL_GRADES.keys())
        raise KeyError(
            f"Norme '{norme}' non disponible.\n"
            f"Normes disponibles : {available_normes}"
        )

    # Normaliser la nuance
    # 1. Supprimer espaces inutiles + majuscules
    # 2. Ajouter espaces après "S" si absent
    grade_normalized = grade.strip().upper()
    
    # Insérer un espace après "S" s'il n'y en a pas
    if grade_normalized.startswith("S") and len(grade_normalized) > 1:
        if grade_normalized[1] != " ":
            grade_normalized = "S " + grade_normalized[1:]

    # Validation nuance pour cette norme
    if grade_normalized not in _STEEL_GRADES[norme]:
        available_grades = list(_STEEL_GRADES[norme].keys())
        raise KeyError(
            f"Nuance '{grade}' non disponible pour {norme}.\n"
            f"Nuances disponibles : {available_grades}"
        )

    # Récupérer les paliers d'épaisseur pour cette nuance
    thresholds = _STEEL_GRADES[norme][grade_normalized]

    # Parcourir les seuils d'épaisseur (triés)
    for t_max in sorted(thresholds.keys()):
        if thickness <= t_max:
            fy, fu = thresholds[t_max]

            # Vérifier que les valeurs sont définies
            if fy is None or fu is None:
                raise ValueError(
                    f"Valeurs non définies pour {grade} ({norme}) "
                    f"à épaisseur t={thickness} mm.\n"
                    f"Cette combinaison n'est pas couverte par la norme."
                )

            return fy, fu

    # Épaisseur hors limites
    max_thickness = max(thresholds.keys())
    raise ValueError(
        f"Épaisseur t={thickness} mm hors limites pour {grade} ({norme}).\n"
        f"Épaisseur maximale : {max_thickness} mm"
    )


# =============================================================================
# MatSteel
# =============================================================================

class MatSteel(Material):
    """
    Acier de construction selon EC3 — EN 1993-1-1.

    Deux modes d'instanciation :
        - Par nuance et épaisseur : MatSteel(grade="S355", thickness=20)
        - Par valeurs directes    : MatSteel(fy=345, fu=490)

    :param grade:        Nuance d'acier ("S235", "S275", "S355", "S460", etc.)
                         Format accepté : "S355" ou "S 355" (espaces ignorés)
    :param thickness:    Épaisseur de l'élément [mm] (pour déterminer fy/fu).
                         Défaut : 16 mm
    :param fy:           Limite d'élasticité [MPa] (prioritaire sur grade/thickness)
    :param fu:           Résistance ultime en traction [MPa] (prioritaire sur grade/thickness)
    :param country:      Code pays pour l'Annexe Nationale de EN 1993-1-1.
                         Choix : "FR" (défaut), "DE", "UK", "NL", etc.
                         Impacte les coefficients partiels (γM0, γM1, γM2).
    :param coefficients: Coefficients partiels personnalisés (SteelCoefficients).
                         Prioritaire sur country.
    :param norme:        Norme produit acier selon EN 1993-1-1 — Tableau 3.1.
                         Choix : "EN 10025-2" (défaut - laminés à chaud),
                                 "EN 10025-3" (N/NL),
                                 "EN 10025-4" (M/ML),
                                 "EN 10025-5" (W),
                                 "EN 10025-6" (Q/QL),
                                 "EN 10210-1" (profils creux - à chaud),
                                 "EN 10219-1" (profils creux - formés à froid).
                         Utilisée pour le lookup (grade, thickness) → (fy, fu).

    :raises KeyError:    Si norme ou grade invalide
    :raises ValueError:  Si épaisseur hors limites pour la nuance/norme

    Exemple
    -------
    >>> # Mode 1 : Par nuance (récupère fy/fu du tableau)
    >>> acier = MatSteel(grade="S355", thickness=30, country="FR")
    >>> acier.fy
    355.0

    >>> # Mode 2 : Par valeurs directes
    >>> acier = MatSteel(fy=345, fu=490)
    >>> acier.fy
    345.0

    >>> # Mode 3 : Norme produit spécifique
    >>> acier = MatSteel(grade="S 275 H", thickness=50, norme="EN 10210-1")
    >>> # Récupère fy/fu pour profils creux EN 10210-1
    """

    _DEFAULT_E = 210000.0       # MPa
    _DEFAULT_NU = 0.3
    _DEFAULT_ALPHA = 12e-6      # K⁻¹
    _DEFAULT_RHO = 7850.0       # kg/m³

    def __init__(
        self,
        grade: Optional[str] = None,
        thickness: float = 16.0,
        fy: Optional[float] = None,
        fu: Optional[float] = None,
        country: str = "FR",
        coefficients: Optional["NationalAnnex"] = None,
        norme: str = "EN 10025-2",
        gamma_m0: Optional[float] = None,
        gamma_m1: Optional[float] = None,
        gamma_m2: Optional[float] = None,
    ) -> None:

        # -- Résistances --
        if fy is not None and fu is not None:
            self._fy = fy
            self._fu = fu
            self._grade = grade or "Custom"
            self._thickness = thickness
        elif grade is not None:
            self._grade = grade.upper()
            self._thickness = thickness
            self._fy, self._fu = _get_fy_fu(self._grade, self._thickness, norme)
        else:
            raise ValueError(
                "Fournir soit (grade + thickness), soit (fy + fu)."
            )

        # -- Annexe Nationale --
        self._country = country.upper()
        if coefficients is not None:
            self._coefficients = coefficients
        else:
            self._coefficients = self._get_coefficients(self._country)

        # -- Surcharges directes des coefficients partiels ---------------
        # Utile pour les normes hors Annexe Nationale EC3 (ex. SIA 263),
        # où γM0/γM1/γM2 ne sont pas dérivés d'un pays mais de la norme.
        self._gamma_m0_override = gamma_m0
        self._gamma_m1_override = gamma_m1
        self._gamma_m2_override = gamma_m2

        # -- Init Material --
        super().__init__(
            name=self._grade,
            E=self._DEFAULT_E,
            nu=self._DEFAULT_NU,
            rho=self._DEFAULT_RHO,
        )

    # ---- helpers internes ----

    @staticmethod
    def _get_coefficients(country: str) -> SteelCoefficients:
        country = country.upper()
        if country not in Country.__members__.keys():
            raise ValueError(
                f"Annexe Nationale '{country}' non supportée. "
                f"Choix possibles : {list(Country.__members__.keys())}"
            )
        return NationalAnnex.from_country(Country[country])

    # ---- country (dynamique) ----

    @property
    def country(self) -> str:
        return self._country

    @country.setter
    def country(self, value: str) -> None:
        self._country = value.upper()
        self._coefficients = self._get_coefficients(self._country)

    @property
    def coefficients(self) -> SteelCoefficients:
        return self._coefficients

    # =================================================================
    # Propriétés de base
    # =================================================================

    @property
    def grade(self) -> str:
        return self._grade

    @grade.setter
    def grade(self, value: str) -> None:
        """Permet de changer la nuance et mettre à jour fy/fu en conséquence.
        Note : L'épaisseur doit être définie pour que cela fonctionne."""
        self._grade = value.upper()
        if self._thickness is not None:
            self._fy, self._fu = _get_fy_fu(self._grade, self._thickness)
        else:
            raise ValueError(
                "L'épaisseur doit être définie pour mettre à jour fy/fu lors du changement de nuance."
            )

    @property
    def thickness(self) -> float:
        return self._thickness

    @thickness.setter
    def thickness(self, value: float, norme: str = "EN 10025-2") -> None:
        """Permet de changer l'épaisseur et mettre à jour fy/fu en conséquence.
        Note : La nuance doit être définie pour que cela fonctionne."""
        self._thickness = value
        if self._grade is not None:
            self._fy, self._fu = _get_fy_fu(self._grade, self._thickness, norme)
        else:
            raise ValueError(
                "La nuance doit être définie pour mettre à jour fy/fu lors du changement d'épaisseur."
            )

    # ---- fy ----

    @property
    def fy(self) -> float:
        return self._fy

    @fy.setter 
    def fy(self, value: float) -> None:
        """Permet de changer fy directement (mode valeurs directes)."""
        self._fy = value

    @property
    def fy_report(self) -> FormulaResult:
        return FormulaResult(
            name="fy",
            formula="fy = f(nuance, épaisseur) — EC3 Table 3.1",
            formula_values=f"fy({self._grade}, t≤{self._thickness:.0f}mm) = {self._fy:.2f}",
            result=self._fy,
            unit="MPa",
            ref="EC3 — Table 3.1",
        )

    # ---- fu ----

    @property
    def fu(self) -> float:
        return self._fu

    @fu.setter 
    def fu(self, value: float) -> None:
        """Permet de changer fu directement (mode valeurs directes)."""
        self._fu = value

    @property
    def fu_report(self) -> FormulaResult:
        return FormulaResult(
            name="fu",
            formula="fu = f(nuance, épaisseur) — EC3 Table 3.1",
            formula_values=f"fu({self._grade}, t≤{self._thickness:.0f}mm) = {self._fu:.2f}",
            result=self._fu,
            unit="MPa",
            ref="EC3 — Table 3.1",
        )

    # ---- epsilon (paramètre de ductilité) ----

    @property
    def epsilon(self) -> float:
        """ε = √(235/fy) — EC3 §5.5.2"""
        return (235 / self._fy) ** 0.5

    @property
    def epsilon_report(self) -> FormulaResult:
        return FormulaResult(
            name="ε",
            formula="ε = √(235 / fy)",
            formula_values=f"ε = √(235 / {self._fy:.2f}) = {self.epsilon:.4f}",
            result=self.epsilon,
            unit="-",
            ref="EC3 — §5.5.2",
        )

    # =================================================================
    # Propriétés dépendantes de l'AN (gamma)
    # =================================================================

    @property
    def gamma_m0(self) -> float:
        if self._gamma_m0_override is not None:
            return self._gamma_m0_override
        return self._coefficients.ec3.gamma_m0

    @property
    def gamma_m1(self) -> float:
        if self._gamma_m1_override is not None:
            return self._gamma_m1_override
        return self._coefficients.ec3.gamma_m1

    @property
    def gamma_m2(self) -> float:
        if self._gamma_m2_override is not None:
            return self._gamma_m2_override
        return self._coefficients.ec3.gamma_m2

    # =================================================================
    # Résistances de calcul
    # =================================================================

    # ---- fy / gamma_m0 ----

    @property
    def fy_d(self) -> float:
        """fy / γM0"""
        return self._fy / self._coefficients.ec3.gamma_m0

    @property
    def fy_d_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="fy,d",
            formula="fy,d = fy / γM0",
            formula_values=f"fy,d = {self._fy:.2f} / {c.ec3.gamma_m0} = {self.fy_d:.2f}",
            result=self.fy_d,
            unit="MPa",
            ref=f"EC3 — §6.1(1) — AN {c.country}",
        )

    # ---- fu / gamma_m2 ----

    @property
    def fu_d(self) -> float:
        """fu / γM2"""
        return self._fu / self._coefficients.ec3.gamma_m2

    @property
    def fu_d_report(self) -> FormulaResult:
        c = self._coefficients
        return FormulaResult(
            name="fu,d",
            formula="fu,d = fu / γM2",
            formula_values=f"fu,d = {self._fu:.2f} / {c.ec3.gamma_m2} = {self.fu_d:.2f}",
            result=self.fu_d,
            unit="MPa",
            ref=f"EC3 — §6.1(1) — AN {c.country}",
        )

    # =================================================================
    # Rapport complet
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        """Renvoie la liste de tous les FormulaResult pour un rapport complet."""
        return [
            self.fy_report,
            self.fu_report,
            self.epsilon_report,
            self.fy_d_report,
            self.fu_d_report,
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"MatSteel(grade='{self._grade}', thickness={self._thickness}, "
            f"fy={self._fy}, fu={self._fu}, country='{self._country}')"
        )

    def __str__(self) -> str:
        lines = [
            f"{'=' * 60}",
            f"  Acier {self._grade} — t={self._thickness:.0f}mm — AN {self._country}",
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

    # Par nuance
    s355 = MatSteel(grade="S355", thickness=20)
    print(s355)

    # Par valeurs directes
    custom = MatSteel(fy=345, fu=490)
    print(custom)

    # Accès individuel
    print(f"\nfy = {s355.fy} MPa")
    print(f"ε  = {s355.epsilon:.4f}")
    print(s355.epsilon_report)

    # Changement AN
    s355.country = "UK"
    print(f"\nfu,d (UK) = {s355.fu_d:.2f} MPa")
    print(s355.fu_d_report)
