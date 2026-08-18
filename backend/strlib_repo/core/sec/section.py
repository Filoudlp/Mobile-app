#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define the base Section class.

    All section types (SecRectangular, SecCircular, SecT, SecI, etc.)
    inherit from this abstract base class.

    The Section class enforces a common interface:
        - Geometric properties (area, inertia, etc.) as @property
        - Reporting via FormulaResult
        - Common utility methods (summary, export)
"""

__all__ = ['Section']

from abc import ABC, abstractmethod
from typing import Optional

from core.formula import FormulaResult


class Section(ABC):
    """
    Classe mère abstraite pour toutes les sections géométriques.

    Responsabilité : définir l'interface commune que toute section
    doit respecter (aire, inerties, modules, rayons de giration, etc.).

    Aucune propriété matériau ici — uniquement de la géométrie pure.

    :param name: Nom de la section (ex: "RECT 300×500", "HEA 200")
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self._name = name or "Section"

    # =================================================================
    # Nom
    # =================================================================

    @property
    def name(self) -> str:
        """Nom de la section"""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    # =================================================================
    # Propriétés abstraites — Obligatoires dans toute section fille
    # =================================================================

    # --- Centre de gravité ---

    @property
    @abstractmethod
    def yg(self) -> float:
        """Position du CDG selon y depuis le bord gauche [mm]"""
        ...

    @property
    @abstractmethod
    def zg(self) -> float:
        """Position du CDG selon z depuis le bord inférieur [mm]"""
        ...

    # --- Aire ---

    @property
    @abstractmethod
    def area(self) -> float:
        """Aire de la section [mm²]"""
        ...

    # --- Moments d'inertie ---

    @property
    @abstractmethod
    def inertia_y(self) -> float:
        """Moment d'inertie selon y [mm⁴]"""
        ...

    @property
    @abstractmethod
    def inertia_z(self) -> float:
        """Moment d'inertie selon z [mm⁴]"""
        ...

    # --- Moments statiques max ---

    @property
    @abstractmethod
    def sy(self) -> float:
        """Moment statique maximal selon y [mm³]"""
        ...

    @property
    @abstractmethod
    def sz(self) -> float:
        """Moment statique maximal selon z [mm³]"""
        ...

    # --- Modules de résistance élastiques ---

    @property
    @abstractmethod
    def wel_y(self) -> float:
        """Module de résistance élastique selon y [mm³]"""
        ...

    @property
    @abstractmethod
    def wel_z(self) -> float:
        """Module de résistance élastique selon z [mm³]"""
        ...

    # --- Modules de résistance plastiques ---

    @property
    @abstractmethod
    def wpl_y(self) -> float:
        """Module de résistance plastique selon y [mm³]"""
        ...

    @property
    @abstractmethod
    def wpl_z(self) -> float:
        """Module de résistance plastique selon z [mm³]"""
        ...

    # --- Rayons de giration ---

    @property
    @abstractmethod
    def iy(self) -> float:
        """Rayon de giration selon y [mm]"""
        ...

    @property
    @abstractmethod
    def iz(self) -> float:
        """Rayon de giration selon z [mm]"""
        ...

    # --- Périmètre ---

    @property
    @abstractmethod
    def perimeter(self) -> float:
        """Périmètre de la section [mm]"""
        ...

    # =================================================================
    # Reports abstraits
    # =================================================================

    @abstractmethod
    def all_reports(self) -> list[FormulaResult]:
        """Renvoie la liste de tous les FormulaResult de la section."""
        ...

    # =================================================================
    # Méthodes utilitaires communes
    # =================================================================

    def summary(self) -> dict[str, float]:
        """
        Renvoie un dictionnaire résumé de toutes les propriétés
        géométriques principales. Utile pour l'export ou le debug.

        :return: dict {nom_propriété: valeur}
        """
        return {
            "name": self._name,
            "yg [mm]": self.yg,
            "zg [mm]": self.zg,
            "A [mm²]": self.area,
            "Iy [mm⁴]": self.inertia_y,
            "Iz [mm⁴]": self.inertia_z,
            "Sy [mm³]": self.sy,
            "Sz [mm³]": self.sz,
            "Wel,y [mm³]": self.wel_y,
            "Wel,z [mm³]": self.wel_z,
            "Wpl,y [mm³]": self.wpl_y,
            "Wpl,z [mm³]": self.wpl_z,
            "iy [mm]": self.iy,
            "iz [mm]": self.iz,
            "u [mm]": self.perimeter,
        }

    def to_markdown(self) -> str:
        """
        Génère un tableau markdown des propriétés géométriques.
        Utile pour l'intégration dans des rapports de calcul.

        :return: str (tableau markdown)
        """
        lines = [
            f"### {self._name}",
            "",
            "| Propriété | Valeur | Unité |",
            "|-----------|-------:|-------|",
        ]
        mapping = [
            ("A",      self.area,      "mm²"),
            ("yg",     self.yg,        "mm"),
            ("zg",     self.zg,        "mm"),
            ("Iy",     self.inertia_y, "mm⁴"),
            ("Iz",     self.inertia_z, "mm⁴"),
            ("Sy",     self.sy,        "mm³"),
            ("Sz",     self.sz,        "mm³"),
            ("Wel,y",  self.wel_y,     "mm³"),
            ("Wel,z",  self.wel_z,     "mm³"),
            ("Wpl,y",  self.wpl_y,     "mm³"),
            ("Wpl,z",  self.wpl_z,     "mm³"),
            ("iy",     self.iy,        "mm"),
            ("iz",     self.iz,        "mm"),
            ("u",      self.perimeter,  "mm"),
        ]
        for name, val, unit in mapping:
            lines.append(f"| {name:7s} | {val:>12.2f} | {unit} |")

        return "\n".join(lines)

    # =================================================================
    # Affichage
    # =================================================================

    @abstractmethod
    def __repr__(self) -> str:
        ...

    @abstractmethod
    def __str__(self) -> str:
        ...
