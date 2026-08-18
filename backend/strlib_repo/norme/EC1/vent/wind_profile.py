#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Profil de vent et pression dynamique de pointe qp(z) — France et Suisse.

France — NF EN 1991-1-4 §4.3-4.5 + Annexe nationale, Tableau 4.1(NA) :
    cr(z) = kr · ln(z / z0)                        éq. (4.4)
    kr = 0,19 · (z0 / z0,II)^0,07 , z0,II = 0,05 m  éq. (4.5)
    vm(z) = cr(z) · co(z) · vb                      éq. (4.3)
    Iv(z) = kI / [co(z) · ln(z / z0)] , kI = 1,0    éq. (4.7)
    qp(z) = [1 + 7·Iv(z)] · 0,5 · ρ · vm(z)²         éq. (4.8)
    Coefficient d'orographie co(z) : procédure complète (4.3.3 NA, cas
    terrain complexe / obstacle isolé) hors périmètre — valeur par défaut
    co = 1,0 (terrain courant, sans relief marqué), modifiable en avancé.

Suisse — SIA 261:2020 §6.2.1, Tableau 4 :
    qp = ch(z)² · qp0                               éq. (11)
    ch(z) = (z / zg)^αr , avec les planchers de hauteur minimale du §6.2.1.2
    (z = 5 m pour les catégories II/IIa/III si z < 5 m ; z = 10 m pour la
    catégorie IV si z < 10 m ; au-delà de 30 m, profil de la catégorie III
    utilisé à la place de la catégorie IV).

    ⚠ L'éq. (12) donnant ch(z) est rendue par une image dans le PDF source
    (OCR indisponible) ; la loi puissance ch(z) = (z/zg)^αr est la
    reconstruction usuelle de cette formule (cohérente avec les valeurs de
    zg/αr du Tableau 4 et l'allure de la Figure 6) — à confirmer contre le
    document source avant tout usage en production.
"""

__all__ = [
    'FR_TERRAIN_CATEGORIES', 'CH_TERRAIN_CATEGORIES',
    'TerrainRoughnessFR', 'WindPressureFR',
    'TerrainProfileCH', 'WindPressureCH',
]

import math
from typing import Dict, Tuple

from core.formula import FormulaResult, FormulaCollection
from norme.EC1.vent.base_velocity import RHO_AIR

# ---------------------------------------------------------------------------
# France — Tableau 4.1(NA) : catégories et paramètres de terrain
# ---------------------------------------------------------------------------

#: {catégorie: (z0 [m], zmin [m])} — NF EN 1991-1-4/NA, Tableau 4.1(NA).
FR_TERRAIN_CATEGORIES: Dict[str, Tuple[float, float]] = {
    "0": (0.005, 1.0),
    "II": (0.05, 2.0),
    "IIIa": (0.20, 5.0),
    "IIIb": (0.50, 9.0),
    "IV": (1.00, 15.0),
}

_Z0_II = 0.05
_ZMAX = 200.0
_KI = 1.0


class TerrainRoughnessFR:
    """Coefficient de rugosité cr(z) — France (NF EN 1991-1-4/NA §4.3.2)."""

    def __init__(self, category: str) -> None:
        if category not in FR_TERRAIN_CATEGORIES:
            raise ValueError(
                f"Catégorie de terrain '{category}' inconnue. "
                f"Valeurs valides : {list(FR_TERRAIN_CATEGORIES.keys())}"
            )
        self.__category = category
        self.__z0, self.__zmin = FR_TERRAIN_CATEGORIES[category]

    @property
    def category(self) -> str:
        return self.__category

    @property
    def z0(self) -> float:
        return self.__z0

    @property
    def zmin(self) -> float:
        return self.__zmin

    @property
    def kr(self) -> float:
        """Facteur de terrain kr — éq. (4.5)."""
        return round(0.19 * (self.__z0 / _Z0_II) ** 0.07, 5)

    def _z_eff(self, z: float) -> float:
        z = min(z, _ZMAX)
        return max(z, self.__zmin)

    def cr(self, z: float) -> float:
        """Coefficient de rugosité cr(z) — éq. (4.4)."""
        z_eff = self._z_eff(z)
        return round(self.kr * math.log(z_eff / self.__z0), 5)

    def __repr__(self) -> str:
        return f"TerrainRoughnessFR(category='{self.__category}', z0={self.__z0}, zmin={self.__zmin})"


class WindPressureFR:
    """
    Vitesse moyenne et pression dynamique de pointe qp(z) — France.

    :param vb: Vitesse de référence du vent [m/s] (BaseWindVelocityFR.vb).
    :param category: Catégorie de terrain FR ('0', 'II', 'IIIa', 'IIIb', 'IV').
    :param co: Coefficient d'orographie (1,0 par défaut — terrain courant).
    """

    def __init__(self, vb: float, category: str, co: float = 1.0) -> None:
        self.__vb = vb
        self.__roughness = TerrainRoughnessFR(category)
        self.__co = co

    @property
    def vb(self) -> float:
        return self.__vb

    @property
    def roughness(self) -> TerrainRoughnessFR:
        return self.__roughness

    @property
    def co(self) -> float:
        return self.__co

    def vm(self, z: float) -> float:
        """Vitesse moyenne du vent vm(z) [m/s] — éq. (4.3)."""
        return round(self.__roughness.cr(z) * self.__co * self.__vb, 4)

    def Iv(self, z: float) -> float:
        """Intensité de turbulence Iv(z) — éq. (4.7)."""
        z_eff = self.__roughness._z_eff(z)
        denom = self.__co * math.log(z_eff / self.__roughness.z0)
        return round(_KI / denom, 5)

    def qp(self, z: float) -> float:
        """Pression dynamique de pointe qp(z) [kN/m²] — éq. (4.8)."""
        vm = self.vm(z)
        iv = self.Iv(z)
        return round((1 + 7 * iv) * 0.5 * RHO_AIR * vm ** 2 / 1000.0, 5)

    def get_qp(self, z: float, with_values: bool = False) -> FormulaResult:
        fv = ""
        if with_values:
            fv = (
                f"qp({z:.1f}) = [1 + 7×{self.Iv(z):.4f}] × 0,5 × {RHO_AIR} × "
                f"{self.vm(z):.2f}² = {self.qp(z):.4f} kN/m²"
            )
        return FormulaResult(
            name=f"qp({z:.1f}m)",
            formula="qp(z) = [1 + 7·Iv(z)] · 0,5 · ρ · vm(z)²",
            formula_values=fv,
            result=self.qp(z),
            unit="kN/m²",
            ref="NF EN 1991-1-4 — éq. (4.8)",
        )

    def report(self, z: float, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Pression dynamique de pointe — France, z={z:.1f}m",
            ref="NF EN 1991-1-4",
        )
        fc.add(self.get_qp(z, with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return f"WindPressureFR(vb={self.__vb:.2f}m/s, category='{self.__roughness.category}', co={self.__co})"


# ---------------------------------------------------------------------------
# Suisse — SIA 261:2020, §6.2.1, Tableau 4
# ---------------------------------------------------------------------------

#: {catégorie: (zg [m], αr)} — SIA 261, Tableau 4.
CH_TERRAIN_CATEGORIES: Dict[str, Tuple[float, float]] = {
    "II": (300.0, 0.16),    # rive lacustre
    "IIa": (380.0, 0.19),   # grande plaine
    "III": (450.0, 0.23),   # localité, milieu rural
    "IV": (526.0, 0.30),    # zone urbaine étendue
}


class TerrainProfileCH:
    """Coefficient du profil de vent ch(z) — Suisse (SIA 261 §6.2.1.2)."""

    def __init__(self, category: str) -> None:
        if category not in CH_TERRAIN_CATEGORIES:
            raise ValueError(
                f"Catégorie de terrain '{category}' inconnue. "
                f"Valeurs valides : {list(CH_TERRAIN_CATEGORIES.keys())}"
            )
        self.__category = category
        self.__zg, self.__alpha_r = CH_TERRAIN_CATEGORIES[category]

    @property
    def category(self) -> str:
        return self.__category

    @property
    def zg(self) -> float:
        return self.__zg

    @property
    def alpha_r(self) -> float:
        return self.__alpha_r

    def _resolve(self, z: float) -> Tuple[float, float]:
        """Applique les planchers de hauteur et le remplacement catégorie
        IV -> III au-delà de 30 m (SIA 261 §6.2.1.2)."""
        category, zg, alpha_r = self.__category, self.__zg, self.__alpha_r
        if category == "IV" and z > 30.0:
            zg, alpha_r = CH_TERRAIN_CATEGORIES["III"]
            category = "III"
        z_floor = 10.0 if category == "IV" else 5.0
        z_eff = max(z, z_floor)
        return z_eff, zg, alpha_r

    def ch(self, z: float) -> float:
        """Coefficient du profil de répartition du vent ch(z) — éq. (12)
        [reconstruction — voir avertissement en tête de module]."""
        z_eff, zg, alpha_r = self._resolve(z)
        return round((z_eff / zg) ** alpha_r, 5)

    def __repr__(self) -> str:
        return f"TerrainProfileCH(category='{self.__category}', zg={self.__zg}, alpha_r={self.__alpha_r})"


class WindPressureCH:
    """
    Pression dynamique qp(z) — Suisse (SIA 261:2020 §6.2.1.3, éq. 11).

    :param qp0: Pression dynamique de référence [kN/m²] (ReferencePressureCH.qp0).
    :param category: Catégorie de terrain CH ('II', 'IIa', 'III', 'IV').
    """

    def __init__(self, qp0: float, category: str) -> None:
        self.__qp0 = qp0
        self.__profile = TerrainProfileCH(category)

    @property
    def qp0(self) -> float:
        return self.__qp0

    @property
    def profile(self) -> TerrainProfileCH:
        return self.__profile

    def qp(self, z: float) -> float:
        """Pression dynamique qp(z) [kN/m²] — éq. (11) : qp = ch(z)² · qp0."""
        ch = self.__profile.ch(z)
        return round(ch ** 2 * self.__qp0, 5)

    def get_qp(self, z: float, with_values: bool = False) -> FormulaResult:
        fv = ""
        if with_values:
            fv = (
                f"qp({z:.1f}) = {self.__profile.ch(z):.4f}² × {self.__qp0:.2f} "
                f"= {self.qp(z):.4f} kN/m²"
            )
        return FormulaResult(
            name=f"qp({z:.1f}m)",
            formula="qp(z) = ch(z)² · qp0",
            formula_values=fv,
            result=self.qp(z),
            unit="kN/m²",
            ref="SIA 261:2020 — éq. (11) [ch(z) à confirmer]",
        )

    def report(self, z: float, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Pression dynamique — Suisse, z={z:.1f}m",
            ref="SIA 261:2020",
        )
        fc.add(self.get_qp(z, with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return f"WindPressureCH(qp0={self.__qp0:.2f}kN/m², category='{self.__profile.category}')"


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    print("=== France ===")
    wp = WindPressureFR(vb=24.0, category="II")
    for z in (3, 10, 20):
        print(f"  z={z}m : vm={wp.vm(z):.2f}m/s  Iv={wp.Iv(z):.4f}  qp={wp.qp(z):.4f}kN/m²")

    print("\n=== Suisse ===")
    wp_ch = WindPressureCH(qp0=0.9, category="III")
    for z in (3, 10, 20):
        print(f"  z={z}m : ch={wp_ch.profile.ch(z):.4f}  qp={wp_ch.qp(z):.4f}kN/m²")
