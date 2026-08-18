#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Imperfections globales et locales selon l'EC3-1-1 §5.3.

- ``GlobalImperfection`` : défaut d'aplomb (imperfection de structure).
- ``LocalImperfection``  : défaut de rectitude (bow imperfection de barre).
"""

__all__ = ['GlobalImperfection', 'LocalImperfection']

import math
from typing import Optional, Dict

from core.formula import FormulaResult, FormulaCollection

# Tentative d'import du NationalAnnex (optionnel)
try:
    from core.national_annex import NationalAnnex
except ImportError:  # pragma: no cover
    NationalAnnex = None  # type: ignore[misc,assignment]


# ---------------------------------------------------------------------------
# Constantes — Tableau 5.1 (EC3-1-1) : e₀/L
# ---------------------------------------------------------------------------

#: Ratios e₀/L par courbe de flambement et méthode d'analyse.
#: Clé primaire : courbe ("a0", "a", "b", "c", "d").
#: Clé secondaire : méthode ("elastic", "plastic").
BOW_IMPERFECTION_TABLE: Dict[str, Dict[str, float]] = {
    "a0": {"elastic": 1.0 / 350.0, "plastic": 1.0 / 300.0},
    "a":  {"elastic": 1.0 / 300.0, "plastic": 1.0 / 250.0},
    "b":  {"elastic": 1.0 / 250.0, "plastic": 1.0 / 200.0},
    "c":  {"elastic": 1.0 / 200.0, "plastic": 1.0 / 150.0},
    "d":  {"elastic": 1.0 / 150.0, "plastic": 1.0 / 100.0},
}

#: Valeur recommandée de φ₀ (EC3-1-1 §5.3.2(3))
PHI_0_DEFAULT: float = 1.0 / 200.0


# ===================================================================
# Imperfection globale
# ===================================================================

class GlobalImperfection:
    """
    Imperfection globale de structure (défaut d'aplomb) — EC3-1-1 §5.3.2(3).

    L'imperfection globale φ est donnée par :

        φ = φ₀ · αh · αm

    avec :
        - φ₀ = 1/200 (valeur recommandée, ajustable par l'Annexe Nationale)
        - αh = 2/√h  borné à  2/3 ≤ αh ≤ 1.0  (h en mètres)
        - αm = √(0.5 · (1 + 1/m))

    Parameters
    ----------
    h : float
        Hauteur du poteau **en millimètres**.
    m : int
        Nombre de poteaux dans la rangée considérée.
    na : NationalAnnex, optional
        Annexe nationale pour récupérer ``phi_0``.
    phi_0 : float, optional
        Valeur manuelle de φ₀. Prioritaire sur ``na``.
    """

    def __init__(self,
                 h: float,
                 m: int = 1,
                 na: Optional['NationalAnnex'] = None,
                 phi_0: Optional[float] = None) -> None:

        self.__h_mm: float = abs(h)
        self.__h_m: float = self.__h_mm / 1000.0
        self.__m: int = max(m, 1)

        # Détermination de φ₀
        if phi_0 is not None:
            self.__phi_0: float = phi_0
        elif na is not None:
            self.__phi_0 = na.get("EC3", "alpha_imp", PHI_0_DEFAULT)
        else:
            self.__phi_0 = PHI_0_DEFAULT

    # -------------------------------------------------------------------
    # φ₀
    # -------------------------------------------------------------------

    @property
    def phi_0(self) -> float:
        """Valeur de base φ₀ de l'imperfection globale."""
        return self.__phi_0

    # -------------------------------------------------------------------
    # αh
    # -------------------------------------------------------------------

    @property
    def alpha_h(self) -> float:
        """
        Coefficient de réduction lié à la hauteur.

        αh = 2 / √h   avec  2/3 ≤ αh ≤ 1.0  (h en mètres).
        """
        if self.__h_m <= 0:
            return 1.0
        val = 2.0 / math.sqrt(self.__h_m)
        return max(2.0 / 3.0, min(val, 1.0))

    def get_alpha_h(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour αh."""
        r = self.alpha_h
        fv = ""
        if with_values:
            raw = 2.0 / math.sqrt(self.__h_m) if self.__h_m > 0 else 1.0
            fv = (
                f"αh = 2 / √({self.__h_m:.3f}) = {raw:.4f}  →  "
                f"borné à [2/3 ; 1.0] = {r:.4f}"
            )
        return FormulaResult(
            name="αh",
            formula="αh = 2/√h   (2/3 ≤ αh ≤ 1.0, h en m)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §5.3.2(3)",
        )

    # -------------------------------------------------------------------
    # αm
    # -------------------------------------------------------------------

    @property
    def alpha_m(self) -> float:
        """
        Coefficient de réduction lié au nombre de poteaux.

        αm = √(0.5 · (1 + 1/m))
        """
        return math.sqrt(0.5 * (1.0 + 1.0 / self.__m))

    def get_alpha_m(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour αm."""
        r = self.alpha_m
        fv = ""
        if with_values:
            fv = (
                f"αm = √(0.5 × (1 + 1/{self.__m})) = "
                f"√(0.5 × {1.0 + 1.0 / self.__m:.4f}) = {r:.4f}"
            )
        return FormulaResult(
            name="αm",
            formula="αm = √(0.5 · (1 + 1/m))",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §5.3.2(3)",
        )

    # -------------------------------------------------------------------
    # φ
    # -------------------------------------------------------------------

    @property
    def phi(self) -> float:
        """
        Imperfection globale finale.

        φ = φ₀ · αh · αm
        """
        return self.__phi_0 * self.alpha_h * self.alpha_m

    def get_phi(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour φ."""
        r = self.phi
        fv = ""
        if with_values:
            fv = (
                f"φ = {self.__phi_0:.6f} × {self.alpha_h:.4f} × "
                f"{self.alpha_m:.4f} = {r:.6f}  "
                f"(≈ 1/{1.0 / r:.0f})" if r > 0 else "φ = 0"
            )
        return FormulaResult(
            name="φ",
            formula="φ = φ₀ · αh · αm",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §5.3.2(3)",
        )

    # -------------------------------------------------------------------
    # Rapport
    # -------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        ``FormulaCollection`` regroupant le calcul complet de l'imperfection
        globale.
        """
        fc = FormulaCollection(
            title="Imperfection globale de structure (défaut d'aplomb)",
            ref="EC3-1-1 — §5.3.2(3)",
        )
        fc.add(self.get_alpha_h(with_values=with_values))
        fc.add(self.get_alpha_m(with_values=with_values))
        fc.add(self.get_phi(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"GlobalImperfection(h={self.__h_mm:.0f} mm, m={self.__m}, "
            f"φ={self.phi:.6f} ≈ 1/{1.0 / self.phi:.0f})"
            if self.phi > 0
            else f"GlobalImperfection(h={self.__h_mm:.0f} mm, m={self.__m}, φ=0)"
        )


# ===================================================================
# Imperfection locale
# ===================================================================

class LocalImperfection:
    """
    Imperfection locale de barre (défaut de rectitude) — EC3-1-1 §5.3.2(3),
    Tableau 5.1.

    L'amplitude de l'imperfection initiale est :

        e₀ = L × (e₀/L)

    où le ratio e₀/L est lu dans le Tableau 5.1 en fonction de la courbe
    de flambement et de la méthode d'analyse (élastique ou plastique).

    Parameters
    ----------
    L : float
        Longueur de la barre [mm].
    buckling_curve : str
        Courbe de flambement : ``"a0"``, ``"a"``, ``"b"``, ``"c"`` ou ``"d"``.
    method : str
        Méthode d'analyse : ``"elastic"`` ou ``"plastic"``.
    """

    _VALID_CURVES = ("a0", "a", "b", "c", "d")
    _VALID_METHODS = ("elastic", "plastic")

    def __init__(self,
                 L: float,
                 buckling_curve: str = "a",
                 method: str = "elastic") -> None:

        if buckling_curve not in self._VALID_CURVES:
            raise ValueError(
                f"buckling_curve doit être parmi {self._VALID_CURVES}, "
                f"reçu : '{buckling_curve}'"
            )
        if method not in self._VALID_METHODS:
            raise ValueError(
                f"method doit être parmi {self._VALID_METHODS}, "
                f"reçu : '{method}'"
            )

        self.__L: float = abs(L)
        self.__curve: str = buckling_curve
        self.__method: str = method

    # -------------------------------------------------------------------
    # e₀/L
    # -------------------------------------------------------------------

    @property
    def e0_ratio(self) -> float:
        """Ratio e₀/L depuis le Tableau 5.1."""
        return BOW_IMPERFECTION_TABLE[self.__curve][self.__method]

    # -------------------------------------------------------------------
    # e₀
    # -------------------------------------------------------------------

    @property
    def e0(self) -> float:
        """Amplitude de l'imperfection locale [mm] : e₀ = L × (e₀/L)."""
        return self.__L * self.e0_ratio

    def get_e0(self, with_values: bool = False) -> FormulaResult:
        """``FormulaResult`` pour e₀."""
        r = self.e0
        ratio = self.e0_ratio
        # Dénominateur arrondi pour affichage lisible
        denom = round(1.0 / ratio) if ratio > 0 else 0
        fv = ""
        if with_values:
            fv = (
                f"e₀/L = 1/{denom}  (courbe '{self.__curve}', "
                f"méthode {self.__method})  →  "
                f"e₀ = {self.__L:.1f} / {denom} = {r:.2f} mm"
            )
        return FormulaResult(
            name="e₀",
            formula="e₀ = L × (e₀/L)  — Tableau 5.1",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC3-1-1 — §5.3.2(3) Tableau 5.1",
        )

    # -------------------------------------------------------------------
    # Rapport
    # -------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        ``FormulaCollection`` regroupant le calcul de l'imperfection locale.
        """
        fc = FormulaCollection(
            title="Imperfection locale de barre (défaut de rectitude)",
            ref="EC3-1-1 — §5.3.2(3) — Tableau 5.1",
        )
        fc.add(self.get_e0(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        denom = round(1.0 / self.e0_ratio) if self.e0_ratio > 0 else 0
        return (
            f"LocalImperfection(L={self.__L:.0f} mm, "
            f"courbe='{self.__curve}', méthode='{self.__method}', "
            f"e₀/L=1/{denom}, e₀={self.e0:.2f} mm)"
        )


# ===================================================================
# Debug / démonstration
# ===================================================================

if __name__ == "__main__":

    print("=" * 60)
    print("IMPERFECTION GLOBALE — h = 6 m, m = 3 poteaux")
    print("=" * 60)
    gi = GlobalImperfection(h=6000.0, m=3)
    print(gi)
    print(f"  φ₀   = {gi.phi_0:.6f}")
    print(f"  αh   = {gi.alpha_h:.4f}")
    print(f"  αm   = {gi.alpha_m:.4f}")
    print(f"  φ    = {gi.phi:.6f}")
    print()
    print(gi.report())

    print()
    print("=" * 60)
    print("IMPERFECTION LOCALE — L = 5 m, courbe b, élastique")
    print("=" * 60)
    li = LocalImperfection(L=5000.0, buckling_curve="b", method="elastic")
    print(li)
    print(f"  e₀/L = {li.e0_ratio:.6f}")
    print(f"  e₀   = {li.e0:.2f} mm")
    print()
    print(li.report())


# TODO — Implémentation future :
# - Imperfections d'arc (bow imperfections) — Tableau 5.1 complet
# - Imperfections pour les treillis §5.3.3
# - Forces équivalentes aux imperfections §5.3.2(7) — forces horizontales fictives
# - Imperfections pour structures en portique multi-étages
# - Combinaison imperfections globales + locales §5.3.2(6)
# - Imperfections pour le déversement §5.3.4
# - Prise en compte des imperfections de fabrication (tolérances EN 1090)
