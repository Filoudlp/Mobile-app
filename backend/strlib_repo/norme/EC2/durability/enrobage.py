#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC2-1-1 §4.4 — Détermination de l'enrobage nominal des armatures de béton armé.

Couvre :
    - Classes d'exposition (Tableau 4.1)
    - Classe structurale et modulations (Tableau 4.3N)
    - Enrobage minimal vis-à-vis de l'adhérence  cmin,b   (§4.4.1.2(3))
    - Enrobage minimal vis-à-vis de la durabilité cmin,dur (Tableau 4.4N)
    - Enrobage minimal cmin   (§4.4.1.2(2))
    - Enrobage nominal  cnom  (§4.4.1.1(2))
    - Prise en compte optionnelle de la résistance au feu (EC2-1-2)

Unités : mm pour les enrobages, MPa pour fck.
Pas de précontrainte.
"""

__all__ = [
    "Enrobage",
    "classe_structurale",
    "c_min_dur",
    "c_min",
    "c_nom",
]

import math
import warnings
from typing import Dict, List, Optional, TypeVar, Union

from formula import FormulaCollection, FormulaResult

# ---------------------------------------------------------------------------
#  Forward-references pour les classes externes de la librairie
# ---------------------------------------------------------------------------
national_annex = TypeVar("national_annex")
sec_mat_rc = TypeVar("sec_mat_rc")

# ---------------------------------------------------------------------------
#  Constantes — Classes d'exposition valides (EC2-1-1 Tableau 4.1)
# ---------------------------------------------------------------------------
VALID_EXPOSURE_CLASSES: List[str] = [
    "X0",
    "XC1", "XC2", "XC3", "XC4",
    "XD1", "XD2", "XD3",
    "XS1", "XS2", "XS3",
    "XF1", "XF2", "XF3", "XF4",
    "XA1", "XA2", "XA3",
]

# Classes qui interviennent directement dans le Tableau 4.4N
_EXPO_COLS: List[str] = [
    "X0",
    "XC1", "XC2/XC3", "XC4",
    "XD1/XS1", "XD2/XS2", "XD3/XS3",
    "XA1", "XA2", "XA3",
]

# ---------------------------------------------------------------------------
#  Tableau 4.4N — cmin,dur (mm) selon classe structurale & classe d'exposition
#  Clé externe = n° de classe structurale (1..6)
#  Clé interne = colonne normalisée du tableau
# ---------------------------------------------------------------------------
TABLE_4_4N: Dict[int, Dict[str, float]] = {
    1: {"X0": 10, "XC1": 10, "XC2/XC3": 10, "XC4": 15,
        "XD1/XS1": 20, "XD2/XS2": 25, "XD3/XS3": 30,
        "XA1": 10, "XA2": 10, "XA3": 15},
    2: {"X0": 10, "XC1": 10, "XC2/XC3": 15, "XC4": 20,
        "XD1/XS1": 25, "XD2/XS2": 30, "XD3/XS3": 35,
        "XA1": 10, "XA2": 15, "XA3": 20},
    3: {"X0": 10, "XC1": 10, "XC2/XC3": 20, "XC4": 25,
        "XD1/XS1": 30, "XD2/XS2": 35, "XD3/XS3": 40,
        "XA1": 15, "XA2": 20, "XA3": 25},
    4: {"X0": 10, "XC1": 15, "XC2/XC3": 25, "XC4": 30,
        "XD1/XS1": 35, "XD2/XS2": 40, "XD3/XS3": 45,
        "XA1": 20, "XA2": 25, "XA3": 30},
    5: {"X0": 15, "XC1": 20, "XC2/XC3": 30, "XC4": 35,
        "XD1/XS1": 40, "XD2/XS2": 45, "XD3/XS3": 50,
        "XA1": 25, "XA2": 30, "XA3": 35},
    6: {"X0": 20, "XC1": 25, "XC2/XC3": 35, "XC4": 40,
        "XD1/XS1": 45, "XD2/XS2": 50, "XD3/XS3": 55,
        "XA1": 30, "XA2": 35, "XA3": 40},
}

# ---------------------------------------------------------------------------
#  Tableau 4.3N — Seuils de résistance pour la modulation −1 (Critère 2)
#  Clé = colonne du tableau 4.4N  →  fck minimal (MPa) pour bénéficier du −1
# ---------------------------------------------------------------------------
_FCK_THRESHOLDS: Dict[str, float] = {
    "X0":       -1.0,       # pas de réduction liée à la résistance pour X0
    "XC1":      -1.0,       # idem
    "XC2/XC3":  30.0,
    "XC4":      30.0,
    "XD1/XS1":  35.0,
    "XD2/XS2":  40.0,
    "XD3/XS3":  45.0,
    "XA1":      30.0,
    "XA2":      35.0,
    "XA3":      40.0,
}

# ---------------------------------------------------------------------------
#  Helpers internes
# ---------------------------------------------------------------------------

def _normalise_expo(classe: str) -> str:
    """Renvoie la chaîne en majuscules sans espaces."""
    return classe.strip().upper()


def _validate_expo(classes: List[str]) -> List[str]:
    """Valide et normalise une liste de classes d'exposition."""
    normed: List[str] = []
    for c in classes:
        cn = _normalise_expo(c)
        if cn not in VALID_EXPOSURE_CLASSES:
            raise ValueError(
                f"Classe d'exposition '{c}' invalide. "
                f"Classes acceptées : {VALID_EXPOSURE_CLASSES}"
            )
        normed.append(cn)
    if not normed:
        raise ValueError("Au moins une classe d'exposition est requise.")
    return normed


def _expo_to_column(expo: str) -> str:
    """
    Convertit une classe d'exposition unitaire vers la colonne
    correspondante du Tableau 4.4N.

    Les classes XF* n'ont pas de colonne propre dans le tableau 4.4N :
    elles influencent la classe structurale mais ne pilotent pas directement
    cmin,dur.  On renvoie ``""`` dans ce cas.
    """
    mapping = {
        "X0":  "X0",
        "XC1": "XC1",
        "XC2": "XC2/XC3", "XC3": "XC2/XC3",
        "XC4": "XC4",
        "XD1": "XD1/XS1", "XS1": "XD1/XS1",
        "XD2": "XD2/XS2", "XS2": "XD2/XS2",
        "XD3": "XD3/XS3", "XS3": "XD3/XS3",
        "XA1": "XA1",
        "XA2": "XA2",
        "XA3": "XA3",
    }
    return mapping.get(expo, "")


def _severity_rank(col: str) -> int:
    """Rang de sévérité d'une colonne du Tableau 4.4N (plus élevé = plus sévère)."""
    order = [
        "X0", "XC1", "XC2/XC3", "XC4",
        "XD1/XS1", "XD2/XS2", "XD3/XS3",
        "XA1", "XA2", "XA3",
    ]
    try:
        return order.index(col)
    except ValueError:
        return -1


def _most_severe_column(classes: List[str]) -> str:
    """
    Parmi une liste de classes d'exposition, retourne la colonne du
    Tableau 4.4N la plus défavorable (c_min_dur le plus grand en S4).
    """
    best_col = ""
    best_val = -1.0
    for c in classes:
        col = _expo_to_column(c)
        if col == "":
            continue
        val = TABLE_4_4N[4].get(col, 0.0)  # comparaison en S4
        if val > best_val or (val == best_val and _severity_rank(col) > _severity_rank(best_col)):
            best_val = val
            best_col = col
    return best_col


def _fck_from_classe(classe_resistance: str) -> float:
    """Extrait fck (MPa) depuis une chaîne type 'C25/30'."""
    try:
        return float(classe_resistance.upper().replace("C", "").split("/")[0])
    except (ValueError, IndexError):
        return 0.0


# ===================================================================
#  Fonctions standalone
# ===================================================================

def classe_structurale(
    classes_exposition: Union[str, List[str]],
    fck: float = 0.0,
    duree_utilisation: int = 50,
    is_dalle: bool = False,
    assurance_qualite: bool = False,
    classe_structurale_base: int = 4,
) -> int:
    """
    Détermine la classe structurale finale (S1…S6) selon le Tableau 4.3N.

    Parameters
    ----------
    classes_exposition : str ou list[str]
        Classe(s) d'exposition.
    fck : float
        Résistance caractéristique du béton [MPa].
    duree_utilisation : int
        Durée d'utilisation de projet (50 ou 100 ans).
    is_dalle : bool
        True si l'élément est un élément de type dalle.
    assurance_qualite : bool
        True si assurance qualité spéciale.
    classe_structurale_base : int
        Classe structurale de départ (défaut 4 pour 50 ans).

    Returns
    -------
    int
        Classe structurale finale (1 ≤ S ≤ 6).

    References
    ----------
    EC2-1-1 — §4.4.1.2(5), Tableau 4.3N
    """
    if isinstance(classes_exposition, str):
        classes_exposition = [classes_exposition]
    expo_list = _validate_expo(classes_exposition)

    s = classe_structurale_base

    # Critère 1 — durée d'utilisation 100 ans → +2
    if duree_utilisation >= 100:
        s += 2

    # Critère 2 — classe de résistance suffisante → −1
    col = _most_severe_column(expo_list)
    if col:
        threshold = _FCK_THRESHOLDS.get(col, -1.0)
        if threshold > 0 and fck >= threshold:
            s -= 1

    # Critère 3 — dalle → −1
    if is_dalle:
        s -= 1

    # Critère 4 — assurance qualité → −1
    if assurance_qualite:
        s -= 1

    # Clipper entre S1 et S6
    return max(1, min(6, s))


def c_min_dur(
    classes_exposition: Union[str, List[str]],
    s_class: int = 4,
    table: Optional[Dict[int, Dict[str, float]]] = None,
) -> float:
    """
    Enrobage minimal vis-à-vis de la durabilité cmin,dur [mm].

    Parameters
    ----------
    classes_exposition : str ou list[str]
    s_class : int
        Classe structurale (1…6).
    table : dict, optional
        Tableau 4.4N surchargé.

    Returns
    -------
    float
        cmin,dur [mm].

    References
    ----------
    EC2-1-1 — §4.4.1.2(5), Tableau 4.4N
    """
    if isinstance(classes_exposition, str):
        classes_exposition = [classes_exposition]
    expo_list = _validate_expo(classes_exposition)
    tbl = table if table is not None else TABLE_4_4N

    s_class = max(1, min(6, s_class))

    col = _most_severe_column(expo_list)
    if not col:
        return 0.0
    return tbl[s_class].get(col, 0.0)


def c_min(
    c_min_b_val: float,
    c_min_dur_val: float,
    delta_c_dur_gamma: float = 0.0,
    delta_c_dur_st: float = 0.0,
    delta_c_dur_add: float = 0.0,
    c_min_feu: Optional[float] = None,
) -> float:
    """
    Enrobage minimal cmin [mm] — §4.4.1.2(2).

    cmin = max(cmin,b ; cmin,dur + Δcdur,γ − Δcdur,st − Δcdur,add ; 10 mm)

    Si ``c_min_feu`` est fourni :
        cmin = max(cmin_calculé ; c_min_feu)

    References
    ----------
    EC2-1-1 — §4.4.1.2(2)
    """
    dur_term = c_min_dur_val + delta_c_dur_gamma - delta_c_dur_st - delta_c_dur_add
    val = max(c_min_b_val, dur_term, 10.0)
    if c_min_feu is not None:
        val = max(val, c_min_feu)
    return val


def c_nom(
    c_min_val: float,
    delta_c_dev: float = 10.0,
) -> float:
    """
    Enrobage nominal cnom [mm] — §4.4.1.1(2).

    cnom = cmin + Δcdev

    References
    ----------
    EC2-1-1 — §4.4.1.1(2)
    """
    return c_min_val + delta_c_dev


# ===================================================================
#  Classe principale
# ===================================================================

class Enrobage:
    """
    Détermination de l'enrobage nominal des armatures de béton armé
    conformément à l'EC2-1-1 §4.4.

    Parameters
    ----------
    classe_exposition : str ou list[str]
        Classe(s) d'exposition (ex : ``"XC2"`` ou ``["XC2", "XS1"]``).
    sec : sec_mat_rc, optional
        Objet *SecMatRC* portant ``phi_max``, ``fck`` / ``classe_resistance``.
    na : national_annex, optional
        Objet *NationalAnnex* pour les paramètres d'annexe nationale.
    **kwargs
        Paramètres individuels (priorité si ``sec`` / ``na`` non fournis) :

        - ``phi`` (float) : diamètre max armatures [mm]
        - ``fck`` (float) : résistance caractéristique [MPa]
        - ``classe_resistance`` (str) : ex ``"C30/37"``
        - ``n_barres_paquet`` (int) : nb barres dans un paquet (défaut 1)
        - ``duree_utilisation`` (int) : 50 ou 100 ans
        - ``is_dalle`` (bool)
        - ``assurance_qualite`` (bool)
        - ``classe_structurale_base`` (int)
        - ``c_min_feu`` (float, optional) : enrobage mini feu EC2-1-2 [mm]
        - ``delta_c_dev`` (float)
        - ``delta_c_dur_gamma`` (float)
        - ``delta_c_dur_st`` (float)
        - ``delta_c_dur_add`` (float)
        - ``c_nom_fourni`` (float, optional) : enrobage réellement fourni [mm]
        - ``table_4_4N`` (dict, optional) : tableau surchargé

    References
    ----------
    EC2-1-1 — §4.4
    """

    # ------------------------------------------------------------------
    #  Construction
    # ------------------------------------------------------------------
    def __init__(
        self,
        classe_exposition: Union[str, List[str]],
        sec: Optional[sec_mat_rc] = None,
        na: Optional[national_annex] = None,
        **kwargs,
    ) -> None:

        # --- Classes d'exposition ---
        if isinstance(classe_exposition, str):
            classe_exposition = [classe_exposition]
        self.__classes_expo: List[str] = _validate_expo(classe_exposition)

        # --- Armatures ---
        self.__phi: float = (
            sec.phi_max if sec and hasattr(sec, "phi_max")
            else kwargs.get("phi", 0.0)
        )
        self.__n_barres_paquet: int = kwargs.get("n_barres_paquet", 1)

        # --- Béton ---
        self.__fck: float = (
            sec.fck if sec and hasattr(sec, "fck")
            else kwargs.get("fck", 0.0)
        )
        if self.__fck == 0.0:
            cr = (
                sec.classe_resistance if sec and hasattr(sec, "classe_resistance")
                else kwargs.get("classe_resistance", "")
            )
            if cr:
                self.__fck = _fck_from_classe(cr)

        # --- Paramètres de modulation classe structurale ---
        self.__duree_utilisation: int = kwargs.get("duree_utilisation", 50)
        self.__is_dalle: bool = kwargs.get("is_dalle", False)
        self.__assurance_qualite: bool = kwargs.get("assurance_qualite", False)
        self.__classe_structurale_base: int = kwargs.get("classe_structurale_base", 4)

        # --- Paramètres d'annexe nationale ---
        _na = na.ec2 if na and hasattr(na, "ec2") else None

        self.__delta_c_dev: float = (
            _na.delta_c_dev if _na and hasattr(_na, "delta_c_dev")
            else kwargs.get("delta_c_dev", 10.0)
        )
        self.__delta_c_dur_gamma: float = (
            _na.delta_c_dur_gamma if _na and hasattr(_na, "delta_c_dur_gamma")
            else kwargs.get("delta_c_dur_gamma", 0.0)
        )
        self.__delta_c_dur_st: float = (
            _na.delta_c_dur_st if _na and hasattr(_na, "delta_c_dur_st")
            else kwargs.get("delta_c_dur_st", 0.0)
        )
        self.__delta_c_dur_add: float = (
            _na.delta_c_dur_add if _na and hasattr(_na, "delta_c_dur_add")
            else kwargs.get("delta_c_dur_add", 0.0)
        )

        # --- Feu (optionnel) ---
        self.__c_min_feu: Optional[float] = kwargs.get("c_min_feu", None)

        # --- Enrobage fourni (pour vérification) ---
        self.__c_nom_fourni: Optional[float] = kwargs.get("c_nom_fourni", None)

        # --- Tableau 4.4N (surchargeable) ---
        self.__table_4_4N: Dict[int, Dict[str, float]] = kwargs.get(
            "table_4_4N", TABLE_4_4N
        )

        # --- Avertissement durabilité béton faible ---
        self._check_durability_warning()

    # ------------------------------------------------------------------
    #  Avertissements
    # ------------------------------------------------------------------
    def _check_durability_warning(self) -> None:
        """
        Avertit si fck ≤ 20 MPa et classe d'exposition ≥ XC2.
        Référence : EC2-1-1 Tableau E.1N
        """
        expos_severe = {
            "XC2", "XC3", "XC4",
            "XD1", "XD2", "XD3",
            "XS1", "XS2", "XS3",
            "XA1", "XA2", "XA3",
        }
        if self.__fck > 0 and self.__fck <= 20.0:
            if any(c in expos_severe for c in self.__classes_expo):
                warnings.warn(
                    f"Béton fck = {self.__fck} MPa (≤ C20/25) avec classe(s) "
                    f"d'exposition {self.__classes_expo} : le béton peut ne pas "
                    f"satisfaire les exigences de durabilité (Tableau E.1N).",
                    UserWarning,
                    stacklevel=3,
                )

    # ------------------------------------------------------------------
    #  Propriétés d'entrée
    # ------------------------------------------------------------------
    @property
    def classes_exposition(self) -> List[str]:
        """Liste des classes d'exposition."""
        return list(self.__classes_expo)

    @property
    def phi(self) -> float:
        """Diamètre max des armatures [mm]."""
        return self.__phi

    @property
    def n_barres_paquet(self) -> int:
        """Nombre de barres dans un paquet."""
        return self.__n_barres_paquet

    @property
    def fck(self) -> float:
        """Résistance caractéristique du béton [MPa]."""
        return self.__fck

    # ------------------------------------------------------------------
    #  A — Colonne la plus défavorable du Tableau 4.4N
    # ------------------------------------------------------------------
    @property
    def _col_severe(self) -> str:
        return _most_severe_column(self.__classes_expo)

    # ------------------------------------------------------------------
    #  B — Classe structurale (Tableau 4.3N)
    # ------------------------------------------------------------------
    @property
    def s_class(self) -> int:
        """Classe structurale finale (1…6) — §4.4.1.2(5), Tableau 4.3N."""
        return classe_structurale(
            classes_exposition=self.__classes_expo,
            fck=self.__fck,
            duree_utilisation=self.__duree_utilisation,
            is_dalle=self.__is_dalle,
            assurance_qualite=self.__assurance_qualite,
            classe_structurale_base=self.__classe_structurale_base,
        )

    def get_s_class(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la classe structurale."""
        r = self.s_class
        fv = ""
        if with_values:
            mods: List[str] = [f"Base = S{self.__classe_structurale_base}"]
            if self.__duree_utilisation >= 100:
                mods.append("durée 100 ans → +2")
            col = self._col_severe
            if col:
                thr = _FCK_THRESHOLDS.get(col, -1.0)
                if thr > 0 and self.__fck >= thr:
                    mods.append(
                        f"fck = {self.__fck:.0f} MPa ≥ {thr:.0f} MPa "
                        f"(col. {col}) → −1"
                    )
            if self.__is_dalle:
                mods.append("dalle → −1")
            if self.__assurance_qualite:
                mods.append("assurance qualité → −1")
            mods.append(f"Classe structurale finale = S{r}")
            fv = " ; ".join(mods)
        return FormulaResult(
            name="Classe structurale",
            formula="S = S_base + modulations (Tableau 4.3N), clippé [S1 ; S6]",
            formula_values=fv,
            result=float(r),
            unit="-",
            ref="EC2-1-1 — §4.4.1.2(5), Tableau 4.3N",
        )

    # ------------------------------------------------------------------
    #  C — cmin,b  (§4.4.1.2(3))
    # ------------------------------------------------------------------
    @property
    def phi_paquet(self) -> float:
        """Diamètre équivalent du paquet φn = φ·√n — §8.9.1."""
        if self.__n_barres_paquet <= 1:
            return self.__phi
        return self.__phi * math.sqrt(self.__n_barres_paquet)

    @property
    def c_min_b(self) -> float:
        """
        Enrobage minimal vis-à-vis de l'adhérence cmin,b [mm].

        - Barre isolée : cmin,b = φ
        - Paquet de barres : cmin,b = φ_paquet = φ·√n

        Référence : EC2-1-1 — §4.4.1.2(3)
        """
        return self.phi_paquet

    def get_c_min_b(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour cmin,b."""
        r = self.c_min_b
        fv = ""
        if with_values:
            if self.__n_barres_paquet <= 1:
                fv = f"cmin,b = φ = {self.__phi:.1f} mm"
            else:
                fv = (
                    f"cmin,b = φ_paquet = φ·√n = {self.__phi:.1f} × "
                    f"√{self.__n_barres_paquet} = {r:.1f} mm"
                )
        return FormulaResult(
            name="cmin,b",
            formula=(
                "cmin,b = φ (barre isolée) ou φ·√n (paquet)"
            ),
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2-1-1 — §4.4.1.2(3) & §8.9.1",
        )

    # ------------------------------------------------------------------
    #  D — cmin,dur  (Tableau 4.4N)
    # ------------------------------------------------------------------
    @property
    def c_min_dur(self) -> float:
        """
        Enrobage minimal vis-à-vis de la durabilité cmin,dur [mm].

        Référence : EC2-1-1 — §4.4.1.2(5), Tableau 4.4N
        """
        return c_min_dur(
            classes_exposition=self.__classes_expo,
            s_class=self.s_class,
            table=self.__table_4_4N,
        )

    def get_c_min_dur(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour cmin,dur."""
        r = self.c_min_dur
        fv = ""
        if with_values:
            col = self._col_severe
            fv = (
                f"Classe structurale S{self.s_class}, "
                f"colonne la plus sévère : {col} → "
                f"cmin,dur = {r:.0f} mm"
            )
        return FormulaResult(
            name="cmin,dur",
            formula="cmin,dur = Tableau 4.4N (classe struct. × classe expo.)",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2-1-1 — §4.4.1.2(5), Tableau 4.4N",
        )

    # ------------------------------------------------------------------
    #  E — cmin  (§4.4.1.2(2))
    # ------------------------------------------------------------------
    @property
    def c_min(self) -> float:
        """
        Enrobage minimal cmin [mm].

        cmin = max(cmin,b ; cmin,dur + Δcdur,γ − Δcdur,st − Δcdur,add ; 10 mm)
        Si c_min_feu fourni : cmin = max(cmin ; c_min_feu)

        Référence : EC2-1-1 — §4.4.1.2(2)
        """
        return c_min(
            c_min_b_val=self.c_min_b,
            c_min_dur_val=self.c_min_dur,
            delta_c_dur_gamma=self.__delta_c_dur_gamma,
            delta_c_dur_st=self.__delta_c_dur_st,
            delta_c_dur_add=self.__delta_c_dur_add,
            c_min_feu=self.__c_min_feu,
        )

    def get_c_min(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour cmin."""
        r = self.c_min
        dur_term = (
            self.c_min_dur
            + self.__delta_c_dur_gamma
            - self.__delta_c_dur_st
            - self.__delta_c_dur_add
        )
        fv = ""
        if with_values:
            parts = [
                f"cmin,b = {self.c_min_b:.1f}",
                (
                    f"cmin,dur + Δcdur,γ − Δcdur,st − Δcdur,add = "
                    f"{self.c_min_dur:.1f} + {self.__delta_c_dur_gamma:.1f} "
                    f"− {self.__delta_c_dur_st:.1f} − {self.__delta_c_dur_add:.1f} "
                    f"= {dur_term:.1f}"
                ),
                "10",
            ]
            fv = (
                f"cmin = max({' ; '.join(parts)}) = "
                f"max({self.c_min_b:.1f} ; {dur_term:.1f} ; 10) "
            )
            base_val = max(self.c_min_b, dur_term, 10.0)
            if self.__c_min_feu is not None:
                fv += (
                    f"= {base_val:.1f} mm\n"
                    f"Prise en compte du feu : cmin = max({base_val:.1f} ; "
                    f"{self.__c_min_feu:.1f}) = {r:.1f} mm"
                )
            else:
                fv += f"= {r:.1f} mm"
        formula_str = (
            "cmin = max(cmin,b ; cmin,dur + Δcdur,γ − Δcdur,st − Δcdur,add ; 10 mm)"
        )
        if self.__c_min_feu is not None:
            formula_str += "  puis max(cmin ; cmin,feu)"
        return FormulaResult(
            name="cmin",
            formula=formula_str,
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2-1-1 — §4.4.1.2(2)",
        )

    # ------------------------------------------------------------------
    #  F — cnom  (§4.4.1.1(2))
    # ------------------------------------------------------------------
    @property
    def c_nom(self) -> float:
        """
        Enrobage nominal cnom [mm].

        cnom = cmin + Δcdev

        Référence : EC2-1-1 — §4.4.1.1(2)
        """
        return c_nom(self.c_min, self.__delta_c_dev)

    def get_c_nom(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour cnom."""
        r = self.c_nom
        fv = ""
        if with_values:
            fv = (
                f"cnom = cmin + Δcdev = {self.c_min:.1f} + "
                f"{self.__delta_c_dev:.1f} = {r:.1f} mm"
            )
        return FormulaResult(
            name="cnom",
            formula="cnom = cmin + Δcdev",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2-1-1 — §4.4.1.1(2)",
        )

    # ------------------------------------------------------------------
    #  G — Vérification (optionnelle)
    # ------------------------------------------------------------------
    @property
    def verif(self) -> Optional[float]:
        """
        Taux c_nom_requis / c_nom_fourni.
        Retourne None si aucun c_nom_fourni n'a été renseigné.
        """
        if self.__c_nom_fourni is None:
            return None
        if self.__c_nom_fourni == 0:
            return float("inf")
        return round(self.c_nom / self.__c_nom_fourni, 4)

    @property
    def is_ok(self) -> Optional[bool]:
        """
        True si c_nom_fourni ≥ c_nom_requis.
        None si c_nom_fourni n'est pas renseigné.
        """
        v = self.verif
        if v is None:
            return None
        return v <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la vérification c_nom_fourni ≥ c_nom_requis."""
        r = self.verif if self.verif is not None else 0.0
        fv = ""
        if with_values:
            if self.__c_nom_fourni is not None:
                status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
                fv = (
                    f"cnom,requis / cnom,fourni = {self.c_nom:.1f} / "
                    f"{self.__c_nom_fourni:.1f} = {r:.4f} ≤ 1.0 → {status}"
                )
            else:
                fv = "Aucun enrobage fourni renseigné — pas de vérification."
        return FormulaResult(
            name="cnom,req/cnom,fourni",
            formula="cnom,requis / cnom,fourni ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2-1-1 — §4.4.1.1",
        )

    # ------------------------------------------------------------------
    #  H — Rapport complet
    # ------------------------------------------------------------------
    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes du calcul
        d'enrobage nominal.
        """
        fc = FormulaCollection(
            title="Détermination de l'enrobage nominal",
            ref="EC2-1-1 — §4.4",
        )
        fc.add(self.get_s_class(with_values=with_values))
        fc.add(self.get_c_min_b(with_values=with_values))
        fc.add(self.get_c_min_dur(with_values=with_values))
        fc.add(self.get_c_min(with_values=with_values))
        fc.add(self.get_c_nom(with_values=with_values))
        if self.__c_nom_fourni is not None:
            fc.add(self.get_verif(with_values=with_values))
        return fc

    # ------------------------------------------------------------------
    #  Représentation
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        ok_str = ""
        if self.is_ok is not None:
            ok_str = f", ok={self.is_ok}"
        return (
            f"Enrobage(expo={self.__classes_expo}, S{self.s_class}, "
            f"cmin,b={self.c_min_b:.1f}, cmin,dur={self.c_min_dur:.0f}, "
            f"cmin={self.c_min:.1f}, cnom={self.c_nom:.1f} mm{ok_str})"
        )


# ===================================================================
#  Debug / Démonstration
# ===================================================================
if __name__ == "__main__":

    print("=" * 72)
    print("CAS 1 : X0, φ20, S4 (défaut)")
    print("=" * 72)
    e1 = Enrobage("X0", phi=20.0)
    print(e1)
    r1 = e1.report(with_values=True)
    print(r1)

    print("\n" + "=" * 72)
    print("CAS 2 : XC3 + XD1, φ25, dalle, C35/45")
    print("=" * 72)
    e2 = Enrobage(
        ["XC3", "XD1"],
        phi=25.0,
        fck=35.0,
        is_dalle=True,
    )
    print(e2)
    r2 = e2.report(with_values=True)
    print(r2)

    print("\n" + "=" * 72)
    print("CAS 3 : XS2, φ32, 100 ans, paquet de 2 barres")
    print("=" * 72)
    e3 = Enrobage(
        "XS2",
        phi=32.0,
        fck=30.0,
        duree_utilisation=100,
        n_barres_paquet=2,
    )
    print(e3)
    r3 = e3.report(with_values=True)
    print(r3)

    print("\n" + "=" * 72)
    print("CAS 4 : XC2, φ16, avec c_min_feu = 35 mm (EC2-1-2)")
    print("=" * 72)
    e4 = Enrobage(
        "XC2",
        phi=16.0,
        fck=25.0,
        c_min_feu=35.0,
        c_nom_fourni=50.0,
    )
    print(e4)
    r4 = e4.report(with_values=True)
    print(r4)
