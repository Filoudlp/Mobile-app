#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define timber material properties according to EC5.

    References:
        - EN 1995-1-1 (Eurocode 5) — §2.4.1, §2.3.2, §3.2, §3.3, §3.4
        - EN 338 — Table 1 (classes de résistance bois massif)
        - EN 14080 — Table 5 (classes de résistance lamellé-collé)

    Supported National Annexes:
        - FR : France (default)
        - BE : Belgique
        - UK : Royaume-Uni

    Supported timber types:
        - "solid"  : Bois massif (EN 338)
        - "glulam" : Lamellé-collé (EN 14080)
"""

__all__ = ['MatTimber', 'TimberCoefficients']

from dataclasses import dataclass
from typing import Optional

from .material import Material
from .formula import FormulaResult


# =============================================================================
# Coefficients nationaux — EC5 §2.4.1
# =============================================================================

@dataclass
class TimberCoefficients:
    """
    Coefficients partiels de sécurité pour le bois
    selon l'Annexe Nationale — EC5 §2.4.1.

    :param gamma_m: Coefficient partiel bois massif [-]
    :param gamma_m_glulam: Coefficient partiel lamellé-collé [-]
    :param gamma_m_acc: Coefficient partiel situation accidentelle [-]
    :param country: Code pays
    """
    gamma_m: float = 1.30
    gamma_m_glulam: float = 1.25
    gamma_m_acc: float = 1.00
    country: str = "FR"


_NATIONAL_ANNEX_REGISTRY: dict[str, TimberCoefficients] = {
    "FR": TimberCoefficients(gamma_m=1.30, gamma_m_glulam=1.25, gamma_m_acc=1.00, country="FR"),
    "BE": TimberCoefficients(gamma_m=1.30, gamma_m_glulam=1.25, gamma_m_acc=1.00, country="BE"),
    "UK": TimberCoefficients(gamma_m=1.30, gamma_m_glulam=1.25, gamma_m_acc=1.00, country="UK"),
}


# =============================================================================
# Facteur kmod — EC5 §3.1.3 Table 3.1
# =============================================================================

@dataclass
class _KmodEntry:
    """
    Facteur de modification kmod selon la classe de service
    et la classe de durée de charge — EC5 Table 3.1.

    Clé : (timber_type, service_class, load_duration_class)
    """
    pass


# timber_type : "solid" ou "glulam"
# service_class : 1, 2 ou 3
# load_duration_class : "permanent", "long_term", "medium_term", "short_term", "instantaneous"

_KMOD: dict[tuple[str, int, str], float] = {
    # --- Bois massif (EN 338) ---
    ("solid", 1, "permanent"):     0.60,
    ("solid", 1, "long_term"):     0.70,
    ("solid", 1, "medium_term"):   0.80,
    ("solid", 1, "short_term"):    0.90,
    ("solid", 1, "instantaneous"): 1.10,
    ("solid", 2, "permanent"):     0.60,
    ("solid", 2, "long_term"):     0.70,
    ("solid", 2, "medium_term"):   0.80,
    ("solid", 2, "short_term"):    0.90,
    ("solid", 2, "instantaneous"): 1.10,
    ("solid", 3, "permanent"):     0.50,
    ("solid", 3, "long_term"):     0.55,
    ("solid", 3, "medium_term"):   0.65,
    ("solid", 3, "short_term"):    0.70,
    ("solid", 3, "instantaneous"): 0.90,
    # --- Lamellé-collé (EN 14080) ---
    ("glulam", 1, "permanent"):     0.60,
    ("glulam", 1, "long_term"):     0.70,
    ("glulam", 1, "medium_term"):   0.80,
    ("glulam", 1, "short_term"):    0.90,
    ("glulam", 1, "instantaneous"): 1.10,
    ("glulam", 2, "permanent"):     0.60,
    ("glulam", 2, "long_term"):     0.70,
    ("glulam", 2, "medium_term"):   0.80,
    ("glulam", 2, "short_term"):    0.90,
    ("glulam", 2, "instantaneous"): 1.10,
    ("glulam", 3, "permanent"):     0.50,
    ("glulam", 3, "long_term"):     0.55,
    ("glulam", 3, "medium_term"):   0.65,
    ("glulam", 3, "short_term"):    0.70,
    ("glulam", 3, "instantaneous"): 0.90,
}


# =============================================================================
# Facteur kdef — EC5 §3.1.4 Table 3.2
# =============================================================================

_KDEF: dict[tuple[str, int], float] = {
    ("solid", 1):  0.60,
    ("solid", 2):  0.80,
    ("solid", 3):  2.00,
    ("glulam", 1): 0.60,
    ("glulam", 2): 0.80,
    ("glulam", 3): 2.00,
}


# =============================================================================
# Classes de résistance — EN 338 Table 1 (bois massif)
# =============================================================================

@dataclass
class _TimberGradeData:
    """
    Propriétés caractéristiques d'une classe de résistance.

    Résistances en MPa, module en MPa, masse volumique en kg/m³.

    :param fm_k: Résistance caractéristique en flexion [MPa]
    :param ft_0_k: Résistance caractéristique en traction parallèle [MPa]
    :param ft_90_k: Résistance caractéristique en traction perpendiculaire [MPa]
    :param fc_0_k: Résistance caractéristique en compression parallèle [MPa]
    :param fc_90_k: Résistance caractéristique en compression perpendiculaire [MPa]
    :param fv_k: Résistance caractéristique au cisaillement [MPa]
    :param E_0_mean: Module d'élasticité moyen parallèle [MPa]
    :param E_0_05: Module d'élasticité 5ème percentile parallèle [MPa]
    :param E_90_mean: Module d'élasticité moyen perpendiculaire [MPa]
    :param G_mean: Module de cisaillement moyen [MPa]
    :param rho_k: Masse volumique caractéristique [kg/m³]
    :param rho_mean: Masse volumique moyenne [kg/m³]
    """
    fm_k: float
    ft_0_k: float
    ft_90_k: float
    fc_0_k: float
    fc_90_k: float
    fv_k: float
    E_0_mean: float
    E_0_05: float
    E_90_mean: float
    G_mean: float
    rho_k: float
    rho_mean: float


# --- Bois massif résineux — EN 338 Table 1 ---
_SOLID_GRADES: dict[str, _TimberGradeData] = {
    "C14": _TimberGradeData(
        fm_k=14, ft_0_k=7.2, ft_90_k=0.4, fc_0_k=16, fc_90_k=2.0, fv_k=3.0,
        E_0_mean=7000, E_0_05=4700, E_90_mean=230, G_mean=440,
        rho_k=290, rho_mean=350,
    ),
    "C16": _TimberGradeData(
        fm_k=16, ft_0_k=8.5, ft_90_k=0.4, fc_0_k=17, fc_90_k=2.2, fv_k=3.2,
        E_0_mean=8000, E_0_05=5400, E_90_mean=270, G_mean=500,
        rho_k=310, rho_mean=370,
    ),
    "C18": _TimberGradeData(
        fm_k=18, ft_0_k=10, ft_90_k=0.4, fc_0_k=18, fc_90_k=2.2, fv_k=3.4,
        E_0_mean=9000, E_0_05=6000, E_90_mean=300, G_mean=560,
        rho_k=320, rho_mean=380,
    ),
    "C22": _TimberGradeData(
        fm_k=22, ft_0_k=13, ft_90_k=0.4, fc_0_k=20, fc_90_k=2.4, fv_k=3.8,
        E_0_mean=10000, E_0_05=6700, E_90_mean=330, G_mean=630,
        rho_k=340, rho_mean=410,
    ),
    "C24": _TimberGradeData(
        fm_k=24, ft_0_k=14.5, ft_90_k=0.4, fc_0_k=21, fc_90_k=2.5, fv_k=4.0,
        E_0_mean=11000, E_0_05=7400, E_90_mean=370, G_mean=690,
        rho_k=350, rho_mean=420,
    ),
    "C27": _TimberGradeData(
        fm_k=27, ft_0_k=16.5, ft_90_k=0.4, fc_0_k=22, fc_90_k=2.6, fv_k=4.0,
        E_0_mean=11500, E_0_05=7700, E_90_mean=380, G_mean=720,
        rho_k=370, rho_mean=450,
    ),
    "C30": _TimberGradeData(
        fm_k=30, ft_0_k=19, ft_90_k=0.4, fc_0_k=24, fc_90_k=2.7, fv_k=4.0,
        E_0_mean=12000, E_0_05=8000, E_90_mean=400, G_mean=750,
        rho_k=380, rho_mean=460,
    ),
    "C35": _TimberGradeData(
        fm_k=35, ft_0_k=22.5, ft_90_k=0.4, fc_0_k=25, fc_90_k=2.8, fv_k=4.0,
        E_0_mean=13000, E_0_05=8700, E_90_mean=430, G_mean=810,
        rho_k=400, rho_mean=480,
    ),
    "C40": _TimberGradeData(
        fm_k=40, ft_0_k=26, ft_90_k=0.4, fc_0_k=27, fc_90_k=2.9, fv_k=4.0,
        E_0_mean=14000, E_0_05=9400, E_90_mean=470, G_mean=880,
        rho_k=420, rho_mean=500,
    ),
    "C45": _TimberGradeData(
        fm_k=45, ft_0_k=30, ft_90_k=0.4, fc_0_k=29, fc_90_k=3.1, fv_k=4.0,
        E_0_mean=15000, E_0_05=10000, E_90_mean=500, G_mean=940,
        rho_k=440, rho_mean=520,
    ),
    "C50": _TimberGradeData(
        fm_k=50, ft_0_k=33, ft_90_k=0.4, fc_0_k=30, fc_90_k=3.2, fv_k=4.0,
        E_0_mean=16000, E_0_05=10700, E_90_mean=530, G_mean=1000,
        rho_k=460, rho_mean=550,
    ),
}


# --- Lamellé-collé — EN 14080 Table 5 (homogène) ---
_GLULAM_GRADES: dict[str, _TimberGradeData] = {
    "GL20H": _TimberGradeData(
        fm_k=20, ft_0_k=16, ft_90_k=0.5, fc_0_k=20, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=8400, E_0_05=7000, E_90_mean=300, G_mean=650,
        rho_k=340, rho_mean=370,
    ),
    "GL22H": _TimberGradeData(
        fm_k=22, ft_0_k=17.6, ft_90_k=0.5, fc_0_k=22, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=10500, E_0_05=8800, E_90_mean=300, G_mean=650,
        rho_k=370, rho_mean=410,
    ),
    "GL24H": _TimberGradeData(
        fm_k=24, ft_0_k=19.2, ft_90_k=0.5, fc_0_k=24, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=11500, E_0_05=9600, E_90_mean=300, G_mean=650,
        rho_k=385, rho_mean=420,
    ),
    "GL26H": _TimberGradeData(
        fm_k=26, ft_0_k=20.8, ft_90_k=0.5, fc_0_k=26, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=12100, E_0_05=10100, E_90_mean=300, G_mean=650,
        rho_k=405, rho_mean=440,
    ),
    "GL28H": _TimberGradeData(
        fm_k=28, ft_0_k=22.4, ft_90_k=0.5, fc_0_k=28, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=12600, E_0_05=10500, E_90_mean=300, G_mean=650,
        rho_k=425, rho_mean=460,
    ),
    "GL30H": _TimberGradeData(
        fm_k=30, ft_0_k=24, ft_90_k=0.5, fc_0_k=30, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=13600, E_0_05=11300, E_90_mean=300, G_mean=650,
        rho_k=430, rho_mean=480,
    ),
    "GL32H": _TimberGradeData(
        fm_k=32, ft_0_k=25.6, ft_90_k=0.5, fc_0_k=32, fc_90_k=2.5, fv_k=3.5,
        E_0_mean=14200, E_0_05=11800, E_90_mean=300, G_mean=650,
        rho_k=440, rho_mean=490,
    ),
}

# Registre combiné
_ALL_GRADES: dict[str, dict[str, _TimberGradeData]] = {
    "solid": _SOLID_GRADES,
    "glulam": _GLULAM_GRADES,
}


# =============================================================================
# Classe principale
# =============================================================================

class MatTimber(Material):
    """
    Matériau bois selon EC5 / EN 338 / EN 14080.

    :param grade: Classe de résistance ("C24", "GL24H", etc.)
    :param timber_type: Type de bois ("solid" ou "glulam")
    :param service_class: Classe de service (1, 2 ou 3) — EC5 §2.3.1.3
    :param load_duration: Classe de durée de charge — EC5 §2.3.1.2
        ("permanent", "long_term", "medium_term", "short_term", "instantaneous")
    :param country: Code pays pour l'Annexe Nationale
    :param name: Nom libre
    """

    VALID_TIMBER_TYPES = ("solid", "glulam")
    VALID_SERVICE_CLASSES = (1, 2, 3)
    VALID_LOAD_DURATIONS = (
        "permanent", "long_term", "medium_term", "short_term", "instantaneous"
    )

    def __init__(
        self,
        grade: str,
        timber_type: str = "solid",
        service_class: int = 1,
        load_duration: str = "medium_term",
        country: str = "FR",
        name: Optional[str] = None,
    ) -> None:

        # --- Validation type de bois ---
        timber_type = timber_type.lower()
        if timber_type not in self.VALID_TIMBER_TYPES:
            raise ValueError(
                f"Type '{timber_type}' inconnu. "
                f"Types disponibles : {self.VALID_TIMBER_TYPES}"
            )
        self._timber_type = timber_type

        # --- Validation et résolution de la classe de résistance ---
        grade_upper = grade.upper()
        grade_registry = _ALL_GRADES[self._timber_type]
        if grade_upper not in grade_registry:
            raise ValueError(
                f"Classe '{grade}' inconnue pour type '{timber_type}'. "
                f"Classes disponibles : {list(grade_registry.keys())}"
            )
        self._grade = grade_upper
        self._data: _TimberGradeData = grade_registry[self._grade]

        # --- Validation classe de service ---
        if service_class not in self.VALID_SERVICE_CLASSES:
            raise ValueError(
                f"Classe de service '{service_class}' invalide. "
                f"Valeurs possibles : {self.VALID_SERVICE_CLASSES}"
            )
        self._service_class = service_class

        # --- Validation durée de charge ---
        load_duration = load_duration.lower()
        if load_duration not in self.VALID_LOAD_DURATIONS:
            raise ValueError(
                f"Durée de charge '{load_duration}' invalide. "
                f"Valeurs possibles : {self.VALID_LOAD_DURATIONS}"
            )
        self._load_duration = load_duration

        # --- AN ---
        self._country = country.upper()
        self._coefficients = self._get_coefficients(self._country)

        # --- Nom ---
        self._name = name or f"Bois {self._grade}"

        # --- Init parent ---
        super().__init__(
            name=self._name,
            E=self._data.E_0_mean,
            nu=0.0,  # non pertinent pour le bois, on utilise G directement
        )

    # =================================================================
    # Gestion Annexe Nationale
    # =================================================================

    @staticmethod
    def _get_coefficients(country: str) -> TimberCoefficients:
        if country not in _NATIONAL_ANNEX_REGISTRY:
            raise ValueError(
                f"AN '{country}' non supporté. "
                f"Disponibles : {list(_NATIONAL_ANNEX_REGISTRY.keys())}"
            )
        return _NATIONAL_ANNEX_REGISTRY[country]

    @property
    def country(self) -> str:
        return self._country

    @country.setter
    def country(self, value: str) -> None:
        self._country = value.upper()
        self._coefficients = self._get_coefficients(self._country)

    # =================================================================
    # Setters pour classe de service / durée de charge
    # =================================================================

    @property
    def service_class(self) -> int:
        return self._service_class

    @service_class.setter
    def service_class(self, value: int) -> None:
        if value not in self.VALID_SERVICE_CLASSES:
            raise ValueError(f"Classe de service invalide : {value}")
        self._service_class = value

    @property
    def load_duration(self) -> str:
        return self._load_duration

    @load_duration.setter
    def load_duration(self, value: str) -> None:
        value = value.lower()
        if value not in self.VALID_LOAD_DURATIONS:
            raise ValueError(f"Durée de charge invalide : {value}")
        self._load_duration = value

    @property
    def timber_type(self) -> str:
        return self._timber_type

    @property
    def grade(self) -> str:
        return self._grade

    # =================================================================
    # Propriétés caractéristiques — EN 338 / EN 14080
    # =================================================================

    @property
    def fm_k(self) -> float:
        """Résistance caractéristique en flexion [MPa]"""
        return self._data.fm_k

    @property
    def ft_0_k(self) -> float:
        """Résistance caractéristique en traction parallèle [MPa]"""
        return self._data.ft_0_k

    @property
    def ft_90_k(self) -> float:
        """Résistance caractéristique en traction perpendiculaire [MPa]"""
        return self._data.ft_90_k

    @property
    def fc_0_k(self) -> float:
        """Résistance caractéristique en compression parallèle [MPa]"""
        return self._data.fc_0_k

    @property
    def fc_90_k(self) -> float:
        """Résistance caractéristique en compression perpendiculaire [MPa]"""
        return self._data.fc_90_k

    @property
    def fv_k(self) -> float:
        """Résistance caractéristique au cisaillement [MPa]"""
        return self._data.fv_k

    @property
    def E_0_mean(self) -> float:
        """Module d'élasticité moyen parallèle [MPa]"""
        return self._data.E_0_mean

    @property
    def E_0_05(self) -> float:
        """Module d'élasticité 5ème percentile parallèle [MPa]"""
        return self._data.E_0_05

    @property
    def E_90_mean(self) -> float:
        """Module d'élasticité moyen perpendiculaire [MPa]"""
        return self._data.E_90_mean

    @property
    def G_mean(self) -> float:
        """Module de cisaillement moyen [MPa]"""
        return self._data.G_mean

    @property
    def rho_k(self) -> float:
        """Masse volumique caractéristique [kg/m³]"""
        return self._data.rho_k

    @property
    def rho_mean(self) -> float:
        """Masse volumique moyenne [kg/m³]"""
        return self._data.rho_mean

    # =================================================================
    # gamma_m — EC5 §2.4.1
    # =================================================================

    @property
    def gamma_m(self) -> float:
        """Coefficient partiel selon le type de bois — EC5 §2.4.1"""
        c = self._coefficients
        if self._timber_type == "glulam":
            return c.gamma_m_glulam
        return c.gamma_m

    @property
    def gamma_m_report(self) -> FormulaResult:
        return FormulaResult(
            name="γM",
            formula="γM — EC5 §2.4.1",
            formula_values=f"γM({self._timber_type}) = {self.gamma_m:.2f}",
            result=self.gamma_m,
            unit="-",
            ref=f"EC5 — §2.4.1 — AN {self._country}",
        )

    # =================================================================
    # kmod — EC5 §3.1.3 Table 3.1
    # =================================================================

    @property
    def kmod(self) -> float:
        """
        Facteur de modification kmod — EC5 Table 3.1.
        Dépend du type de bois, de la classe de service
        et de la classe de durée de charge.
        """
        key = (self._timber_type, self._service_class, self._load_duration)
        if key not in _KMOD:
            raise ValueError(
                f"Combinaison kmod introuvable : type={self._timber_type}, "
                f"SC={self._service_class}, durée={self._load_duration}"
            )
        return _KMOD[key]

    @property
    def kmod_report(self) -> FormulaResult:
        return FormulaResult(
            name="kmod",
            formula="kmod — EC5 Table 3.1",
            formula_values=(
                f"kmod({self._timber_type}, SC{self._service_class}, "
                f"{self._load_duration}) = {self.kmod:.2f}"
            ),
            result=self.kmod,
            unit="-",
            ref="EC5 — §3.1.3 — Table 3.1",
        )

    # =================================================================
    # kdef — EC5 §3.1.4 Table 3.2
    # =================================================================

    @property
    def kdef(self) -> float:
        """Facteur de déformation kdef — EC5 Table 3.2."""
        key = (self._timber_type, self._service_class)
        if key not in _KDEF:
            raise ValueError(
                f"Combinaison kdef introuvable : type={self._timber_type}, "
                f"SC={self._service_class}"
            )
        return _KDEF[key]

    @property
    def kdef_report(self) -> FormulaResult:
        return FormulaResult(
            name="kdef",
            formula="kdef — EC5 Table 3.2",
            formula_values=(
                f"kdef({self._timber_type}, SC{self._service_class}) = {self.kdef:.2f}"
            ),
            result=self.kdef,
            unit="-",
            ref="EC5 — §3.1.4 — Table 3.2",
        )

    # =================================================================
    # Résistances de calcul — EC5 §2.4.1 Eq. 2.17
    # f_d = kmod * f_k / γM
    # =================================================================

    def _fd(self, fk: float) -> float:
        """Calcul générique de la résistance de calcul."""
        return self.kmod * fk / self.gamma_m

    # ---- fm_d ----

    @property
    def fm_d(self) -> float:
        """Résistance de calcul en flexion [MPa]"""
        return self._fd(self._data.fm_k)

    @property
    def fm_d_report(self) -> FormulaResult:
        return FormulaResult(
            name="fm,d",
            formula="fm,d = kmod × fm,k / γM",
            formula_values=(
                f"fm,d = {self.kmod:.2f} × {self._data.fm_k:.2f} / "
                f"{self.gamma_m:.2f} = {self.fm_d:.2f}"
            ),
            result=self.fm_d,
            unit="MPa",
            ref="EC5 — §2.4.1 — Eq. 2.17",
        )

    # ---- ft_0_d ----

    @property
    def ft_0_d(self) -> float:
        """Résistance de calcul en traction parallèle [MPa]"""
        return self._fd(self._data.ft_0_k)

    @property
    def ft_0_d_report(self) -> FormulaResult:
        return FormulaResult(
            name="ft,0,d",
            formula="ft,0,d = kmod × ft,0,k / γM",
            formula_values=(
                f"ft,0,d = {self.kmod:.2f} × {self._data.ft_0_k:.2f} / "
                f"{self.gamma_m:.2f} = {self.ft_0_d:.2f}"
            ),
            result=self.ft_0_d,
            unit="MPa",
            ref="EC5 — §2.4.1 — Eq. 2.17",
        )

    # ---- ft_90_d ----

    @property
    def ft_90_d(self) -> float:
        """Résistance de calcul en traction perpendiculaire [MPa]"""
        return self._fd(self._data.ft_90_k)

    @property
    def ft_90_d_report(self) -> FormulaResult:
        return FormulaResult(
            name="ft,90,d",
            formula="ft,90,d = kmod × ft,90,k / γM",
            formula_values=(
                f"ft,90,d = {self.kmod:.2f} × {self._data.ft_90_k:.2f} / "
                f"{self.gamma_m:.2f} = {self.ft_90_d:.2f}"
            ),
            result=self.ft_90_d,
            unit="MPa",
            ref="EC5 — §2.4.1 — Eq. 2.17",
        )

    # ---- fc_0_d ----

    @property
    def fc_0_d(self) -> float:
        """Résistance de calcul en compression parallèle [MPa]"""
        return self._fd(self._data.fc_0_k)

    @property
    def fc_0_d_report(self) -> FormulaResult:
        return FormulaResult(
            name="fc,0,d",
            formula="fc,0,d = kmod × fc,0,k / γM",
            formula_values=(
                f"fc,0,d = {self.kmod:.2f} × {self._data.fc_0_k:.2f} / "
                f"{self.gamma_m:.2f} = {self.fc_0_d:.2f}"
            ),
            result=self.fc_0_d,
            unit="MPa",
            ref="EC5 — §2.4.1 — Eq. 2.17",
        )

    # ---- fc_90_d ----

    @property
    def fc_90_d(self) -> float:
        """Résistance de calcul en compression perpendiculaire [MPa]"""
        return self._fd(self._data.fc_90_k)

    @property
    def fc_90_d_report(self) -> FormulaResult:
        return FormulaResult(
            name="fc,90,d",
            formula="fc,90,d = kmod × fc,90,k / γM",
            formula_values=(
                f"fc,90,d = {self.kmod:.2f} × {self._data.fc_90_k:.2f} / "
                f"{self.gamma_m:.2f} = {self.fc_90_d:.2f}"
            ),
            result=self.fc_90_d,
            unit="MPa",
            ref="EC5 — §2.4.1 — Eq. 2.17",
        )

    # ---- fv_d ----

    @property
    def fv_d(self) -> float:
        """Résistance de calcul au cisaillement [MPa]"""
        return self._fd(self._data.fv_k)

    @property
    def fv_d_report(self) -> FormulaResult:
        return FormulaResult(
            name="fv,d",
            formula="fv,d = kmod × fv,k / γM",
            formula_values=(
                f"fv,d = {self.kmod:.2f} × {self._data.fv_k:.2f} / "
                f"{self.gamma_m:.2f} = {self.fv_d:.2f}"
            ),
            result=self.fv_d,
            unit="MPa",
            ref="EC5 — §2.4.1 — Eq. 2.17",
        )

    # =================================================================
    # Rapport complet
    # =================================================================

    def all_reports(self) -> list[FormulaResult]:
        """Retourne la liste de tous les FormulaResult pour rapport de calcul."""
        return [
            self.gamma_m_report,
            self.kmod_report,
            self.kdef_report,
            self.fm_d_report,
            self.ft_0_d_report,
            self.ft_90_d_report,
            self.fc_0_d_report,
            self.fc_90_d_report,
            self.fv_d_report,
        ]

    # =================================================================
    # Représentation
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"MatTimber(grade='{self._grade}', type='{self._timber_type}', "
            f"SC={self._service_class}, load='{self._load_duration}', "
            f"country='{self._country}')"
        )

    def __str__(self) -> str:
        lines = [
            f"{'=' * 70}",
            f"  {self._name} ({self._timber_type}) — SC{self._service_class} "
            f"— {self._load_duration} — AN {self._country}",
            f"{'=' * 70}",
            f"  --- Propriétés caractéristiques ---",
            f"  fm,k    = {self._data.fm_k:8.2f} MPa",
            f"  ft,0,k  = {self._data.ft_0_k:8.2f} MPa",
            f"  ft,90,k = {self._data.ft_90_k:8.2f} MPa",
            f"  fc,0,k  = {self._data.fc_0_k:8.2f} MPa",
            f"  fc,90,k = {self._data.fc_90_k:8.2f} MPa",
            f"  fv,k    = {self._data.fv_k:8.2f} MPa",
            f"  E0,mean = {self._data.E_0_mean:8.0f} MPa",
            f"  E0,05   = {self._data.E_0_05:8.0f} MPa",
            f"  E90,mean= {self._data.E_90_mean:8.0f} MPa",
            f"  G,mean  = {self._data.G_mean:8.0f} MPa",
            f"  ρk      = {self._data.rho_k:8.0f} kg/m³",
            f"  ρmean   = {self._data.rho_mean:8.0f} kg/m³",
            f"  --- Résistances de calcul ---",
        ]
        for r in self.all_reports():
            lines.append(f"  {r.formula_values:60s} [{r.unit}]  ({r.ref})")
        lines.append(f"{'=' * 70}")
        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    # --- Bois massif C24 ---
    c24 = MatTimber(grade="C24", service_class=1, load_duration="medium_term")
    print(c24)

    print(f"\nfm,d  = {c24.fm_d:.2f} MPa")
    print(c24.fm_d_report)

    print(f"\nkmod  = {c24.kmod}")
    print(f"kdef  = {c24.kdef}")
    print(f"γM    = {c24.gamma_m}")

    # --- Changement durée de charge ---
    print("\n--- Passage en charge courte durée ---")
    c24.load_duration = "short_term"
    print(f"kmod  = {c24.kmod}")
    print(f"fm,d  = {c24.fm_d:.2f} MPa")

    # --- Lamellé-collé GL24H ---
    print("\n--- GL24H ---")
    gl24 = MatTimber(grade="GL24H", timber_type="glulam", service_class=2)
    print(gl24)

    # --- Rapport complet ---
    print("\n--- Rapport complet C24 ---")
    for r in c24.all_reports():
        print(f"  {r.name:10s} = {r.result:10.4f} {r.unit:5s}  |  {r.ref}")
