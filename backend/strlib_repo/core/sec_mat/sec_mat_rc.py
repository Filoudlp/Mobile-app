#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define Reinforced Concrete section-material properties.

    Cette classe sert de **conteneur central** pour stocker toutes les
    propriétés d'une section béton armé, avant et après calcul.

    Workflow typique :
        1. Création avec sec + mat_concrete + mat_reinforcement
        2. Calcul externe (flexion, effort tranchant, etc.)
        3. Stockage des résultats (ast, asc, covers, etc.) via setters
        4. Calcul des propriétés dérivées (Ih, Ic, xh, xc)
        5. Affichage / export pour rapports

    UNITS:
        - mm   : lengths
        - mm²  : areas
        - mm⁴  : inertia
        - MPa  : stress
        - N    : forces

    References:
        - EN 1992-1-1 (Eurocode 2)
"""

__all__ = ['SecMatRC', 'RebarSet', 'EXPOSURE_CLASSES', 'STRUCTURAL_CLASSES',
           'CNOM_MIN_TABLE', 'REBAR_AREAS']

from typing import Optional, TypeVar, List, Tuple
from dataclasses import dataclass, field
import math

section = TypeVar('section')
material_concrete = TypeVar('material_concrete')
material_reinforcement = TypeVar('material_reinforcement')


# =============================================================================
# Tableaux réglementaires
# =============================================================================

# --- Diamètres nominaux courants et aires unitaires (mm²) ---
# Référence : barres HA selon NF A 35-080
REBAR_AREAS: dict[int, float] = {
    6:   28.27,    #  π/4 ×  6² =  28.27 mm²
    8:   50.27,    #  π/4 ×  8² =  50.27 mm²
    10:  78.54,    #  π/4 × 10² =  78.54 mm²
    12: 113.10,    #  π/4 × 12² = 113.10 mm²
    14: 153.94,    #  π/4 × 14² = 153.94 mm²
    16: 201.06,    #  π/4 × 16² = 201.06 mm²
    20: 314.16,    #  π/4 × 20² = 314.16 mm²
    25: 490.87,    #  π/4 × 25² = 490.87 mm²
    32: 804.25,    #  π/4 × 32² = 804.25 mm²
    40: 1256.64,   #  π/4 × 40² = 1256.64 mm²
}


# --- Classes d'exposition (EC2 Tableau 4.1) ---
# Clé : classe d'exposition
# Valeur : (description courte, description détaillée, exemples)
EXPOSURE_CLASSES: dict[str, dict] = {
    # ---- Aucun risque de corrosion ----
    "X0": {
        "risk": "Aucun risque",
        "description": "Béton non armé sans risque de corrosion ou d'attaque",
        "examples": "Béton non armé à l'intérieur de bâtiments, "
                     "fondations non armées sans gel",
    },

    # ---- Corrosion induite par carbonatation ----
    "XC1": {
        "risk": "Carbonatation",
        "description": "Sec ou humide en permanence",
        "examples": "Intérieur de bâtiments à faible taux d'humidité, "
                     "béton submergé en permanence",
    },
    "XC2": {
        "risk": "Carbonatation",
        "description": "Humide, rarement sec",
        "examples": "Fondations, surfaces en contact prolongé avec l'eau",
    },
    "XC3": {
        "risk": "Carbonatation",
        "description": "Humidité modérée",
        "examples": "Intérieur de bâtiments à humidité modérée ou élevée, "
                     "extérieur abrité de la pluie",
    },
    "XC4": {
        "risk": "Carbonatation",
        "description": "Alternance d'humidité et de séchage",
        "examples": "Surfaces extérieures soumises à la pluie",
    },

    # ---- Corrosion induite par les chlorures (hors eau de mer) ----
    "XD1": {
        "risk": "Chlorures (hors mer)",
        "description": "Humidité modérée",
        "examples": "Surfaces exposées à des chlorures transportés par l'air",
    },
    "XD2": {
        "risk": "Chlorures (hors mer)",
        "description": "Humide, rarement sec",
        "examples": "Piscines, éléments exposés aux eaux industrielles "
                     "contenant des chlorures",
    },
    "XD3": {
        "risk": "Chlorures (hors mer)",
        "description": "Alternance d'humidité et de séchage",
        "examples": "Parties de ponts, dalles de parking exposées aux "
                     "sels de déverglaçage",
    },

    # ---- Corrosion induite par les chlorures d'eau de mer ----
    "XS1": {
        "risk": "Chlorures (mer)",
        "description": "Air marin, sans contact direct",
        "examples": "Structures proches du littoral (> zone d'éclaboussement)",
    },
    "XS2": {
        "risk": "Chlorures (mer)",
        "description": "Submergé en permanence",
        "examples": "Éléments de structures maritimes immergés en permanence",
    },
    "XS3": {
        "risk": "Chlorures (mer)",
        "description": "Zones de marnage et d'éclaboussement",
        "examples": "Quais, piles de ponts en zone de marnage",
    },

    # ---- Attaque gel/dégel ----
    "XF1": {
        "risk": "Gel/dégel",
        "description": "Saturation modérée sans agent de déverglaçage",
        "examples": "Surfaces verticales exposées à la pluie et au gel",
    },
    "XF2": {
        "risk": "Gel/dégel",
        "description": "Saturation modérée avec agents de déverglaçage",
        "examples": "Surfaces verticales de structures routières "
                     "exposées au gel et au sel",
    },
    "XF3": {
        "risk": "Gel/dégel",
        "description": "Forte saturation sans agent de déverglaçage",
        "examples": "Surfaces horizontales exposées à la pluie et au gel",
    },
    "XF4": {
        "risk": "Gel/dégel",
        "description": "Forte saturation avec agents de déverglaçage",
        "examples": "Routes et tabliers de ponts exposés aux sels, "
                     "surfaces soumises aux embruns et au gel",
    },

    # ---- Attaques chimiques ----
    "XA1": {
        "risk": "Attaque chimique",
        "description": "Environnement à faible agressivité chimique",
        "examples": "Sols naturels, eaux souterraines faiblement agressives",
    },
    "XA2": {
        "risk": "Attaque chimique",
        "description": "Environnement à agressivité chimique modérée",
        "examples": "Sols et eaux souterraines modérément agressifs, "
                     "contact avec des eaux industrielles",
    },
    "XA3": {
        "risk": "Attaque chimique",
        "description": "Environnement à forte agressivité chimique",
        "examples": "Sols et eaux très agressifs, eaux industrielles "
                     "fortement acides ou sulfatées",
    },
}


# --- Classes structurales (EC2 §4.4.1.2) ---
# La classe structurale de base est S4 (durée d'utilisation 50 ans)
# On peut ajuster de S1 à S6 selon les critères du tableau 4.3N
STRUCTURAL_CLASSES: dict[str, dict] = {
    "S1": {
        "lifetime": "≤ 10 ans",
        "description": "Structures temporaires",
        "examples": "Coffrages, structures provisoires de chantier",
    },
    "S2": {
        "lifetime": "≤ 25 ans",
        "description": "Éléments remplaçables",
        "examples": "Éléments structuraux remplaçables (appareils d'appui)",
    },
    "S3": {
        "lifetime": "≤ 50 ans",
        "description": "Classe réduite (conditions favorables)",
        "examples": "Bâtiments courants avec béton ≥ C35/45 vs classe "
                     "d'exposition, ou dalles/membrures ≥ 80 mm",
    },
    "S4": {
        "lifetime": "50 ans",
        "description": "Classe de référence (défaut)",
        "examples": "Bâtiments courants, structures de génie civil courantes",
    },
    "S5": {
        "lifetime": "≤ 100 ans",
        "description": "Classe augmentée",
        "examples": "Structures avec durée de vie requise > 50 ans, "
                     "ou exigences de qualité accrues",
    },
    "S6": {
        "lifetime": "> 100 ans",
        "description": "Classe très élevée",
        "examples": "Ouvrages d'art monumentaux, tunnels à très longue durée",
    },
}


# =============================================================================
# Dataclass pour décrire un groupe de barres
# =============================================================================

@dataclass
class RebarSet:
    """
    Décrit un groupe de barres d'armature identiques.

    Peut être combiné en liste pour décrire une nappe :
        [RebarSet(nb=2, phi=12), RebarSet(nb=2, phi=10)]  →  "2HA12+2HA10"

    :param nb: Nombre de barres
    :param phi: Diamètre nominal en mm
    """
    nb: int
    phi: int

    def __post_init__(self):
        if self.phi not in REBAR_AREAS:
            raise ValueError(
                f"Diamètre HA{self.phi} inconnu. "
                f"Diamètres disponibles : {list(REBAR_AREAS.keys())}"
            )
        if self.nb < 0:
            raise ValueError("Le nombre de barres doit être ≥ 0")

    @property
    def area_unit(self) -> float:
        """Aire d'une barre (mm²)."""
        return REBAR_AREAS[self.phi]

    @property
    def area(self) -> float:
        """Aire totale du groupe (mm²)."""
        return self.nb * self.area_unit

    @property
    def area_cm2(self) -> float:
        """Aire totale du groupe (cm²)."""
        return self.area / 100.0

    @property
    def label(self) -> str:
        """Label court : ex '2HA12'."""
        return f"{self.nb}HA{self.phi}"

    def __repr__(self) -> str:
        return f"RebarSet({self.label} → {self.area_cm2:.2f} cm²)"


def rebar_sets_total_area(sets: List[RebarSet]) -> float:
    """Aire totale d'une liste de RebarSet (mm²)."""
    return sum(s.area for s in sets)


def rebar_sets_label(sets: List[RebarSet]) -> str:
    """Label combiné : ex '2HA12+2HA10'."""
    return "+".join(s.label for s in sets)


def rebar_sets_phi_max(sets: List[RebarSet]) -> int:
    """Diamètre max d'une liste de RebarSet (mm)."""
    if not sets:
        return 0
    return max(s.phi for s in sets)


# =============================================================================
# Classe SecMatRC
# =============================================================================

class SecMatRC:
    """
    Conteneur section-matériau pour le béton armé.

    Stocke les données géométriques liées au matériau (d, d', enrobages,
    armatures, inerties homogènes et fissurées) qui dépendent à la fois
    de la section et du matériau.

    Les armatures peuvent être renseignées de deux façons :
        - Par section directe : rc.ast = 6.28  (cm²)
        - Par description de barres : rc.rebars_bottom = [RebarSet(2,12), RebarSet(2,10)]
        → L'aire est alors calculée automatiquement.
        → Si les deux sont renseignés, les RebarSet priment.

    :param sec: Section géométrique
    :param mat_concrete: Matériau béton (MatConcrete)
    :param mat_reinforcement: Matériau acier d'armature (MatReinforcement)
    :param phi_fluage: Coefficient de fluage φ(∞,t0) (défaut None)
    :param name: Nom optionnel
    """

    def __init__(
        self,
        sec: section,
        mat_concrete: material_concrete,
        mat_reinforcement: material_reinforcement,
        phi_fluage: Optional[float] = 3,
        name: Optional[str] = None,
    ) -> None:

        # --- Références aux objets de base ---
        self._sec = sec
        self._mat_c = mat_concrete
        self._mat_s = mat_reinforcement
        self._name = name or f"RC_{sec.__class__.__name__}"

        # --- Géométrie de base ---
        self._h: float = sec.h
        self._d: Optional[float] = 0.9 * self._h     # estimation initiale
        self._d_prime: Optional[float] = 0.1 * self._h

        # --- Enrobages et diamètres ---
        self._cnom: Optional[float] = None          # mm, enrobage nominal
        self._cnom_top: Optional[float] = None      # mm, enrobage nominal sup (si différent)
        self._cnom_left: Optional[float] = None      # mm, enrobage nominal gauche (si différent)
        self._cnom_right: Optional[float] = None      # mm, enrobage nominal droite (si différent)
        self._phi_l: Optional[int] = None           # mm, diamètre armatures longitudinales
        self._phi_t: Optional[int] = None           # mm, diamètre armatures transversales

        # --- Classe d'exposition et structurale ---
        self._exposure_class: Optional[str] = None  # ex: "XC3"
        self._structural_class: str = "S4"          # par défaut : 50 ans

        # --- Armatures tendues (bottom) ---
        self._ast: Optional[float] = None           # cm², section d'acier tendu
        self._rebars_bottom: Optional[List[RebarSet]] = None

        # --- Armatures comprimées (top) ---
        self._asc: Optional[float] = None           # cm², section d'acier comprimé
        self._rebars_top: Optional[List[RebarSet]] = None

        # --- Espacement ---
        self._eh: Optional[float] = None            # mm, espacement horizontal
        self._ev: Optional[float] = None            # mm, espacement vertical

        # --- Bras de levier ---
        self._z: Optional[float] = None             # mm

        # --- Fluage ---
        self._phi_fluage: Optional[float] = phi_fluage

        # --- Cache inerties ---
        self._cache_valid: bool = False
        self._Ih: Optional[float] = None    # mm⁴, inertie homogénéisée
        self._Ic: Optional[float] = None    # mm⁴, inertie fissurée
        self._xh: Optional[float] = None    # mm, AN section homogénéisée
        self._xc: Optional[float] = None    # mm, AN section fissurée

    # =================================================================
    # Propriétés de base (lecture seule)
    # =================================================================

    @property
    def sec(self):
        """Section géométrique."""
        return self._sec

    @property
    def mat_concrete(self):
        """Matériau béton."""
        return self._mat_c

    @property
    def mat_reinforcement(self):
        """Matériau acier d'armature."""
        return self._mat_s

    @property
    def name(self) -> str:
        return self._name

    @property
    def h(self) -> float:
        return self._h

    # =================================================================
    # Hauteur utile d et d'
    # =================================================================

    @property
    def d(self) -> Optional[float]:
        """Hauteur utile des armatures tendues (mm)."""
        return self._d

    @d.setter
    def d(self, value: float) -> None:
        if value <= 0 or value > self._h:
            raise ValueError(f"d={value} doit être dans ]0, h={self._h}]")
        self._d = value
        self._invalidate_cache()

    @property
    def d_prime(self) -> Optional[float]:
        """Distance du centre des armatures comprimées au parement (mm)."""
        return self._d_prime

    @d_prime.setter
    def d_prime(self, value: float) -> None:
        if value < 0 or value > self._h:
            raise ValueError(f"d'={value} doit être dans [0, h={self._h}]")
        self._d_prime = value
        self._invalidate_cache()

    # =================================================================
    # Enrobages et diamètres
    # =================================================================

    @property
    def cnom(self) -> Optional[float]:
        """Enrobage nominal côté tendu (mm)."""
        return self._cnom

    @cnom.setter
    def cnom(self, value: float) -> None:
        self._cnom = value

    @property
    def cnom_top(self) -> Optional[float]:
        """Enrobage nominal côté comprimé (mm). Si None, utilise cnom."""
        return self._cnom_top

    @cnom_top.setter
    def cnom_top(self, value: float) -> None:
        self._cnom_top = value

    @property
    def cnom_left(self) -> Optional[float]:
        """Enrobage nominal côté comprimé (mm). Si None, utilise cnom."""
        return self._cnom_left

    @cnom_left.setter
    def cnom_left(self, value: float) -> None:
        self._cnom_left = value

    @property
    def cnom_right(self) -> Optional[float]:
        """Enrobage nominal côté comprimé (mm). Si None, utilise cnom."""
        return self._cnom_right

    @cnom_right.setter
    def cnom_right(self, value: float) -> None:
        self._cnom_right = value

    @property
    def phi_l(self) -> Optional[int]:
        """Diamètre des armatures longitudinales (mm)."""
        return self._phi_l

    @phi_l.setter
    def phi_l(self, value: int) -> None:
        self._phi_l = value

    @property
    def phi_t(self) -> Optional[int]:
        """Diamètre des armatures transversales (mm)."""
        return self._phi_t

    @phi_t.setter
    def phi_t(self, value: int) -> None:
        self._phi_t = value

    # =================================================================
    # Classe d'exposition et structurale
    # =================================================================

    @property
    def exposure_class(self) -> Optional[str]:
        """Classe d'exposition EC2 (ex: 'XC3')."""
        return self._exposure_class

    @exposure_class.setter
    def exposure_class(self, value: str) -> None:
        value = value.upper()
        if value not in EXPOSURE_CLASSES:
            raise ValueError(
                f"Classe d'exposition '{value}' inconnue. "
                f"Disponibles : {list(EXPOSURE_CLASSES.keys())}"
            )
        self._exposure_class = value

    @property
    def structural_class(self) -> str:
        """Classe structurale EC2 (ex: 'S4')."""
        return self._structural_class

    @structural_class.setter
    def structural_class(self, value: str) -> None:
        value = value.upper()
        if value not in STRUCTURAL_CLASSES:
            raise ValueError(
                f"Classe structurale '{value}' inconnue. "
                f"Disponibles : {list(STRUCTURAL_CLASSES.keys())}"
            )
        self._structural_class = value

    # Enrobage not implemented yet, but can be added similarly to cnom and cnom_top if needed.

    # =================================================================
    # Armatures : double mode (section directe ou RebarSet)
    # =================================================================

    # --- Bottom (tendues) ---

    @property
    def rebars_bottom(self) -> Optional[List[RebarSet]]:
        """Liste de RebarSet pour les armatures tendues."""
        return self._rebars_bottom

    @rebars_bottom.setter
    def rebars_bottom(self, sets: List[RebarSet]) -> None:
        self._rebars_bottom = sets
        self._invalidate_cache()

    @property
    def ast(self) -> Optional[float]:
        """
        Section d'acier tendu (cm²).

        Si des RebarSet sont définis, l'aire est calculée automatiquement.
        Sinon, renvoie la valeur stockée manuellement.
        """
        if self._rebars_bottom:
            return rebar_sets_total_area(self._rebars_bottom) / 100.0
        return self._ast

    @ast.setter
    def ast(self, value: float) -> None:
        """
        Renseigne l'aire d'acier tendu manuellement (cm²).

        Note : si des RebarSet sont déjà définis, ils priment sur cette valeur.
        Pour forcer la valeur manuelle, supprimer les RebarSet :
            rc.rebars_bottom = None
        """
        if value < 0:
            raise ValueError("ast doit être ≥ 0")
        self._ast = value
        self._invalidate_cache()

    @property
    def ast_mm2(self) -> Optional[float]:
        """Section d'acier tendu (mm²)."""
        a = self.ast
        return a * 100.0 if a is not None else None

    @property
    def rebars_bottom_label(self) -> Optional[str]:
        """Label des armatures tendues : ex '2HA12+2HA10'."""
        if self._rebars_bottom:
            return rebar_sets_label(self._rebars_bottom)
        return None

    # --- Top (comprimées) ---

    @property
    def rebars_top(self) -> Optional[List[RebarSet]]:
        """Liste de RebarSet pour les armatures comprimées."""
        return self._rebars_top

    @rebars_top.setter
    def rebars_top(self, sets: List[RebarSet]) -> None:
        self._rebars_top = sets
        self._invalidate_cache()

    @property
    def asc(self) -> Optional[float]:
        """
        Section d'acier comprimé (cm²).

        Si des RebarSet sont définis, l'aire est calculée automatiquement.
        Sinon, renvoie la valeur stockée manuellement.
        """
        if self._rebars_top:
            return rebar_sets_total_area(self._rebars_top) / 100.0
        return self._asc

    @asc.setter
    def asc(self, value: float) -> None:
        if value < 0:
            raise ValueError("asc doit être ≥ 0")
        self._asc = value
        self._invalidate_cache()

    @property
    def asc_mm2(self) -> Optional[float]:
        """Section d'acier comprimé (mm²)."""
        a = self.asc
        return a * 100.0 if a is not None else None

    @property
    def rebars_top_label(self) -> Optional[str]:
        """Label des armatures comprimées : ex '2HA12'."""
        if self._rebars_top:
            return rebar_sets_label(self._rebars_top)
        return None

    # =================================================================
    # Espacement
    # =================================================================

    @property
    def eh(self) -> Optional[float]:
        """Espacement horizontal entre barres (mm)."""
        return self._eh

    @eh.setter
    def eh(self, value: float) -> None:
        self._eh = value

    @property
    def ev(self) -> Optional[float]:
        """Espacement vertical entre lits (mm)."""
        return self._ev

    @ev.setter
    def ev(self, value: float) -> None:
        self._ev = value

    # =================================================================
    # Bras de levier
    # =================================================================

    @property
    def z(self) -> Optional[float]:
        """Bras de levier z (mm)."""
        return self._z

    @z.setter
    def z(self, value: float) -> None:
        self._z = value

    # =================================================================
    # Fluage et coefficient d'équivalence
    # =================================================================

    @property
    def phi_fluage(self) -> Optional[float]:
        """Coefficient de fluage φ(∞,t0)."""
        return self._phi_fluage

    @phi_fluage.setter
    def phi_fluage(self, value: float) -> None:
        self._phi_fluage = value
        self._invalidate_cache()

    @property
    def alpha_eq_short(self) -> float:
        """
        Coefficient d'équivalence court terme : αe = Es / Ecm.
        Ref: EC2 §5.4(2)
        """
        return self._mat_s.Es / self._mat_c.Ecm

    @property
    def alpha_eq_long(self) -> Optional[float]:
        """
        Coefficient d'équivalence long terme : αe,lt = Es / (Ecm / (1 + φ)).
        Ref: EC2 §5.4(2)
        Retourne None si phi_fluage non renseigné.
        """
        if self._phi_fluage is None:
            return None
        Ec_eff = self._mat_c.Ecm / (1.0 + self._phi_fluage)
        return self._mat_s.Es / Ec_eff

    def get_alpha_eq_short(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour αe — EC2 §5.4(2)."""
        r = self.alpha_eq_short
        fv = ""
        if with_values:
            fv = (f"αe = Es / Ecm = {self._mat_s.Es:.0f} / "
                f"{self._mat_c.Ecm:.0f} = {r:.2f}")
        return FormulaResult(
            name="αe",
            formula="αe = Es / Ecm",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 — §5.4(2)",
        )

    def get_alpha_eq_long(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour αe,lt — EC2 §5.4(2)."""
        r = self.alpha_eq_long  # None si phi absent
        fv = ""
        if with_values and r is not None:
            Ec_eff = self._mat_c.Ecm / (1.0 + self._phi_fluage)
            fv = (f"αe,lt = Es / (Ecm / (1+φ)) = {self._mat_s.Es:.0f} / "
                f"({self._mat_c.Ecm:.0f} / (1+{self._phi_fluage:.2f})) "
                f"= {self._mat_s.Es:.0f} / {Ec_eff:.0f} = {r:.2f}")
        return FormulaResult(
            name="αe,lt",
            formula="αe,lt = Es / (Ecm / (1 + φ))",
            formula_values=fv,
            result=r if r is not None else float('nan'),
            unit="-",
            ref="EC2 — §5.4(2)",
        )

    def report_equivalence(self, with_values: bool = True) -> FormulaCollection:
        """FormulaCollection — coefficients d'équivalence."""
        fc = FormulaCollection(
            title="Coefficients d'équivalence acier/béton",
            ref="EC2 — §5.4(2)",
        )
        fc.add(self.get_alpha_eq_short(with_values=with_values))
        if self._phi_fluage is not None:
            fc.add(self.get_alpha_eq_long(with_values=with_values))
        return fc


    # =================================================================
    # Compute d from covers
    # =================================================================

    def compute_d_from_covers(self, side: str = "bottom") -> float:
        """
        Calcule la hauteur utile à partir de l'enrobage et des diamètres.

            d = h - cnom - φt - φl/2        (armatures tendues)
            d'= cnom_top + φt + φl/2        (armatures comprimées)

        Si les RebarSet sont définis, φl est pris comme le diamètre max
        du jeu de barres correspondant.

        :param side: "bottom" → calcule d, "top" → calcule d',
                     "both" → calcule les deux
        :return: d ou d' calculé (si "both", retourne d)
        :raises ValueError: si données manquantes
        """
        missing = self._missing_for_compute_d(side)
        if missing:
            raise ValueError(
                f"Données manquantes pour compute_d('{side}') : {missing}"
            )

        phi_t = self._phi_t

        if side in ("bottom", "both"):
            phi_l_bot = self._get_phi_l_bottom()
            cnom_bot = self._cnom
            self._d = self._h - cnom_bot - phi_t - phi_l_bot / 2.0
            self._invalidate_cache()

        if side in ("top", "both"):
            phi_l_top = self._get_phi_l_top()
            cnom_t = self._cnom_top if self._cnom_top is not None else self._cnom
            self._d_prime = cnom_t + phi_t + phi_l_top / 2.0
            self._invalidate_cache()

        if side == "top":
            return self._d_prime
        return self._d

    def _get_phi_l_bottom(self) -> float:
        """Diamètre longitudinal côté tendu : RebarSet max ou phi_l."""
        if self._rebars_bottom:
            return rebar_sets_phi_max(self._rebars_bottom)
        if self._phi_l is not None:
            return self._phi_l
        return 0

    def _get_phi_l_top(self) -> float:
        """Diamètre longitudinal côté comprimé : RebarSet max ou phi_l."""
        if self._rebars_top:
            return rebar_sets_phi_max(self._rebars_top)
        if self._phi_l is not None:
            return self._phi_l
        return 0

    def _missing_for_compute_d(self, side: str) -> List[str]:
        """Liste les données manquantes pour compute_d."""
        missing = []
        if self._phi_t is None:
            missing.append("phi_t")

        if side in ("bottom", "both"):
            if self._cnom is None:
                missing.append("cnom")
            if self._rebars_bottom is None and self._phi_l is None:
                missing.append("phi_l ou rebars_bottom")

        if side in ("top", "both"):
            if self._cnom is None and self._cnom_top is None:
                missing.append("cnom ou cnom_top")
            if self._rebars_top is None and self._phi_l is None:
                missing.append("phi_l ou rebars_top")

        return missing

    def get_compute_d_formula(self, with_values: bool = False) -> str:
        if with_values and self._d is not None:
            phi_l = self._get_phi_l_bottom()
            return (f"d = h - cnom - φt - φl/2 = {self._h:.0f} - "
                    f"{self._cnom:.0f} - {self._phi_t:.0f} - "
                    f"{phi_l:.0f}/2 = {self._d:.1f} mm")
        return "d = h - cnom - φt - φl/2"

    @property
    def compute_d_ref(self) -> str:
        return "EC2 — §4.4.1"

    # =================================================================
    # Inerties (sections rectangulaires uniquement)
    # =================================================================

    @property
    def missing_for_inertia(self) -> List[str]:
        """Liste les paramètres manquants pour calculer Ih et Ic."""
        missing = []
        if self.ast is None:
            missing.append("ast (ou rebars_bottom)")
        if self._d is None:
            missing.append("d")
        # b requis
        if not hasattr(self._sec, 'b'):
            missing.append("sec.b (section non rectangulaire)")
        return missing

    def _compute_inertia(self, alpha_eq: float) -> None:
        """
        Calcule les inerties homogénéisée et fissurée (section rectangulaire).

        :param alpha_eq: coefficient d'équivalence à utiliser
        """
        b = self._sec.b
        h = self._h
        d = self._d
        Ast = self.ast_mm2 or 0.0
        Asc = self.asc_mm2 or 0.0
        d_p = self._d_prime or 0.0

        # --- Section homogénéisée ---
        # Aire homogénéisée
        Ah = b * h + (alpha_eq - 1) * (Ast + Asc)
        # Position AN depuis le haut
        Sh = (b * h * h / 2.0
              + (alpha_eq - 1) * Ast * d
              + (alpha_eq - 1) * Asc * d_p)
        self._xh = Sh / Ah
        # Inertie
        self._Ih = (b * h ** 3 / 12.0
                    + b * h * (self._xh - h / 2.0) ** 2
                    + (alpha_eq - 1) * Ast * (d - self._xh) ** 2
                    + (alpha_eq - 1) * Asc * (self._xh - d_p) ** 2)

        # --- Section fissurée (béton tendu négligé) ---
        # Equation du 2nd degré : b·x²/2 + (αe-1)·Asc·(x-d') = αe·Ast·(d-x)
        # → b/2·x² + [(αe-1)·Asc + αe·Ast]·x - [(αe-1)·Asc·d' + αe·Ast·d] = 0
        a_coef = b / 2.0
        b_coef = (alpha_eq - 1) * Asc + alpha_eq * Ast
        c_coef = -((alpha_eq - 1) * Asc * d_p + alpha_eq * Ast * d)

        delta = b_coef ** 2 - 4 * a_coef * c_coef
        self._xc = (-b_coef + math.sqrt(delta)) / (2 * a_coef)

        self._Ic = (b * self._xc ** 3 / 3.0
                    + (alpha_eq - 1) * Asc * (self._xc - d_p) ** 2
                    + alpha_eq * Ast * (d - self._xc) ** 2)

        self._cache_valid = True

    def _ensure_cache(self, alpha_eq: Optional[float] = None) -> None:
        """Recalcule le cache si nécessaire."""
        if self._cache_valid:
            return
        if self.missing_for_inertia:
            return
        ae = alpha_eq or self.alpha_eq_short
        self._compute_inertia(ae)

    def _invalidate_cache(self) -> None:
        self._cache_valid = False
        self._Ih = None
        self._Ic = None
        self._xh = None
        self._xc = None

    @property
    def Ih(self) -> Optional[float]:
        """Inertie de la section homogénéisée (mm⁴). None si données manquantes."""
        self._ensure_cache()
        return self._Ih

    @property
    def Ic(self) -> Optional[float]:
        """Inertie de la section fissurée (mm⁴). None si données manquantes."""
        self._ensure_cache()
        return self._Ic

    @property
    def xh(self) -> Optional[float]:
        """Position de l'AN — section homogénéisée (mm depuis le haut)."""
        self._ensure_cache()
        return self._xh

    @property
    def xc(self) -> Optional[float]:
        """Position de l'AN — section fissurée (mm depuis le haut)."""
        self._ensure_cache()
        return self._xc

    # =================================================================
    # Utilitaires de consultation des tableaux réglementaires
    # =================================================================

    @staticmethod
    def print_exposure_classes() -> None:
        """Affiche toutes les classes d'exposition avec description."""
        print(f"\n{'='*80}")
        print(f"  CLASSES D'EXPOSITION — EC2 Tableau 4.1")
        print(f"{'='*80}")
        for cls, info in EXPOSURE_CLASSES.items():
            print(f"\n  {cls:4s}  │ {info['risk']}")
            print(f"        │ {info['description']}")
            print(f"        │ Ex: {info['examples']}")
        print(f"\n{'='*80}\n")

    @staticmethod
    def print_structural_classes() -> None:
        """Affiche toutes les classes structurales avec description."""
        print(f"\n{'='*70}")
        print(f"  CLASSES STRUCTURALES — EC2 §4.4.1.2")
        print(f"{'='*70}")
        for cls, info in STRUCTURAL_CLASSES.items():
            print(f"\n  {cls:3s}  │ Durée : {info['lifetime']}")
            print(f"       │ {info['description']}")
            print(f"       │ Ex: {info['examples']}")
        print(f"\n{'='*70}\n")

    @staticmethod
    def print_rebar_areas() -> None:
        """Affiche le tableau des aires unitaires des barres HA."""
        print(f"\n{'='*50}")
        print(f"  AIRES UNITAIRES DES BARRES HA (mm²)")
        print(f"{'='*50}")
        for phi, area in REBAR_AREAS.items():
            print(f"  HA{phi:<3d} │ {area:>8.2f} mm²  ({area/100:.2f} cm²)")
        print(f"{'='*50}\n")

    # =================================================================
    # Summary et affichage
    # =================================================================

    def summary(self) -> dict:
        """Retourne un dictionnaire de toutes les données stockées."""
        return {
            "name": self._name,
            "h": self._h,
            "d": self._d,
            "d_prime": self._d_prime,
            "cnom": self._cnom,
            "cnom_top": self._cnom_top,
            "phi_l": self._phi_l,
            "phi_t": self._phi_t,
            "exposure_class": self._exposure_class,
            "structural_class": self._structural_class,
            "cmin_dur": self.cmin_dur,
            "ast (cm²)": self.ast,
            "rebars_bottom": self.rebars_bottom_label,
            "asc (cm²)": self.asc,
            "rebars_top": self.rebars_top_label,
            "eh": self._eh,
            "ev": self._ev,
            "z": self._z,
            "phi_fluage": self._phi_fluage,
            "alpha_eq_short": round(self.alpha_eq_short, 2),
            "alpha_eq_long": (round(self.alpha_eq_long, 2)
                              if self.alpha_eq_long is not None else None),
            "xh": self.xh,
            "xc": self.xc,
            "Ih (mm⁴)": self.Ih,
            "Ic (mm⁴)": self.Ic,
        }

    def __str__(self) -> str:
        lines = [
            f"\n{'=' * 70}",
            f"  {self._name}",
            f"  Section : {self._sec.__class__.__name__} | "
            f"Béton : fck={self._mat_c.fck:.0f} MPa | "
            f"Acier : fyk={self._mat_s.fyk:.0f} MPa",
            f"{'=' * 70}",
            "",
        ]

        data = self.summary()
        for key, val in data.items():
            if key == "name":
                continue
            status = "✓" if val is not None else "—"
            val_str = f"{val}" if val is not None else "non renseigné"
            lines.append(f"  {status}  {key:20s} = {val_str}")

        missing = self.missing_for_inertia
        if missing:
            lines.append(f"\n  ⚠ Manquant pour inertie : {missing}")

        lines.append(f"\n{'=' * 70}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (f"SecMatRC(name='{self._name}', h={self._h}, "
                f"d={self._d}, ast={self.ast}, asc={self.asc})")


# =============================================================================
# Main — Démonstration
# =============================================================================

if __name__ == "__main__":

    # --- Affichage des tableaux ---
    SecMatRC.print_exposure_classes()
    SecMatRC.print_structural_classes()
    SecMatRC.print_rebar_areas()

    # --- Simulation sans imports réels ---
    class FakeSec:
        h = 500
        b = 300
        def __class_name__(self): return "Rectangular"

    class FakeConcrete:
        fck = 30
        Ecm = 33000

    class FakeReinf:
        fyk = 500
        Es = 200000

    sec = FakeSec()
    beton = FakeConcrete()
    acier = FakeReinf()

    rc = SecMatRC(sec=sec, mat_concrete=beton, mat_reinforcement=acier)
    print(rc)
    print("Missing pour inertie :", rc.missing_for_inertia)

    # --- Mode 1 : section directe ---
    print("\n--- Mode 1 : Ast en cm² ---")
    rc.ast = 6.28
    rc.asc = 2.26
    rc.cnom = 30
    rc.phi_l = 20
    rc.phi_t = 8
    rc.compute_d_from_covers("both")
    print(rc.get_compute_d_formula(with_values=True))
    print(rc)

    # --- Mode 2 : par RebarSet ---
    print("\n--- Mode 2 : RebarSet ---")
    rc2 = SecMatRC(sec=sec, mat_concrete=beton, mat_reinforcement=acier,
                   phi_fluage=2.5, name="Poutre_B2")

    rc2.rebars_bottom = [RebarSet(2, 12), RebarSet(2, 10)]
    rc2.rebars_top = [RebarSet(2, 10)]
    rc2.cnom = 30
    rc2.phi_t = 8
    rc2.exposure_class = "XC3"
    rc2.structural_class = "S4"

    # phi_l est déduit des RebarSet automatiquement
    rc2.compute_d_from_covers("both")

    print(f"Armatures tendues  : {rc2.rebars_bottom_label} = {rc2.ast:.2f} cm²")
    print(f"Armatures comprimées : {rc2.rebars_top_label} = {rc2.asc:.2f} cm²")
    print(f"cmin,dur = {rc2.cmin_dur} mm")
    print(f"αe court terme = {rc2.alpha_eq_short:.2f}")
    print(f"αe long terme  = {rc2.alpha_eq_long:.2f}")
    print(rc2)
