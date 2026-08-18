# deflection.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification des flèches verticales selon l'EC3-1-1 — §7.2.

Trois modes de fonctionnement :
  • ``calculated``   – flèche fournie directement par l'utilisateur.
  • ``distributed``  – calcul analytique sous charge répartie q [N/mm].
  • ``point_load``   – calcul analytique sous charge ponctuelle F [N].

Conditions d'appui disponibles :
  ``simply_supported``, ``cantilever``, ``fixed_fixed``, ``fixed_pinned``.
"""

__all__ = ["Deflection", "deflection_check"]

from typing import TypeVar, Optional
import math

from core.formula import FormulaResult, FormulaCollection
from norme.EC3.els.limits import get_limit, VERTICAL_LIMITS

section = TypeVar("section")
material = TypeVar("material")

# ---------------------------------------------------------------------------
# Coefficients analytiques
# ---------------------------------------------------------------------------

# Charge répartie q :  δ = q·L⁴ / (K·E·I)
_K_DISTRIBUTED: dict[str, float] = {
    "simply_supported": 384.0 / 5.0,   # 76.8  →  5qL⁴/384EI
    "cantilever":       8.0,
    "fixed_fixed":      384.0,
    "fixed_pinned":     185.0,
}

# Charge ponctuelle F à mi-portée :  δ = F·L³ / (K·E·I)
_K_POINT: dict[str, float] = {
    "simply_supported": 48.0,
    "cantilever":       3.0,
    "fixed_fixed":      192.0,
    "fixed_pinned":     48.0 * math.sqrt(5),  # ≈ 107.33
}

# Formules littérales (pour affichage)
_FORMULA_DIST: dict[str, str] = {
    "simply_supported": "δ = 5·q·L⁴ / (384·E·I)",
    "cantilever":       "δ = q·L⁴ / (8·E·I)",
    "fixed_fixed":      "δ = q·L⁴ / (384·E·I)",
    "fixed_pinned":     "δ = q·L⁴ / (185·E·I)",
}

_FORMULA_POINT: dict[str, str] = {
    "simply_supported": "δ = F·L³ / (48·E·I)",
    "cantilever":       "δ = F·L³ / (3·E·I)",
    "fixed_fixed":      "δ = F·L³ / (192·E·I)",
    "fixed_pinned":     "δ = F·L³ / (48·√5·E·I)",
}


class Deflection:
    """
    Vérification de la flèche verticale d'un élément de structure.

    Paramètres
    ----------
    mode : str
        ``"calculated"`` | ``"distributed"`` | ``"point_load"``
    support : str
        ``"simply_supported"`` | ``"cantilever"`` | ``"fixed_fixed"`` | ``"fixed_pinned"``
    L : float
        Portée de l'élément [mm].
    mat : material, optional
        Objet matériau (propriétés ``E``).
    sec : section, optional
        Objet section (propriété ``Iy``).
    delta : float, optional
        Flèche calculée fournie directement [mm]  (mode ``calculated``).
    q : float, optional
        Charge répartie [N/mm]  (mode ``distributed``).
    F : float, optional
        Charge ponctuelle [N]  (mode ``point_load``).
    delta_0 : float
        Contre-flèche [mm] (défaut 0).
    limit_type : str, optional
        Clé dans ``VERTICAL_LIMITS`` pour la limite automatique.
    limit_ratio : float, optional
        Ratio personnalisé (ex. 250 → L/250).
    delta_limit : float, optional
        Flèche limite fournie directement [mm].
    E : float
        Module d'Young [MPa] (si ``mat`` non fourni).
    I : float
        Inertie [mm⁴] (si ``sec`` non fourni).
    """

    _VALID_MODES = {"calculated", "distributed", "point_load"}
    _VALID_SUPPORTS = {"simply_supported", "cantilever", "fixed_fixed", "fixed_pinned"}

    def __init__(
        self,
        mode: str = "calculated",
        support: str = "simply_supported",
        L: float = 0.0,
        mat: Optional[material] = None,
        sec: Optional[section] = None,
        *,
        delta: float = 0.0,
        q: float = 0.0,
        F: float = 0.0,
        delta_0: float = 0.0,
        limit_type: str = "floor_general",
        limit_ratio: Optional[float] = None,
        delta_limit: Optional[float] = None,
        **kwargs,
    ) -> None:

        # --- validation ---
        if mode not in self._VALID_MODES:
            raise ValueError(f"mode doit être parmi {self._VALID_MODES}")
        if support not in self._VALID_SUPPORTS:
            raise ValueError(f"support doit être parmi {self._VALID_SUPPORTS}")

        self.__mode = mode
        self.__support = support
        self.__L = float(L)

        # --- Matériau ---
        self.__E: float = mat.E if mat else kwargs.get("E", 0.0)

        # --- Section ---
        self.__I: float = sec.Iy if sec else kwargs.get("I", 0.0)

        # --- Charges / flèche ---
        self.__delta_input: float = float(delta)
        self.__q: float = float(q)
        self.__F: float = float(F)
        self.__delta_0: float = float(delta_0)

        # --- Limite ---
        self.__limit_type = limit_type
        self.__limit_ratio = limit_ratio
        self.__delta_limit_input = delta_limit

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def delta(self) -> float:
        """Flèche brute calculée [mm]."""
        if self.__mode == "calculated":
            return self.__delta_input
        if self.__mode == "distributed":
            return self._delta_distributed()
        return self._delta_point_load()

    @property
    def delta_0(self) -> float:
        """Contre-flèche [mm]."""
        return self.__delta_0

    @property
    def delta_net(self) -> float:
        """Flèche nette = δ − δ₀ [mm]."""
        return max(self.delta - self.__delta_0, 0.0)

    @property
    def delta_limit(self) -> float:
        """Flèche limite [mm]."""
        if self.__delta_limit_input is not None:
            return self.__delta_limit_input
        return get_limit(
            self.__L,
            element_type=self.__limit_type,
            custom_ratio=self.__limit_ratio,
        )

    @property
    def verif(self) -> float:
        """Taux δ_net / δ_limit."""
        if self.delta_limit == 0:
            return float("inf")
        return round(self.delta_net / self.delta_limit, 4)

    @property
    def is_ok(self) -> bool:
        """True si δ_net ≤ δ_limit."""
        return self.verif <= 1.0

    # -----------------------------------------------------------------------
    # Calculs internes
    # -----------------------------------------------------------------------

    def _delta_distributed(self) -> float:
        """δ sous charge répartie q [N/mm]."""
        EI = self.__E * self.__I
        if EI == 0:
            return 0.0
        K = _K_DISTRIBUTED[self.__support]
        return self.__q * self.__L ** 4 / (K * EI)

    def _delta_point_load(self) -> float:
        """δ sous charge ponctuelle F [N] à mi-portée."""
        EI = self.__E * self.__I
        if EI == 0:
            return 0.0
        K = _K_POINT[self.__support]
        return self.__F * self.__L ** 3 / (K * EI)

    # -----------------------------------------------------------------------
    # FormulaResult builders
    # -----------------------------------------------------------------------

    def get_delta(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la flèche brute δ."""
        r = self.delta
        if self.__mode == "calculated":
            formula = "δ (fournie par l'utilisateur)"
            fv = f"δ = {r:.2f} mm" if with_values else ""
        elif self.__mode == "distributed":
            formula = _FORMULA_DIST[self.__support]
            K = _K_DISTRIBUTED[self.__support]
            fv = ""
            if with_values:
                fv = (
                    f"δ = {self.__q:.4f} × {self.__L:.1f}⁴ / "
                    f"({K:.1f} × {self.__E:.1f} × {self.__I:.1f}) = {r:.2f} mm"
                )
        else:  # point_load
            formula = _FORMULA_POINT[self.__support]
            K = _K_POINT[self.__support]
            fv = ""
            if with_values:
                fv = (
                    f"δ = {self.__F:.2f} × {self.__L:.1f}³ / "
                    f"({K:.2f} × {self.__E:.1f} × {self.__I:.1f}) = {r:.2f} mm"
                )
        return FormulaResult(
            name="δ",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC3-1-1 — §7.2",
        )

    def get_delta_net(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la flèche nette δ_net = δ − δ₀."""
        r = self.delta_net
        fv = ""
        if with_values:
            fv = (
                f"δ_net = {self.delta:.2f} − {self.__delta_0:.2f} "
                f"= {r:.2f} mm"
            )
        return FormulaResult(
            name="δ_net",
            formula="δ_net = δ − δ₀",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC3-1-1 — §7.2",
        )

    def get_delta_limit(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la flèche limite."""
        r = self.delta_limit
        # Déterminer le ratio utilisé pour l'affichage
        if self.__delta_limit_input is not None:
            formula = "δ_lim (fournie par l'utilisateur)"
            fv = f"δ_lim = {r:.2f} mm" if with_values else ""
        else:
            ratio = self.__limit_ratio or VERTICAL_LIMITS.get(self.__limit_type, 250)
            formula = f"δ_lim = L / {ratio:.0f}"
            fv = ""
            if with_values:
                fv = f"δ_lim = {self.__L:.1f} / {ratio:.0f} = {r:.2f} mm"
        return FormulaResult(
            name="δ_lim",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC3-1-1 — §7.2, Tableau 7.1",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification δ_net / δ_lim ≤ 1.0."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"δ_net / δ_lim = {self.delta_net:.2f} / {self.delta_limit:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="δ_net/δ_lim",
            formula="δ_net / δ_lim ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC3-1-1 — §7.2",
            is_check=True,
            limit=1.0,
        )

    # -----------------------------------------------------------------------
    # Report
    # -----------------------------------------------------------------------

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Génère un FormulaCollection regroupant toutes les étapes."""
        fc = FormulaCollection(
            title="Vérification de la flèche verticale",
            ref="EC3-1-1 — §7.2",
        )
        fc.add(self.get_delta(with_values=with_values))
        fc.add(self.get_delta_net(with_values=with_values))
        fc.add(self.get_delta_limit(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"Deflection(δ={self.delta:.2f}, δ_net={self.delta_net:.2f}, "
            f"δ_lim={self.delta_limit:.2f}, taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ---------------------------------------------------------------------------
# Fonction standalone
# ---------------------------------------------------------------------------

def deflection_check(
    delta: float,
    span: float,
    limit_ratio: float = 250.0,
    delta_0: float = 0.0,
) -> float:
    """
    Vérification rapide de flèche sans instancier la classe.

    :param delta:       Flèche calculée [mm].
    :param span:        Portée [mm].
    :param limit_ratio: Ratio de limite (250 → L/250).
    :param delta_0:     Contre-flèche [mm].
    :return:            Taux δ_net / δ_lim.
    """
    delta_net = max(delta - delta_0, 0.0)
    delta_lim = span / limit_ratio if limit_ratio != 0 else 0.0
    if delta_lim == 0:
        return float("inf")
    return delta_net / delta_lim


# ---------------------------------------------------------------------------
# Debug / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # IPE 300, S235, L = 6 000 mm, q = 10 N/mm, bi-articulé
    # Iy(IPE300) ≈ 8 356 × 10⁴ mm⁴ = 83 560 000 mm⁴
    # E = 210 000 MPa
    L = 6000.0
    E = 210000.0
    I = 83560000.0
    q = 10.0
    delta_0 = 5.0

    d = Deflection(
        mode="distributed",
        support="simply_supported",
        L=L,
        q=q,
        delta_0=delta_0,
        limit_type="floor_general",
        E=E,
        I=I,
    )

    print(d)
    rpt = d.report(with_values=True)
    for fr in rpt:
        print(f"  {fr.name}: {fr.formula_values}")
