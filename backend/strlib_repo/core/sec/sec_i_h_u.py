#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define I/H/U steel section geometric properties.

    This class is purely geometric — no material dependency.
    Properties are either provided by the user or loaded from a JSON database
    containing standard profile catalogues (IPE, HEA, HEB, HEM, UPE, UPN, etc.).

    Material-specific properties (class of section, effective area, etc.)
    live in Section_Material classes (SecMatSteel, etc.).

    References:
        - ArcelorMittal / Stahlbau profile tables
        - EN 10365 — Hot rolled steel channels, I and H sections
"""

__all__ = ['SecIHU']

import json
import math
from pathlib import Path
from typing import Optional

from core.sec.section import Section
from core.formula import FormulaResult
import data
from utility.lookupinjson import get_section


# =============================================================================
# SecIHU
# =============================================================================

class SecIHU(Section):
    """
    Section en I, H ou U — propriétés géométriques pures.

    Toutes les propriétés sont stockées directement (pas de calcul analytique) :
    elles proviennent soit du JSON de la base de données, soit des valeurs
    fournies par l'utilisateur via **kwargs.

    Convention d'axes (identique aux catalogues acier) :
        - y-y : axe fort  (flexion dans le plan de l'âme)
        - z-z : axe faible (flexion perpendiculaire à l'âme)
        - Origine au centre de gravité

    Deux modes de construction :
        1. **Par nom de profilé** : ``SecIHU("IPE 300")``
           → charge les données depuis le JSON.
        2. **Par kwargs**         : ``SecIHU(h=300, b=150, tw=7.1, …)``
           → l'utilisateur fournit toutes les grandeurs nécessaires.

    :param name:        Nom du profilé (ex. "IPE 300", "HEA 200", "UPN 220")
    :param db_path:     Chemin vers le fichier JSON (optionnel)
    :param kwargs:      Propriétés géométriques fournies manuellement
    """

    # Liste des clés attendues (pour validation et itération)
    _KEYS = (
        "G", "h", "b", "tw", "tf", "r",
        "A", "hi",
        "Iy", "Iz",
        "wel_y", "wel_z",
        "wpl_y", "wpl_z",
        "iy", "iz",
        "It", "Iw",
        "Avz", "Ss"
    )

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------

    def __init__(
        self,
        name: str,
        sec_data: Optional[Section] = None,
        **kwargs,
    ) -> None:

        # --- Chargement depuis JSON si un nom est fourni ---
        data: dict = {}
        if not kwargs:
            data = sec_data
        elif kwargs:
            data.update(kwargs)

        # --- Masse linéaire ---
        self._G: float = data.get("G", 0.0) 
    
        # --- Dimensions principales ---
        self._h: float = data.get("h", 0.0)
        self._b: float = data.get("b", 0.0)
        self._tw: float = data.get("tw", 0.0)
        self._tf: float = data.get("tf", 0.0)
        self._r: float = data.get("r", 0.0)
        self.hi: float = data.get("hi", self._h - 2 * self._tf)  # Hauteur intérieure (optionnelle)

        # --- Aire ---
        self._area: float = data.get("A", 0.0)

        # --- Aire de cisaillement ---
        self._Avz: float = data.get("Avz", 0.0)

        # --- Moments d'inertie ---
        self._inertia_y: float = data.get("Iy", 0.0)
        self._inertia_z: float = data.get("Iz", 0.0)

        # --- Modules élastiques ---
        self._wel_y: float = data.get("wel_y", 0.0)
        self._wel_z: float = data.get("wel_z", 0.0)
        
        # --- Modules plastiques ---
        self._wpl_y: float = data.get("wpl_y", 0.0)
        self._wpl_z: float = data.get("wpl_z", 0.0)

        # --- Rayons de giration ---
        self._iy: float = data.get("iy", 0.0)
        self._iz: float = data.get("iz", 0.0)

        # --- Constantes de torsion ---
        self._It: float = data.get("It", 0.0)
        self._Iw: float = data.get("Iw", 0.0)

        # --- Centre de gravité ---
        self._yg: float = data.get("yg", self._b / 2 if self._b else 0.0)
        self._zg: float = data.get("zg", self._h / 2 if self._h else 0.0)

        # --- Longueur d'appuis rigide ---
        self._Ss: float = data.get("Ss", 0.0)

        # --- Classification (utilisée pour la sélection auto des courbes
        #     de flambement / déversement — Tableaux 6.2, 6.4, 6.5) ---
        self._section_type: str = data.get("section_type", "H")

        # --- Nom ---
        _name = name
        super().__init__(name=_name)

    # =================================================================
    # Dimensions principales (avec setters)
    # =================================================================

    @property
    def h(self) -> float:
        """Hauteur totale du profilé [mm]"""
        return self._h

    @h.setter
    def h(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"h doit être strictement positif (reçu : {value})")
        self._h = value

    @property
    def b(self) -> float:
        """Largeur de la semelle [mm]"""
        return self._b

    @b.setter
    def b(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"b doit être strictement positif (reçu : {value})")
        self._b = value

    @property
    def tw(self) -> float:
        """Épaisseur de l'âme [mm]"""
        return self._tw

    @tw.setter
    def tw(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"tw doit être strictement positif (reçu : {value})")
        self._tw = value

    @property
    def tf(self) -> float:
        """Épaisseur de la semelle [mm]"""
        return self._tf

    @tf.setter
    def tf(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"tf doit être strictement positif (reçu : {value})")
        self._tf = value

    @property
    def r(self) -> float:
        """Rayon de congé âme-semelle [mm]"""
        return self._r

    @r.setter
    def r(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"r doit être positif ou nul (reçu : {value})")
        self._r = value

    @property
    def section_type(self) -> str:
        """Type de section pour la sélection des courbes de flambement /
        déversement ('I', 'H', 'RHS', 'CHS', 'U', 'L', 'T')."""
        return self._section_type

    @section_type.setter
    def section_type(self, value: str) -> None:
        self._section_type = value

    @property
    def hi(self) -> float:
        """Hauteur intérieure [mm]"""
        return self._hi

    @hi.setter
    def hi(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"hi doit être positif (reçu : {value})")
        self._hi = value

    # =================================================================
    # Centre de gravité
    # =================================================================

    @property
    def yg(self) -> float:
        """Position du CDG selon y depuis le bord gauche [mm]"""
        return self._yg

    @property
    def yg_report(self) -> FormulaResult:
        return FormulaResult(
            name="yg",
            formula="yg (donnée catalogue)",
            formula_values=f"yg = {self.yg:.2f}",
            result=self.yg,
            unit="mm",
            ref="Catalogue profilé",
        )

    @property
    def zg(self) -> float:
        """Position du CDG selon z depuis le bord inférieur [mm]"""
        return self._zg

    @property
    def zg_report(self) -> FormulaResult:
        return FormulaResult(
            name="zg",
            formula="zg (donnée catalogue)",
            formula_values=f"zg = {self.zg:.2f}",
            result=self.zg,
            unit="mm",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Aire
    # =================================================================

    @property
    def area(self) -> float:
        """Aire de la section [mm²]"""
        return self._area

    @area.setter
    def area(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"area doit être positif (reçu : {value})")
        self._area = value

    @property
    def area_report(self) -> FormulaResult:
        return FormulaResult(
            name="A",
            formula="A (donnée catalogue)",
            formula_values=f"A = {self.area:.2f}",
            result=self.area,
            unit="mm²",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Aire de cisaillement
    # =================================================================

    @property
    def Avz(self) -> float:
        """Aire de cisaillement selon z [mm²]"""
        return self._Avz

    @Avz.setter
    def Avz(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"Avz doit être positif (reçu : {value})")
        self._Avz = value

    @property
    def Avz_report(self) -> FormulaResult:
        return FormulaResult(
            name="Av,z",
            formula="Av,z (donnée catalogue)",
            formula_values=f"Av,z = {self.Avz:.2f}",
            result=self.Avz,
            unit="mm²",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Moments d'inertie
    # =================================================================

    @property
    def inertia_y(self) -> float:
        """Moment d'inertie selon y-y (axe fort) [mm⁴]"""
        return self._inertia_y

    @inertia_y.setter
    def inertia_y(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"inertia_y doit être positif (reçu : {value})")
        self._inertia_y = value

    @property
    def inertia_y_report(self) -> FormulaResult:
        return FormulaResult(
            name="Iy",
            formula="Iy (donnée catalogue)",
            formula_values=f"Iy = {self.inertia_y:.2f}",
            result=self.inertia_y,
            unit="mm⁴",
            ref="Catalogue profilé",
        )

    @property
    def inertia_z(self) -> float:
        """Moment d'inertie selon z-z (axe faible) [mm⁴]"""
        return self._inertia_z

    @inertia_z.setter
    def inertia_z(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"inertia_z doit être positif (reçu : {value})")
        self._inertia_z = value

    @property
    def inertia_z_report(self) -> FormulaResult:
        return FormulaResult(
            name="Iz",
            formula="Iz (donnée catalogue)",
            formula_values=f"Iz = {self.inertia_z:.2f}",
            result=self.inertia_z,
            unit="mm⁴",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Modules de résistance élastiques
    # =================================================================

    @property
    def wel_y(self) -> float:
        """Module de résistance élastique selon y-y [mm³]"""
        return self._wel_y

    @wel_y.setter
    def wel_y(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"wel_y doit être positif (reçu : {value})")
        self._wel_y = value

    @property
    def wel_y_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wel,y",
            formula="Wel,y (donnée catalogue)",
            formula_values=f"Wel,y = {self.wel_y:.2f}",
            result=self.wel_y,
            unit="mm³",
            ref="Catalogue profilé",
        )

    @property
    def wel_z(self) -> float:
        """Module de résistance élastique selon z-z [mm³]"""
        return self._wel_z

    @wel_z.setter
    def wel_z(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"wel_z doit être positif (reçu : {value})")
        self._wel_z = value

    @property
    def wel_z_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wel,z",
            formula="Wel,z (donnée catalogue)",
            formula_values=f"Wel,z = {self.wel_z:.2f}",
            result=self.wel_z,
            unit="mm³",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Modules de résistance plastiques
    # =================================================================

    @property
    def wpl_y(self) -> float:
        """Module de résistance plastique selon y-y [mm³]"""
        return self._wpl_y

    @wpl_y.setter
    def wpl_y(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"wpl_y doit être positif (reçu : {value})")
        self._wpl_y = value

    @property
    def wpl_y_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wpl,y",
            formula="Wpl,y (donnée catalogue)",
            formula_values=f"Wpl,y = {self.wpl_y:.2f}",
            result=self.wpl_y,
            unit="mm³",
            ref="Catalogue profilé",
        )

    @property
    def wpl_z(self) -> float:
        """Module de résistance plastique selon z-z [mm³]"""
        return self._wpl_z

    @wpl_z.setter
    def wpl_z(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"wpl_z doit être positif (reçu : {value})")
        self._wpl_z = value

    @property
    def wpl_z_report(self) -> FormulaResult:
        return FormulaResult(
            name="Wpl,z",
            formula="Wpl,z (donnée catalogue)",
            formula_values=f"Wpl,z = {self.wpl_z:.2f}",
            result=self.wpl_z,
            unit="mm³",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Rayons de giration
    # =================================================================

    @property
    def iy(self) -> float:
        """Rayon de giration selon y-y [mm]"""
        return self._iy

    @iy.setter
    def iy(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"iy doit être positif (reçu : {value})")
        self._iy = value

    @property
    def iy_report(self) -> FormulaResult:
        return FormulaResult(
            name="iy",
            formula="iy (donnée catalogue)",
            formula_values=f"iy = {self.iy:.2f}",
            result=self.iy,
            unit="mm",
            ref="Catalogue profilé",
        )

    @property
    def iz(self) -> float:
        """Rayon de giration selon z-z [mm]"""
        return self._iz

    @iz.setter
    def iz(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"iz doit être positif (reçu : {value})")
        self._iz = value

    @property
    def iz_report(self) -> FormulaResult:
        return FormulaResult(
            name="iz",
            formula="iz (donnée catalogue)",
            formula_values=f"iz = {self.iz:.2f}",
            result=self.iz,
            unit="mm",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Inertie de torsion
    # =================================================================

    @property
    def It(self) -> float:
        """Constante de torsion de Saint-Venant [mm⁴]"""
        return self._It

    @It.setter
    def It(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"It doit être positif (reçu : {value})")
        self._It = value

    @property
    def It_report(self) -> FormulaResult:
        return FormulaResult(
            name="It",
            formula="It (donnée catalogue)",
            formula_values=f"It = {self.It:.2f}",
            result=self.It,
            unit="mm⁴",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Inertie de gauchissement
    # =================================================================
    @property
    def Iw(self) -> float:
        """Constante de gauchissement [mm⁶]"""
        return self._Iw

    @Iw.setter
    def Iw(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"Iw doit être positif (reçu : {value})")
        self._Iw = value

    @property
    def Iw_report(self) -> FormulaResult:
        return FormulaResult(
            name="Iw",
            formula="Iw (donnée catalogue)",
            formula_values=f"Iw = {self.Iw:.4e}",
            result=self.Iw,
            unit="mm⁶",
            ref="Catalogue profilé",
        )

    # =================================================================
    # Rapports d'élancement des parois (utiles pour la classe de section)
    # =================================================================

    @property
    def cf_tf(self) -> float:
        """Élancement de la semelle : c/tf  avec c = (b - tw - 2r) / 2"""
        if self._tf == 0:
            return 0.0
        c = (self._b - self._tw - 2 * self._r) / 2
        return c / self._tf

    @property
    def cf_tf_report(self) -> FormulaResult:
        c = (self._b - self._tw - 2 * self._r) / 2
        return FormulaResult(
            name="c/tf",
            formula="c/tf  avec c = (b - tw - 2r) / 2",
            formula_values=(
                f"c = ({self._b:.2f} - {self._tw:.2f} - 2×{self._r:.2f}) / 2 "
                f"= {c:.2f} → c/tf = {c:.2f} / {self._tf:.2f} = {self.cf_tf:.2f}"
            ),
            result=self.cf_tf,
            unit="-",
            ref="EC3-1-1 — Tableau 5.2",
        )

    @property
    def dw_tw(self) -> float:
        """Élancement de l'âme : hi/tw"""
        if self._tw == 0:
            return 0.0
        return self._hi / self._tw

    @property
    def dw_tw_report(self) -> FormulaResult:
        return FormulaResult(
            name="hi/tw",
            formula="hi/tw",
            formula_values=(
                f"hi/tw = {self._hi:.2f} / {self._tw:.2f} = {self.dw_tw:.2f}"
            ),
            result=self.dw_tw,
            unit="-",
            ref="EC3-1-1 — Tableau 5.2",
        )

    # =================================================================
    # Mandatory
    # =================================================================


    def sy(self) -> float:
        """Moment statique maximal selon y [mm³]"""
        raise "Not implemented yet"

    def sz(self) -> float:
        """Moment statique maximal selon z [mm³]"""
        
        raise "Not implemented yet"

    def perimeter(self) -> float:
        """Périmètre de la section [mm]"""
        raise "Not implemented yet"

    # =================================================================
    # Rapport complet
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        """Renvoie la liste de tous les FormulaResult."""
        return [
            self.area_report,
            self.Avz_report,
            self.yg_report,
            self.zg_report,
            self.inertia_y_report,
            self.inertia_z_report,
            self.wel_y_report,
            self.wel_z_report,
            self.wpl_y_report,
            self.wpl_z_report,
            self.iy_report,
            self.iz_report,
            self.It_report,
            self.Iw_report,
            self.cf_tf_report,
            self.dw_tw_report,
        ]

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"SecIHU(name='{self._name}', h={self._h}, b={self._b}, "
            f"tw={self._tw}, tf={self._tf}, r={self._r})"
        )

    def __str__(self) -> str:
        lines = [
            f"{'=' * 75}",
            f"  {self._name}",
            f"  h={self._h:.1f}  b={self._b:.1f}  tw={self._tw:.1f}  "
            f"tf={self._tf:.1f}  r={self._r:.1f}  [mm]",
            f"{'=' * 75}",
        ]
        for r in self.all_reports():
            lines.append(
                f"  {r.name:10s} = {r.result:>14.2f} {r.unit:6s}  ({r.ref})"
            )
        lines.append(f"{'=' * 75}")
        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    # --- Mode kwargs (sans JSON) ---
    # ipe300 = SecIHU(
    #     name="IPE 300",
    #     h=300, b=150, tw=7.1, tf=10.7, r=15,
    #     A=5381,
    #     Avz=2568,
    #     Iy=83560000,
    #     Iz=6038000,
    #     wel_y=557100,
    #     wel_z=80510,
    #     wpl_y=628400,
    #     wpl_z=125200,
    #     iy=124.6,
    #     iz=33.5,
    #     It=201000,
    #     Iw=126000000000,
    # )

    with open("ressource/IPE.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    sec = "IPE A 300"
    data = get_section(data, sec)

    ipe300 = SecIHU(sec, data)
    print(ipe300)
    print()

    # --- Accès individuel ---
    print(f"A    = {ipe300.area:.0f} mm²")
    print(f"Iy   = {ipe300.inertia_y:.0f} mm⁴")
    print(f"Wpl,y= {ipe300.wpl_y:.0f} mm³")
    print(f"c/tf = {ipe300.cf_tf:.2f}")
    print(f"d/tw = {ipe300.dw_tw:.2f}")
    print()

    # --- Repr ---
    print(repr(ipe300))
