#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classification des sections transversales selon l'EC3-1-1 §5.5 — Tableau 5.2.

Détermine la classe (1, 2 ou 3) d'une section en I/H, RHS ou CHS
en fonction du cas de charge (compression, flexion, flexion+compression).

La classe 4 n'est pas couverte dans cette version : si les limites de
classe 3 sont dépassées, la classe retournée est 3 avec un avertissement.
"""

__all__ = ['Classification']

import math
import warnings
from typing import TypeVar, Optional, Dict

from core.formula import FormulaResult, FormulaCollection

section = TypeVar('section')
material = TypeVar('material')

# ---------------------------------------------------------------------------
# Constantes — Limites c/t du Tableau 5.2 (EC3-1-1)
# ---------------------------------------------------------------------------

# Semelle en console (outstand flange) — compression
FLANGE_OUTSTAND_LIMITS: Dict[int, float] = {
    1: 9.0,
    2: 10.0,
    3: 14.0,
}

# Âme — flexion pure (internal part subject to bending)
WEB_BENDING_LIMITS: Dict[int, float] = {
    1: 72.0,
    2: 83.0,
    3: 124.0,
}

# Âme — compression pure (internal part subject to compression)
WEB_COMPRESSION_LIMITS: Dict[int, float] = {
    1: 33.0,
    2: 38.0,
    3: 42.0,
}

# RHS — paroi en flexion (internal part subject to bending)
RHS_BENDING_LIMITS: Dict[int, float] = {
    1: 72.0,
    2: 83.0,
    3: 124.0,
}

# RHS — paroi en compression (internal part subject to compression)
RHS_COMPRESSION_LIMITS: Dict[int, float] = {
    1: 33.0,
    2: 38.0,
    3: 42.0,
}

# CHS — d/t limites
CHS_LIMITS: Dict[int, float] = {
    1: 50.0,   # 50 ε²
    2: 70.0,   # 70 ε²
    3: 90.0,   # 90 ε²
}


class Classification:
    """
    Classification d'une section transversale selon l'EC3-1-1 §5.5.

    Prend en charge les profilés I/H, RHS et CHS.

    Parameters
    ----------
    load_case : str
        Cas de charge : ``"compression"``, ``"flexion"`` ou
        ``"flexion_compression"``.
    mat : material, optional
        Objet matériau fournissant ``fy`` et ``E``.
    sec : section, optional
        Objet section fournissant les dimensions géométriques.
    Ned : float
        Effort normal de calcul [N] (positif en compression).
        Utilisé uniquement pour ``"flexion_compression"``.
    Med : float
        Moment fléchissant de calcul [N·mm].
        Utilisé uniquement pour ``"flexion_compression"``.
    **kwargs
        Paramètres manuels : ``fy``, ``E``, ``h``, ``b``, ``tw``, ``tf``,
        ``d``, ``c_flange``, ``section_type``, ``D`` (diamètre CHS),
        ``t`` (épaisseur CHS).
    """

    _VALID_LOAD_CASES = ("compression", "flexion", "flexion_compression")
    _VALID_SECTION_TYPES = ("I", "RHS", "CHS")

    def __init__(self,
                 load_case: str,
                 mat: Optional[material] = None,
                 sec: Optional[section] = None,
                 Ned: float = 0.0,
                 Med: float = 0.0,
                 **kwargs) -> None:

        # --- Cas de charge ---
        if load_case not in self._VALID_LOAD_CASES:
            raise ValueError(
                f"load_case doit être parmi {self._VALID_LOAD_CASES}, "
                f"reçu : '{load_case}'"
            )
        self.__load_case: str = load_case
        self.__ned: float = abs(Ned)
        self.__med: float = abs(Med)

        # --- Matériau ---
        self.__fy: float = mat.fy if mat else kwargs.get("fy", 235.0)
        self.__E: float = mat.E if mat else kwargs.get("E", 210000.0)

        # --- Section ---
        self.__section_type: str = (
            sec.section_type if sec else kwargs.get("section_type", "I")
        )
        if self.__section_type not in self._VALID_SECTION_TYPES:
            raise ValueError(
                f"section_type doit être parmi {self._VALID_SECTION_TYPES}, "
                f"reçu : '{self.__section_type}'"
            )

        # Dimensions profilé I/H
        self.__h: float = sec.h if sec else kwargs.get("h", 0.0)
        self.__b: float = sec.b if sec else kwargs.get("b", 0.0)
        self.__tw: float = sec.tw if sec else kwargs.get("tw", 0.0)
        self.__tf: float = sec.tf if sec else kwargs.get("tf", 0.0)
        self.__d: float = sec.d if sec else kwargs.get("d", 0.0)
        self.__c_flange: float = (
            sec.c_flange if sec else kwargs.get("c_flange", 0.0)
        )
        self.__A: float = sec.A if sec else kwargs.get("A", 0.0)

        # Dimensions CHS
        self.__D: float = kwargs.get("D", 0.0)
        self.__t_chs: float = kwargs.get("t", 0.0)

        # Si c_flange non fourni, estimation pour profilé I/H
        if self.__section_type == "I" and self.__c_flange == 0.0:
            if self.__b > 0.0 and self.__tw > 0.0:
                self.__c_flange = (self.__b - self.__tw) / 2.0

        # Si d non fourni, estimation pour profilé I/H
        if self.__section_type == "I" and self.__d == 0.0:
            if self.__h > 0.0 and self.__tf > 0.0:
                self.__d = self.__h - 2.0 * self.__tf

    # -----------------------------------------------------------------------
    # Epsilon
    # -----------------------------------------------------------------------

    @property
    def epsilon(self) -> float:
        """ε = √(235 / fy)  — EC3-1-1 Tableau 5.2 note."""
        if self.__fy <= 0:
            return 1.0
        return math.sqrt(235.0 / self.__fy)

    def get_epsilon(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour ε."""
        r = self.epsilon
        fv = ""
        if with_values:
            fv = f"ε = √(235 / {self.__fy:.1f}) = {r:.4f}"
        return FormulaResult(
            name="ε",
            formula="ε = √(235 / fy)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — Tableau 5.2",
        )

    # -----------------------------------------------------------------------
    # Alpha & Psi (flexion + compression)
    # -----------------------------------------------------------------------

    @property
    def alpha(self) -> float:
        """
        Paramètre α pour l'âme en flexion + compression.

        α = (Ned / (d · tw · fy) + 1) / 2  borné à [0, 1].

        En flexion pure α = 0.5, en compression pure α = 1.0.
        """
        if self.__load_case == "compression":
            return 1.0
        if self.__load_case == "flexion":
            return 0.5

        # flexion_compression
        if self.__d <= 0 or self.__tw <= 0 or self.__fy <= 0:
            return 0.5
        # Capacité plastique de l'âme en compression
        npl_web = self.__d * self.__tw * self.__fy
        if npl_web == 0:
            return 0.5
        alpha_val = (self.__ned / npl_web + 1.0) / 2.0
        return max(0.0, min(alpha_val, 1.0))

    @property
    def psi(self) -> float:
        """
        Rapport de contraintes ψ pour l'âme en flexion + compression.

        ψ = (2α - 1)  : varie de -1 (flexion pure) à +1 (compression pure).

        En flexion pure ψ = -1 (σ2 = -σ1).
        En compression pure ψ = +1.
        """
        if self.__load_case == "compression":
            return 1.0
        if self.__load_case == "flexion":
            return -1.0
        # flexion_compression : déduit de alpha
        return 2.0 * self.alpha - 1.0

    # -----------------------------------------------------------------------
    # Semelle — classification
    # -----------------------------------------------------------------------

    @property
    def flange_ratio(self) -> float:
        """Rapport c/tf de la semelle (ou c/t pour RHS, d/t pour CHS)."""
        if self.__section_type == "CHS":
            if self.__t_chs <= 0:
                return 0.0
            return self.__D / self.__t_chs

        if self.__section_type == "RHS":
            # Pour RHS, semelle = paroi horizontale, c = b - 3t (approx.)
            # On utilise c_flange si disponible, sinon b - 2*tf (simplifié)
            t = self.__tf if self.__tf > 0 else self.__t_chs
            if t <= 0:
                return 0.0
            c = self.__b - 2.0 * t if self.__b > 0 else 0.0
            return c / t

        # Profilé I/H — semelle en console
        if self.__tf <= 0:
            return 0.0
        return self.__c_flange / self.__tf

    @property
    def flange_limits(self) -> Dict[int, float]:
        """Limites c/t (ou d/t) de la semelle pour les classes 1, 2, 3."""
        eps = self.epsilon

        if self.__section_type == "CHS":
            # CHS : limites en d/t = k · ε²
            return {
                1: CHS_LIMITS[1] * eps ** 2,
                2: CHS_LIMITS[2] * eps ** 2,
                3: CHS_LIMITS[3] * eps ** 2,
            }

        if self.__section_type == "RHS":
            # RHS paroi en compression (semelle comprimée)
            if self.__load_case == "compression":
                return {k: v * eps for k, v in RHS_COMPRESSION_LIMITS.items()}
            else:
                return {k: v * eps for k, v in RHS_BENDING_LIMITS.items()}

        # I/H — semelle en console
        return {k: v * eps for k, v in FLANGE_OUTSTAND_LIMITS.items()}

    @property
    def flange_class(self) -> int:
        """Classe de la semelle (1, 2 ou 3)."""
        # CHS n'a pas de distinction semelle/âme → traité ici
        ratio = self.flange_ratio
        limits = self.flange_limits
        if ratio <= limits[1]:
            return 1
        if ratio <= limits[2]:
            return 2
        if ratio <= limits[3]:
            return 3
        # Dépassement classe 3 → avertissement
        warnings.warn(
            f"Le rapport c/t de la semelle ({ratio:.2f}) dépasse la "
            f"limite de classe 3 ({limits[3]:.2f}). "
            f"Classe 4 non implémentée — classe 3 retournée.",
            UserWarning,
            stacklevel=2,
        )
        return 3

    def get_flange_class(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour la classe de la semelle."""
        r = self.flange_class
        ratio = self.flange_ratio
        limits = self.flange_limits
        fv = ""
        if with_values:
            lbl = "d/t" if self.__section_type == "CHS" else "c/t"
            fv = (
                f"{lbl} = {ratio:.2f}  |  "
                f"Limites : Cl.1 ≤ {limits[1]:.2f}, "
                f"Cl.2 ≤ {limits[2]:.2f}, "
                f"Cl.3 ≤ {limits[3]:.2f}  →  Classe {r}"
            )
        return FormulaResult(
            name="Classe semelle",
            formula="c/tf ≤ limites Tableau 5.2",
            formula_values=fv,
            result=float(r),
            unit="-",
            ref="EC3-1-1 — Tableau 5.2",
        )

    # -----------------------------------------------------------------------
    # Âme — classification
    # -----------------------------------------------------------------------

    @property
    def web_ratio(self) -> float:
        """Rapport d/tw de l'âme (0 pour CHS)."""
        if self.__section_type == "CHS":
            return 0.0
        if self.__section_type == "RHS":
            # Paroi verticale = âme
            t = self.__tw if self.__tw > 0 else self.__tf
            if t <= 0:
                return 0.0
            d = self.__h - 2.0 * t if self.__h > 0 else self.__d
            return d / t

        # I/H
        if self.__tw <= 0:
            return 0.0
        return self.__d / self.__tw

    @property
    def web_limits(self) -> Dict[int, float]:
        """Limites d/tw de l'âme pour les classes 1, 2, 3."""
        eps = self.epsilon

        if self.__section_type == "CHS":
            return {1: 0.0, 2: 0.0, 3: 0.0}

        # --- Compression pure ---
        if self.__load_case == "compression":
            if self.__section_type == "RHS":
                return {k: v * eps for k, v in RHS_COMPRESSION_LIMITS.items()}
            return {k: v * eps for k, v in WEB_COMPRESSION_LIMITS.items()}

        # --- Flexion pure ---
        if self.__load_case == "flexion":
            if self.__section_type == "RHS":
                return {k: v * eps for k, v in RHS_BENDING_LIMITS.items()}
            return {k: v * eps for k, v in WEB_BENDING_LIMITS.items()}

        # --- Flexion + compression ---
        a = self.alpha
        p = self.psi

        if a > 0.5:
            denom_1 = 13.0 * a - 1.0
            if denom_1 <= 0:
                denom_1 = 1e-6
            lim_1 = 396.0 * eps / denom_1
            lim_2 = 456.0 * eps / denom_1
        else:
            if a <= 0:
                a = 1e-6
            lim_1 = 36.0 * eps / a
            lim_2 = 41.5 * eps / a

        # Classe 3 — formule commune
        if p > -1.0:
            denom_3 = 0.67 + 0.33 * p
            if denom_3 <= 0:
                denom_3 = 1e-6
            lim_3 = 42.0 * eps / denom_3
        else:
            lim_3 = 62.0 * eps * (1.0 - p) * math.sqrt(-p)

        return {1: lim_1, 2: lim_2, 3: lim_3}

    @property
    def web_class(self) -> int:
        """Classe de l'âme (1, 2 ou 3). Retourne 1 pour CHS."""
        if self.__section_type == "CHS":
            return 1

        ratio = self.web_ratio
        limits = self.web_limits
        if ratio <= limits[1]:
            return 1
        if ratio <= limits[2]:
            return 2
        if ratio <= limits[3]:
            return 3
        warnings.warn(
            f"Le rapport d/tw de l'âme ({ratio:.2f}) dépasse la "
            f"limite de classe 3 ({limits[3]:.2f}). "
            f"Classe 4 non implémentée — classe 3 retournée.",
            UserWarning,
            stacklevel=2,
        )
        return 3

    def get_web_class(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour la classe de l'âme."""
        r = self.web_class
        ratio = self.web_ratio
        limits = self.web_limits
        fv = ""
        if with_values:
            if self.__section_type == "CHS":
                fv = "CHS — pas de classification d'âme distincte → Classe 1"
            else:
                fv = (
                    f"d/tw = {ratio:.2f}  |  "
                    f"Limites : Cl.1 ≤ {limits[1]:.2f}, "
                    f"Cl.2 ≤ {limits[2]:.2f}, "
                    f"Cl.3 ≤ {limits[3]:.2f}  →  Classe {r}"
                )
        return FormulaResult(
            name="Classe âme",
            formula="d/tw ≤ limites Tableau 5.2",
            formula_values=fv,
            result=float(r),
            unit="-",
            ref="EC3-1-1 — Tableau 5.2",
        )

    # -----------------------------------------------------------------------
    # Classification globale de la section
    # -----------------------------------------------------------------------

    @property
    def section_class(self) -> int:
        """Classe de la section = max(classe semelle, classe âme)."""
        return max(self.flange_class, self.web_class)

    @property
    def is_class_1(self) -> bool:
        """True si la section est de classe 1."""
        return self.section_class == 1

    @property
    def is_class_2(self) -> bool:
        """True si la section est de classe 2."""
        return self.section_class == 2

    @property
    def is_class_3(self) -> bool:
        """True si la section est de classe 3."""
        return self.section_class == 3

    def get_section_class(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour la classe globale de la section."""
        r = self.section_class
        fv = ""
        if with_values:
            fv = (
                f"Classe section = max(Classe semelle={self.flange_class}, "
                f"Classe âme={self.web_class}) = Classe {r}"
            )
        return FormulaResult(
            name="Classe section",
            formula="Classe = max(Classe_semelle, Classe_âme)",
            formula_values=fv,
            result=float(r),
            unit="-",
            ref="EC3-1-1 — §5.5.2",
        )

    # -----------------------------------------------------------------------
    # Rapport
    # -----------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un ``FormulaCollection`` regroupant toutes les étapes
        de la classification.
        """
        fc = FormulaCollection(
            title=f"Classification de section — {self.__load_case}",
            ref="EC3-1-1 — §5.5 / Tableau 5.2",
        )
        fc.add(self.get_epsilon(with_values=with_values))
        fc.add(self.get_flange_class(with_values=with_values))
        if self.__section_type != "CHS":
            fc.add(self.get_web_class(with_values=with_values))
        fc.add(self.get_section_class(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"Classification(type={self.__section_type}, "
            f"load={self.__load_case}, "
            f"Classe {self.section_class})"
        )


# =======================================================================
# Fonctions utilitaires
# =======================================================================

def classify(load_case: str, fy: float = 235.0,
             section_type: str = "I", **kwargs) -> int:
    """
    Classification rapide sans instancier explicitement la classe.

    Returns
    -------
    int
        Classe de la section (1, 2 ou 3).
    """
    c = Classification(load_case=load_case, fy=fy,
                       section_type=section_type, **kwargs)
    return c.section_class


# =======================================================================
# Debug / démonstration
# =======================================================================

if __name__ == "__main__":

    # --- IPE 300, S235 ---
    # Dimensions IPE 300 : h=300, b=150, tw=7.1, tf=10.7, d=248.6
    ipe300 = dict(
        h=300.0, b=150.0, tw=7.1, tf=10.7,
        d=248.6, c_flange=(150.0 - 7.1) / 2.0,
        section_type="I", fy=235.0, A=5381.0,
    )

    print("=" * 60)
    print("IPE 300 — FLEXION PURE")
    print("=" * 60)
    clf_flex = Classification(load_case="flexion", **ipe300)
    print(clf_flex)
    print(clf_flex.report())

    print()
    print("=" * 60)
    print("IPE 300 — COMPRESSION PURE")
    print("=" * 60)
    clf_comp = Classification(load_case="compression", **ipe300)
    print(clf_comp)
    print(clf_comp.report())

    print()
    print("=" * 60)
    print("IPE 300 — FLEXION + COMPRESSION (Ned=200kN)")
    print("=" * 60)
    clf_fc = Classification(
        load_case="flexion_compression",
        Ned=200_000.0,
        Med=50_000_000.0,
        **ipe300,
    )
    print(clf_fc)
    print(f"  α = {clf_fc.alpha:.4f}")
    print(f"  ψ = {clf_fc.psi:.4f}")
    print(clf_fc.report())


# TODO — Implémentation future :
# - Classe 4 et renvoi vers effective_properties.py
# - Profilés en L (cornières)
# - Profilés en U
# - Profilés en T
# - Sections composées soudées (dimensions arbitraires)
# - Classification sous effort biaxial (N + My + Mz)
# - Prise en compte des contraintes résiduelles
# - Tableau 5.2 complet : parois internes (internal part) pour semelles de caissons
