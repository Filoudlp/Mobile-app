# vibration.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification des vibrations (fréquence propre) selon l'EC3-1-1 — §7.2.

Deux modes :
  • ``analytical`` — formule exacte f₁ = C/(2π·L²) · √(E·I / m)
  • ``simplified`` — formule simplifiée f₁ ≈ 18 / √δ_max

Conditions d'appui : ``simply_supported``, ``cantilever``,
``fixed_fixed``, ``fixed_pinned``.
"""

__all__ = ["Vibration", "natural_frequency"]

from typing import TypeVar, Optional
import math

from core.formula import FormulaResult, FormulaCollection

section = TypeVar("section")
material = TypeVar("material")

# ---------------------------------------------------------------------------
# Constante C selon les conditions d'appui
# f₁ = C / (2·π·L²) · √(E·I / m)
# ---------------------------------------------------------------------------

_C_SUPPORT: dict[str, float] = {
    "simply_supported": math.pi ** 2,          # π²   ≈  9.8696
    "cantilever":       3.516,
    "fixed_fixed":      4.0 * math.pi ** 2,    # 4π²  ≈ 39.478
    "fixed_pinned":     15.418,
}

_FORMULA_C: dict[str, str] = {
    "simply_supported": "π²",
    "cantilever":       "3.516",
    "fixed_fixed":      "4·π²",
    "fixed_pinned":     "15.418",
}

# ---------------------------------------------------------------------------
# Limites de fréquence selon l'usage
# ---------------------------------------------------------------------------

FREQUENCY_LIMITS: dict[str, float] = {
    "floor":       3.0,   # Plancher de bâtiment  [Hz]
    "footbridge":  5.0,   # Passerelle piétonne   [Hz]
    "gymnasium":   8.0,   # Salle de sport        [Hz]
}


class Vibration:
    """
    Vérification de la fréquence propre d'un élément de structure.

    Paramètres
    ----------
    mode : str
        ``"analytical"`` (défaut) ou ``"simplified"``.
    support : str
        Condition d'appui (voir ``_C_SUPPORT``).
    L : float
        Portée [mm].
    m : float
        Masse linéique [kg/mm].
    mat : material, optional
        Objet matériau (propriété ``E`` en MPa).
    sec : section, optional
        Objet section (propriété ``Iy`` en mm⁴).
    delta_max : float, optional
        Flèche maximale [mm] pour le mode ``simplified``.
    usage : str
        Clé dans ``FREQUENCY_LIMITS`` (``"floor"``, ``"footbridge"``, ``"gymnasium"``).
    f_limit : float, optional
        Fréquence limite fournie directement [Hz].
    E : float
        Module d'Young [MPa] (si ``mat`` non fourni).
    I : float
        Inertie [mm⁴] (si ``sec`` non fourni).
    """

    _VALID_MODES = {"analytical", "simplified"}
    _VALID_SUPPORTS = {"simply_supported", "cantilever", "fixed_fixed", "fixed_pinned"}

    def __init__(
        self,
        mode: str = "analytical",
        support: str = "simply_supported",
        L: float = 0.0,
        m: float = 0.0,
        mat: Optional[material] = None,
        sec: Optional[section] = None,
        *,
        delta_max: float = 0.0,
        usage: str = "floor",
        f_limit: Optional[float] = None,
        **kwargs,
    ) -> None:

        if mode not in self._VALID_MODES:
            raise ValueError(f"mode doit être parmi {self._VALID_MODES}")
        if support not in self._VALID_SUPPORTS:
            raise ValueError(f"support doit être parmi {self._VALID_SUPPORTS}")

        self.__mode = mode
        self.__support = support
        self.__L: float = float(L)
        self.__m: float = float(m)
        self.__delta_max: float = float(delta_max)
        self.__usage: str = usage
        self.__f_limit_input: Optional[float] = f_limit

        # --- Matériau ---
        self.__E: float = mat.E if mat else kwargs.get("E", 0.0)

        # --- Section ---
        self.__I: float = sec.Iy if sec else kwargs.get("I", 0.0)

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def f1(self) -> float:
        """Fréquence propre fondamentale f₁ [Hz]."""
        if self.__mode == "simplified":
            return self._f1_simplified()
        return self._f1_analytical()

    @property
    def f_limit(self) -> float:
        """Fréquence limite [Hz]."""
        if self.__f_limit_input is not None:
            return self.__f_limit_input
        if self.__usage not in FREQUENCY_LIMITS:
            raise KeyError(
                f"usage '{self.__usage}' inconnu. "
                f"Clés disponibles : {list(FREQUENCY_LIMITS.keys())}"
            )
        return FREQUENCY_LIMITS[self.__usage]

    @property
    def verif(self) -> float:
        """Taux f_limit / f₁ (≤ 1.0 si OK)."""
        if self.f1 == 0:
            return float("inf")
        return round(self.f_limit / self.f1, 4)

    @property
    def is_ok(self) -> bool:
        """True si f₁ ≥ f_limit."""
        return self.f1 >= self.f_limit

    # -----------------------------------------------------------------------
    # Calculs internes
    # -----------------------------------------------------------------------

    def _f1_analytical(self) -> float:
        """f₁ = C / (2·π·L²) · √(E·I / m)  [Hz].

        Note : E en MPa = N/mm², I en mm⁴, m en kg/mm, L en mm.
        E·I / m donne N·mm³ / kg = (kg·mm/s²)·mm³ / (kg·mm) = mm²/s²·mm² … 
        En fait f = C/(2πL²) √(EI/m) avec E [N/mm²], I [mm⁴], m [kg/mm], L [mm]
        EI/m → N·mm² / (kg/mm)·mm = N·mm³/kg
        N = kg·m/s² = kg·1000mm/s²  →  EI/m → 1000 mm⁴/s²
        On doit convertir : EI (N·mm²) * 1e-3 (m/mm) → kg·mm³/s² … 
        
        Approche propre : convertir en SI puis revenir en Hz.
        """
        C = _C_SUPPORT[self.__support]
        # Conversion en SI : E [Pa], I [m⁴], m [kg/m], L [m]
        E_si = self.__E * 1e6          # MPa → Pa (N/m²)
        I_si = self.__I * 1e-12        # mm⁴ → m⁴
        m_si = self.__m * 1e3          # kg/mm → kg/m
        L_si = self.__L * 1e-3         # mm → m

        if m_si == 0 or L_si == 0:
            return 0.0

        return C / (2.0 * math.pi * L_si ** 2) * math.sqrt(E_si * I_si / m_si)

    def _f1_simplified(self) -> float:
        """f₁ ≈ 18 / √δ_max  [Hz], δ_max en mm."""
        if self.__delta_max <= 0:
            return 0.0
        return 18.0 / math.sqrt(self.__delta_max)

    # -----------------------------------------------------------------------
    # FormulaResult builders
    # -----------------------------------------------------------------------

    def get_f1(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la fréquence propre f₁."""
        r = self.f1
        if self.__mode == "simplified":
            formula = "f₁ ≈ 18 / √δ_max"
            fv = ""
            if with_values:
                fv = (
                    f"f₁ = 18 / √{self.__delta_max:.2f} "
                    f"= {r:.3f} Hz"
                )
        else:
            C_str = _FORMULA_C[self.__support]
            formula = f"f₁ = {C_str} / (2·π·L²) · √(E·I / m)"
            C = _C_SUPPORT[self.__support]
            fv = ""
            if with_values:
                fv = (
                    f"f₁ = {C:.4f} / (2·π·{self.__L:.1f}²) "
                    f"· √({self.__E:.1f}·{self.__I:.1f} / {self.__m:.6f}) "
                    f"= {r:.3f} Hz  "
                    f"[unités converties en SI pour le calcul]"
                )
        return FormulaResult(
            name="f₁",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="Hz",
            ref="EC3-1-1 — §7.2",
        )

    def get_f_limit(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la fréquence limite."""
        r = self.f_limit
        if self.__f_limit_input is not None:
            formula = "f_lim (fournie par l'utilisateur)"
            fv = f"f_lim = {r:.2f} Hz" if with_values else ""
        else:
            formula = f"f_lim = {r:.1f} Hz  (usage : {self.__usage})"
            fv = f"f_lim = {r:.2f} Hz" if with_values else ""
        return FormulaResult(
            name="f_lim",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="Hz",
            ref="EC3-1-1 — §7.2",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification f₁ ≥ f_lim."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"f_lim / f₁ = {self.f_limit:.3f} / {self.f1:.3f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="f_lim/f₁",
            formula="f_lim / f₁ ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §7.2",
            is_check=True,
            status=self.is_ok,
        )

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection regroupant toutes les étapes."""
        fc = FormulaCollection(
            title="Vérification des vibrations",
            ref="EC3-1-1 — §7.2",
        )
        fc.add(self.get_f1(with_values=with_values))
        fc.add(self.get_f_limit(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"Vibration(f₁={self.f1:.3f} Hz, f_lim={self.f_limit:.2f} Hz, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ---------------------------------------------------------------------------
# Fonction standalone
# ---------------------------------------------------------------------------

def natural_frequency(
    L: float,
    E: float,
    I: float,
    m: float,
    support: str = "simply_supported",
) -> float:
    """
    Calcul rapide de la fréquence propre f₁ sans instancier la classe.

    :param L:       Portée [mm].
    :param E:       Module d'Young [MPa].
    :param I:       Inertie [mm⁴].
    :param m:       Masse linéique [kg/mm].
    :param support: Condition d'appui.
    :return:        f₁ [Hz].
    """
    v = Vibration(
        mode="analytical",
        support=support,
        L=L,
        m=m,
        E=E,
        I=I,
    )
    return v.f1


# ---------------------------------------------------------------------------
# Debug / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # IPE 300, S235, L = 8 000 mm, m = 0.05 kg/mm, bi-articulé, usage plancher
    # Iy(IPE300) ≈ 83 560 000 mm⁴,  E = 210 000 MPa
    L = 8000.0
    E = 210000.0
    I = 83560000.0
    m = 0.05  # kg/mm

    v = Vibration(
        mode="analytical",
        support="simply_supported",
        L=L,
        m=m,
        usage="floor",
        E=E,
        I=I,
    )

    print(v)
    rpt = v.report(with_values=True)
    for fr in rpt:
        print(f"  {fr.name}: {fr.formula_values}")

    # Test standalone
    f = natural_frequency(L, E, I, m)
    print(f"\nStandalone : f₁ = {f:.3f} Hz")

    # Test simplifié
    v2 = Vibration(mode="simplified", delta_max=10.0, usage="floor")
    print(f"\nSimplifié : {v2}")
