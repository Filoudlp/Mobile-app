# drift.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification des déplacements horizontaux (drift) selon l'EC3-1-1 — §7.2.

La classe ``Drift`` compare un déplacement horizontal calculé à une limite
déduite de la hauteur et du type de structure, ou fournie directement.
"""

__all__ = ["Drift", "drift_check"]

from typing import TypeVar, Optional

from core.formula import FormulaResult, FormulaCollection
from ec3.ec3_1_1.serviceability.limits import get_drift_limit, HORIZONTAL_LIMITS

section = TypeVar("section")
material = TypeVar("material")


class Drift:
    """
    Vérification du déplacement horizontal d'une structure.

    Paramètres
    ----------
    delta : float
        Déplacement horizontal calculé [mm].
    height : float
        Hauteur totale H ou entre niveaux h [mm].
    structure_type : str
        Clé dans ``HORIZONTAL_LIMITS``
        (``"portal_top"``, ``"portal_inter_storey"``,
         ``"multi_storey_total"``, ``"multi_storey_inter_storey"``).
    limit_ratio : float, optional
        Ratio personnalisé (ex. 300 → H/300).
    drift_limit : float, optional
        Déplacement limite fourni directement [mm].
    """

    def __init__(
        self,
        delta: float,
        height: float,
        structure_type: str = "portal_top",
        *,
        limit_ratio: Optional[float] = None,
        drift_limit: Optional[float] = None,
    ) -> None:
        self.__delta: float = abs(float(delta))
        self.__height: float = float(height)
        self.__structure_type: str = structure_type
        self.__limit_ratio: Optional[float] = limit_ratio
        self.__drift_limit_input: Optional[float] = drift_limit

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def delta(self) -> float:
        """Déplacement horizontal calculé [mm]."""
        return self.__delta

    @property
    def delta_limit(self) -> float:
        """Déplacement horizontal admissible [mm]."""
        if self.__drift_limit_input is not None:
            return self.__drift_limit_input
        return get_drift_limit(
            self.__height,
            structure_type=self.__structure_type,
            custom_ratio=self.__limit_ratio,
        )

    @property
    def verif(self) -> float:
        """Taux δ / δ_lim."""
        if self.delta_limit == 0:
            return float("inf")
        return round(self.__delta / self.delta_limit, 4)

    @property
    def is_ok(self) -> bool:
        """True si δ ≤ δ_lim."""
        return self.verif <= 1.0

    # -----------------------------------------------------------------------
    # FormulaResult builders
    # -----------------------------------------------------------------------

    def get_delta_limit(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour le déplacement limite."""
        r = self.delta_limit
        if self.__drift_limit_input is not None:
            formula = "δ_lim (fournie par l'utilisateur)"
            fv = f"δ_lim = {r:.2f} mm" if with_values else ""
        else:
            ratio = self.__limit_ratio or HORIZONTAL_LIMITS.get(
                self.__structure_type, 300
            )
            formula = f"δ_lim = H / {ratio:.0f}"
            fv = ""
            if with_values:
                fv = f"δ_lim = {self.__height:.1f} / {ratio:.0f} = {r:.2f} mm"
        return FormulaResult(
            name="δ_lim",
            formula=formula,
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC3-1-1 — §7.2",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification δ / δ_lim ≤ 1.0."""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"δ / δ_lim = {self.__delta:.2f} / {self.delta_limit:.2f} "
                f"= {r:.4f} ≤ 1.0 → {status}"
            )
        return FormulaResult(
            name="δ/δ_lim",
            formula="δ / δ_lim ≤ 1.0",
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
            title="Vérification du déplacement horizontal",
            ref="EC3-1-1 — §7.2",
        )
        fc.add(self.get_delta_limit(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"Drift(δ={self.__delta:.2f}, δ_lim={self.delta_limit:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ---------------------------------------------------------------------------
# Fonction standalone
# ---------------------------------------------------------------------------

def drift_check(
    delta: float,
    height: float,
    limit_ratio: float = 300.0,
) -> float:
    """
    Vérification rapide de déplacement horizontal sans instancier la classe.

    :param delta:       Déplacement calculé [mm].
    :param height:      Hauteur H ou h [mm].
    :param limit_ratio: Ratio (300 → H/300).
    :return:            Taux δ / δ_lim.
    """
    delta_lim = height / limit_ratio if limit_ratio != 0 else 0.0
    if delta_lim == 0:
        return float("inf")
    return abs(delta) / delta_lim


# ---------------------------------------------------------------------------
# Debug / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # δ = 15 mm, H = 6 000 mm, limite H/300
    d = Drift(delta=15.0, height=6000.0, structure_type="portal_top")

    print(d)
    rpt = d.report(with_values=True)
    for fr in rpt:
        print(f"  {fr.name}: {fr.formula_values}")
