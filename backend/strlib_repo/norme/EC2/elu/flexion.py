#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC2 – Flexion simple ELU & ELS pour section rectangulaire ou en T.

Conforme à l'EN 1992-1-1 (Eurocode 2).
Unités : N, mm, MPa.
"""

__all__ = ["Flexion", "as_flexion_simple", "sigma_els"]

from typing import TypeVar, Optional
import math

# --- Imports internes (à adapter au chemin réel de la librairie) -----------
# from formula import FormulaResult, FormulaCollection
# Pour rendre le fichier exécutable seul on fournit un import conditionnel :
try:
    from formula import FormulaResult, FormulaCollection
except ImportError:
    # Stubs minimaux pour exécution autonome / debug
    class FormulaResult:
        def __init__(self, name="", formula="", formula_values="",
                     result=0.0, unit="", ref=""):
            self.name = name
            self.formula = formula
            self.formula_values = formula_values
            self.result = result
            self.unit = unit
            self.ref = ref

        def __repr__(self):
            return (f"FormulaResult({self.name}={self.result:.4f} {self.unit}"
                    f"  |  {self.formula_values})")

    class FormulaCollection:
        def __init__(self, title="", ref=""):
            self.title = title
            self.ref = ref
            self._items: list = []

        def add(self, item):
            self._items.append(item)

        def __repr__(self):
            sep = "-" * 60
            header = f"\n{sep}\n  {self.title}  ({self.ref})\n{sep}"
            body = "\n".join(f"  {r}" for r in self._items)
            return f"{header}\n{body}\n{sep}"


sec_mat = TypeVar("sec_mat")

# ==========================================================================
#  Constantes utilitaires
# ==========================================================================

_EPS = 1e-12  # garde contre division par zéro


def _safe_div(a: float, b: float) -> float:
    """Division protégée."""
    if abs(b) < _EPS:
        return float("inf") if a >= 0 else float("-inf")
    return a / b


# ==========================================================================
#  Paramètres diagramme rectangulaire simplifié  (EC2 §3.1.7 (3))
# ==========================================================================

def _lambda_rect(fck: float) -> float:
    """λ – hauteur relative du bloc rectangulaire simplifié.
    EC2 §3.1.7 (3) : λ = 0.8 pour fck ≤ 50 MPa
                       λ = 0.8 – (fck – 50)/400 pour 50 < fck ≤ 90 MPa
    """
    if fck <= 50.0:
        return 0.8
    return max(0.8 - (fck - 50.0) / 400.0, 0.0)


def _eta_rect(fck: float) -> float:
    """η – coefficient d'efficacité du bloc rectangulaire simplifié.
    EC2 §3.1.7 (3) : η = 1.0 pour fck ≤ 50 MPa
                       η = 1.0 – (fck – 50)/200 pour 50 < fck ≤ 90 MPa
    """
    if fck <= 50.0:
        return 1.0
    return max(1.0 - (fck - 50.0) / 200.0, 0.0)


def _ecu2(fck: float) -> float:
    """εcu2 – déformation ultime béton diagramme parabole‑rectangle [‰ → abs].
    EC2 Tableau 3.1 : εcu2 = 3.5 ‰ pour fck ≤ 50 MPa
                       εcu2 = 2.6 + 35·((90-fck)/100)^4 ‰ pour fck > 50 MPa
    """
    if fck <= 50.0:
        return 3.5e-3
    return (2.6 + 35.0 * ((90.0 - fck) / 100.0) ** 4) * 1e-3


# ==========================================================================
#  Calcul de μlu (moment réduit limite – pivot A/B)
# ==========================================================================

def _alpha_lu(ecu2: float, eud: float) -> float:
    """Position relative limite de l'axe neutre (frontière pivot A/B).
    α_lu = εcu2 / (εcu2 + εud)
    """
    denom = ecu2 + eud
    if abs(denom) < _EPS:
        return 0.0
    return ecu2 / denom


def _mu_lu(fck: float, eud: float = 10.0e-3) -> float:
    """Moment réduit limite μlu (diagramme rectangulaire simplifié).
    μlu = η · λ · α_lu · (1 – λ · α_lu / 2)
    avec α_lu = εcu2 / (εcu2 + εud).
    """
    lam = _lambda_rect(fck)
    eta = _eta_rect(fck)
    ecu = _ecu2(fck)
    a_lu = _alpha_lu(ecu, eud)
    return eta * lam * a_lu * (1.0 - lam * a_lu / 2.0)


# ==========================================================================
#  Classe Flexion
# ==========================================================================

class Flexion:
    """
    Vérification à la flexion simple d'une section rectangulaire ou en T
    en béton armé, ELU (§6.1) et ELS (§7.1–§7.3) – sans précontrainte.

    Parameters
    ----------
    Med : float
        Moment fléchissant de calcul [N·mm] (valeur absolue utilisée).
    Med_els : float, optional
        Moment fléchissant ELS (caractéristique/quasi-permanent) [N·mm].
        S'il n'est pas fourni, les vérifications ELS sont ignorées.
    sec : sec_mat, optional
        Objet SecMatRC portant toutes les propriétés géométriques et
        matériaux. Les propriétés peuvent aussi être passées via **kwargs.
    **kwargs :
        Propriétés individuelles (priorité basse par rapport à sec) :
        b, bw, beff, hf, h, d, d_prime, c_nom,
        fck, fcd, fctm, Ecm, alpha_cc,
        fyk, fyd, Es, eud,
        As_exist (section d'acier existante tendu) [mm²],
        As2_exist (section d'acier existante comprimé) [mm²],
        is_T (bool).
    """

    # ------------------------------------------------------------------
    #  Constructeur
    # ------------------------------------------------------------------
    def __init__(
        self,
        Med: float,
        sec: Optional[sec_mat] = None,
        Med_els: Optional[float] = None,
        **kwargs,
    ) -> None:

        self.__med: float = abs(Med)
        self.__med_els: float = abs(Med_els) if Med_els is not None else 0.0
        self.__has_els: bool = Med_els is not None

        # --- helpers ---
        def _g(attr: str, default=0.0):
            """Lecture depuis sec puis kwargs."""
            if sec is not None and hasattr(sec, attr):
                return getattr(sec, attr)
            return kwargs.get(attr, default)

        # --- Géométrie ---
        self.__h: float = _g("h")
        self.__b: float = _g("b")               # largeur (rect) ou beff
        self.__bw: float = _g("bw", self.__b)    # largeur âme (T)
        self.__beff: float = _g("beff", self.__b)
        self.__hf: float = _g("hf", 0.0)         # épaisseur table
        self.__d: float = _g("d")
        self.__d_prime: float = _g("d_prime", 0.0)
        self.__is_T: bool = _g("is_T", False)

        # --- Béton ---
        self.__fck: float = _g("fck")
        self.__fcd: float = _g("fcd")
        self.__fctm: float = _g("fctm", 0.0)
        self.__Ecm: float = _g("Ecm", 33000.0)
        self.__alpha_cc: float = _g("alpha_cc", 1.0)

        # --- Acier ---
        self.__fyk: float = _g("fyk", 500.0)
        self.__fyd: float = _g("fyd")
        self.__Es: float = _g("Es", 200000.0)
        self.__eud: float = _g("eud", 10.0e-3)

        # --- Aciers existants (pour vérification ELS) ---
        self.__As_exist: float = _g("As_exist", 0.0)
        self.__As2_exist: float = _g("As2_exist", 0.0)

        # --- Paramètres diagramme rect. simplifié ---
        self.__lam: float = _lambda_rect(self.__fck)
        self.__eta: float = _eta_rect(self.__fck)
        self.__ecu2: float = _ecu2(self.__fck)

        # --- Coefficient d'équivalence ELS ---
        self.__n_eq: float = (
            _safe_div(self.__Es, self.__Ecm)
            if self.__Ecm > 0 else 15.0
        )

        # --- Largeur de calcul ELU (selon forme) ---
        self.__b_elu: float = self.__beff if self.__is_T else self.__b

    # ==================================================================
    #  Propriétés de lecture
    # ==================================================================

    @property
    def med(self) -> float:
        """Moment de calcul ELU [N·mm]."""
        return self.__med

    @property
    def med_els(self) -> float:
        """Moment de calcul ELS [N·mm]."""
        return self.__med_els

    # ------------------------------------------------------------------
    #  A — ELU  —  Section rectangulaire ou en T
    # ------------------------------------------------------------------

    # --- A.1  Moment réduit limite μlu ---

    @property
    def mu_lu(self) -> float:
        """Moment réduit limite μlu (frontière pivot A/B).
        EC2 §6.1, diagramme rectangulaire simplifié.
        μlu = η·λ·α_lu·(1 − λ·α_lu/2)
        avec α_lu = εcu2 / (εcu2 + εud)
        """
        return _mu_lu(self.__fck, self.__eud)

    def get_mu_lu(self, with_values: bool = False) -> FormulaResult:
        r = self.mu_lu
        a_lu = _alpha_lu(self.__ecu2, self.__eud)
        fv = ""
        if with_values:
            fv = (
                f"α_lu = {self.__ecu2*1e3:.2f}‰ / "
                f"({self.__ecu2*1e3:.2f}‰ + {self.__eud*1e3:.2f}‰) = {a_lu:.4f}\n"
                f"μlu = {self.__eta:.2f} × {self.__lam:.2f} × {a_lu:.4f} × "
                f"(1 − {self.__lam:.2f}×{a_lu:.4f}/2) = {r:.4f}"
            )
        return FormulaResult(
            name="μlu",
            formula="μlu = η·λ·α_lu·(1 − λ·α_lu/2)  ;  α_lu = εcu2/(εcu2+εud)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 §6.1 — diag. rect. simplifié",
        )

    # --- A.2  Section en T : moment repris par les tables ---

    @property
    def _Mf(self) -> float:
        """Moment résistant de la table seule Mf [N·mm].
        Mf = (beff − bw) · hf · η·fcd · (d − hf/2)
        Utilisé uniquement si is_T et que l'axe neutre descend dans l'âme.
        """
        if not self.__is_T:
            return 0.0
        return ((self.__beff - self.__bw) * self.__hf
                * self.__eta * self.__fcd
                * (self.__d - self.__hf / 2.0))

    @property
    def _mu_bu_table(self) -> float:
        """μbu fictif si toute la table est comprimée (largeur beff).
        Permet de tester si l'AN reste dans la table.
        μ_f = Mf_max / (beff · d² · fcd)
        avec Mf_max = beff · hf · η·fcd · (d − hf/2)  (table pleine largeur).
        On compare μbu_beff à ce seuil.
        Alternativement on compare x = λ·α·d à hf.
        """
        if not self.__is_T or self.__hf <= 0:
            return 0.0
        # Moment max que peut reprendre une section de largeur beff
        # avec un bloc comprimé de hauteur hf :
        #   a = 0.8·x = hf  → x = hf/λ
        #   α = x/d = hf/(λ·d)
        #   μ_lim_table = η·λ·α·(1 − λ·α/2)  avec α = hf/(λ·d)
        alpha_tab = self.__hf / (self.__lam * self.__d) if self.__d > 0 else 0.0
        return self.__eta * self.__lam * alpha_tab * (1.0 - self.__lam * alpha_tab / 2.0)

    @property
    def _an_in_table(self) -> bool:
        """True si l'axe neutre reste dans la table (section en T traitée
        comme rectangulaire de largeur beff)."""
        if not self.__is_T:
            return True  # rectangulaire → pas de table
        return self.mu_bu <= self._mu_bu_table

    # --- A.3  Moment réduit μbu ---

    @property
    def mu_bu(self) -> float:
        """Moment réduit μbu = Med / (b · d² · fcd).
        Pour une section en T avec AN dans l'âme, on utilise
        la méthode de décomposition : μw = Mw / (bw · d² · fcd).
        """
        if self.__is_T and not self._an_in_table:
            # Moment résiduel repris par l'âme
            Mw = self.__med - self._Mf
            return _safe_div(Mw, self.__bw * self.__d ** 2 * self.__fcd)
        # Rectangulaire ou T avec AN dans la table
        return _safe_div(
            self.__med,
            self.__b_elu * self.__d ** 2 * self.__fcd,
        )

    def get_mu_bu(self, with_values: bool = False) -> FormulaResult:
        r = self.mu_bu
        fv = ""
        if with_values:
            if self.__is_T and not self._an_in_table:
                Mw = self.__med - self._Mf
                fv = (
                    f"AN dans l'âme → décomposition\n"
                    f"Mf = ({self.__beff:.1f}−{self.__bw:.1f})×{self.__hf:.1f}"
                    f"×{self.__eta:.2f}×{self.__fcd:.2f}"
                    f"×({self.__d:.1f}−{self.__hf:.1f}/2)"
                    f" = {self._Mf:.2f} N·mm\n"
                    f"Mw = {self.__med:.2f} − {self._Mf:.2f} = {Mw:.2f} N·mm\n"
                    f"μbu = {Mw:.2f} / ({self.__bw:.1f}×{self.__d:.1f}²"
                    f"×{self.__fcd:.2f}) = {r:.4f}"
                )
            else:
                b_used = self.__b_elu
                fv = (
                    f"μbu = {self.__med:.2f} / ({b_used:.1f} × {self.__d:.1f}²"
                    f" × {self.__fcd:.2f}) = {r:.4f}"
                )
        return FormulaResult(
            name="μbu",
            formula="μbu = Med / (b · d² · fcd)",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 §6.1",
        )

    # --- A.4  Simple ou double armature ---

    @property
    def is_double(self) -> bool:
        """True si armatures comprimées nécessaires (μbu > μlu)."""
        return self.mu_bu > self.mu_lu

    # --- A.5  α (profondeur relative AN) et z (bras de levier) ---

    @property
    def alpha_u(self) -> float:
        """Profondeur relative de l'axe neutre α = x/d.
        Diag. rect. simplifié : 0.8·α = λ·α → α = 1.25·(1−√(1−2μbu))
        (formulation pour λ = 0.8).
        Formulation générale : λ·α = 1 − √(1 − 2·μbu/(η))  →  α = …/λ
        """
        mu = min(self.mu_bu, self.mu_lu)  # capped pour simple arm.
        disc = 1.0 - 2.0 * mu / self.__eta if self.__eta > 0 else 0.0
        if disc < 0:
            disc = 0.0
        lam_alpha = 1.0 - math.sqrt(disc)
        return _safe_div(lam_alpha, self.__lam)

    def get_alpha_u(self, with_values: bool = False) -> FormulaResult:
        r = self.alpha_u
        mu = min(self.mu_bu, self.mu_lu)
        fv = ""
        if with_values:
            fv = (
                f"α = (1 − √(1 − 2×{mu:.4f}/{self.__eta:.2f})) / {self.__lam:.2f}"
                f" = {r:.4f}"
            )
        return FormulaResult(
            name="α",
            formula="α = (1 − √(1 − 2·μbu/η)) / λ",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 §6.1 — diag. rect. simplifié",
        )

    @property
    def z(self) -> float:
        """Bras de levier z = d·(1 − λ·α/2) [mm]."""
        return self.__d * (1.0 - self.__lam * self.alpha_u / 2.0)

    def get_z(self, with_values: bool = False) -> FormulaResult:
        r = self.z
        fv = ""
        if with_values:
            fv = (
                f"z = {self.__d:.1f} × (1 − {self.__lam:.2f}×{self.alpha_u:.4f}/2)"
                f" = {r:.2f} mm"
            )
        return FormulaResult(
            name="z",
            formula="z = d · (1 − λ·α/2)",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2 §6.1",
        )

    # --- A.6  Pivot ---

    @property
    def pivot(self) -> str:
        """Identification du pivot (A ou B)."""
        a_lu = _alpha_lu(self.__ecu2, self.__eud)
        if self.alpha_u <= a_lu:
            return "A"
        return "B"

    def get_pivot(self, with_values: bool = False) -> FormulaResult:
        r_str = self.pivot
        a_lu = _alpha_lu(self.__ecu2, self.__eud)
        fv = ""
        if with_values:
            fv = (
                f"α = {self.alpha_u:.4f}  ;  α_lu = {a_lu:.4f}  →  "
                f"Pivot {r_str}"
            )
        return FormulaResult(
            name="Pivot",
            formula="Pivot A si α ≤ α_lu, sinon Pivot B",
            formula_values=fv,
            result=0.0 if r_str == "A" else 1.0,
            unit="-",
            ref="EC2 §6.1",
        )

    # --- A.7  Section d'acier tendu As ---

    @property
    def As(self) -> float:
        """Section d'acier tendu requise As [mm²] (simple armature ou
        composante tendue en double armature).
        """
        if self.__fyd < _EPS:
            return 0.0

        if not self.is_double:
            # --- Simple armature ---
            if self.__is_T and not self._an_in_table:
                # Composante table
                As_f = _safe_div(self._Mf, (self.__d - self.__hf / 2.0) * self.__fyd)
                # Composante âme
                As_w = _safe_div(
                    self.__med - self._Mf,
                    self.z * self.__fyd,
                )
                return As_f + As_w
            return _safe_div(self.__med, self.z * self.__fyd)
        else:
            # --- Double armature ---
            return self._As1_double

    @property
    def _As1_double(self) -> float:
        """Acier tendu en double armature."""
        if self.__fyd < _EPS:
            return 0.0
        # Moment repris par la section en simple armature limite
        b_calc = self.__bw if (self.__is_T and not self._an_in_table) else self.__b_elu
        M_lu = self.mu_lu * b_calc * self.__d ** 2 * self.__fcd

        # Bras de levier à μlu
        a_lu = _alpha_lu(self.__ecu2, self.__eud)
        z_lu = self.__d * (1.0 - self.__lam * a_lu / 2.0)

        As1_lu = _safe_div(M_lu, z_lu * self.__fyd)

        # Supplément dû aux aciers comprimés
        delta_M = self.__med - M_lu
        if self.__is_T and not self._an_in_table:
            delta_M = (self.__med - self._Mf) - M_lu
            As1_lu += _safe_div(self._Mf, (self.__d - self.__hf / 2.0) * self.__fyd)

        As2 = self.As2
        return As1_lu + As2

    @property
    def As2(self) -> float:
        """Section d'acier comprimé requise As2 [mm²] (double armature).
        As2 = (Med − Mlu) / ((d − d') · σs2)
        avec σs2 = fyd (on suppose acier comprimé plastifié).
        """
        if not self.is_double:
            return 0.0
        if self.__fyd < _EPS or self.__d - self.__d_prime < _EPS:
            return 0.0

        b_calc = self.__bw if (self.__is_T and not self._an_in_table) else self.__b_elu
        M_lu = self.mu_lu * b_calc * self.__d ** 2 * self.__fcd

        delta_M = self.__med - M_lu
        if self.__is_T and not self._an_in_table:
            delta_M = (self.__med - self._Mf) - M_lu

        # On vérifie que l'acier comprimé est plastifié (hypothèse courante)
        sigma_s2 = self.__fyd  # simplification conservative
        return max(_safe_div(delta_M, (self.__d - self.__d_prime) * sigma_s2), 0.0)

    def get_As(self, with_values: bool = False) -> FormulaResult:
        r = self.As
        fv = ""
        if with_values:
            if not self.is_double:
                if self.__is_T and not self._an_in_table:
                    As_f = _safe_div(self._Mf, (self.__d - self.__hf / 2.0) * self.__fyd)
                    As_w = _safe_div(self.__med - self._Mf, self.z * self.__fyd)
                    fv = (
                        f"Section en T, AN dans l'âme — simple armature\n"
                        f"As,f = {self._Mf:.2f} / (({self.__d:.1f}−{self.__hf:.1f}/2)"
                        f"×{self.__fyd:.2f}) = {As_f:.2f} mm²\n"
                        f"As,w = ({self.__med:.2f}−{self._Mf:.2f}) / "
                        f"({self.z:.2f}×{self.__fyd:.2f}) = {As_w:.2f} mm²\n"
                        f"As = As,f + As,w = {r:.2f} mm²"
                    )
                else:
                    fv = (
                        f"Simple armature\n"
                        f"As = {self.__med:.2f} / ({self.z:.2f} × {self.__fyd:.2f})"
                        f" = {r:.2f} mm²"
                    )
            else:
                fv = (
                    f"Double armature (μbu={self.mu_bu:.4f} > μlu={self.mu_lu:.4f})\n"
                    f"As2 = {self.As2:.2f} mm²\n"
                    f"As1 = {r:.2f} mm²"
                )
        return FormulaResult(
            name="As",
            formula="As = Med / (z · fyd)  [simple]  ou  décomposition [double/T]",
            formula_values=fv,
            result=r,
            unit="mm²",
            ref="EC2 §6.1",
        )

    def get_As2(self, with_values: bool = False) -> FormulaResult:
        r = self.As2
        fv = ""
        if with_values:
            if self.is_double:
                b_calc = self.__bw if (self.__is_T and not self._an_in_table) else self.__b_elu
                M_lu = self.mu_lu * b_calc * self.__d ** 2 * self.__fcd
                delta_M = self.__med - M_lu
                fv = (
                    f"Mlu = {self.mu_lu:.4f}×{b_calc:.1f}×{self.__d:.1f}²"
                    f"×{self.__fcd:.2f} = {M_lu:.2f} N·mm\n"
                    f"ΔM = {self.__med:.2f} − {M_lu:.2f} = {delta_M:.2f} N·mm\n"
                    f"As2 = {delta_M:.2f} / (({self.__d:.1f}−{self.__d_prime:.1f})"
                    f"×{self.__fyd:.2f}) = {r:.2f} mm²"
                )
            else:
                fv = "Pas de double armature nécessaire → As2 = 0"
        return FormulaResult(
            name="As2",
            formula="As2 = ΔM / ((d − d') · fyd)",
            formula_values=fv,
            result=r,
            unit="mm²",
            ref="EC2 §6.1",
        )

    # --- A.8  As,min et As,max ---

    @property
    def As_min(self) -> float:
        """Section minimale d'armatures tendues As,min [mm²].
        EC2 §9.2.1.1 (1) :
        As,min = max(0.26·fctm/fyk·b·d  ;  0.0013·b·d)
        """
        bt = self.__b  # largeur de la zone tendue
        v1 = 0.26 * self.__fctm / self.__fyk * bt * self.__d if self.__fyk > 0 else 0.0
        v2 = 0.0013 * bt * self.__d
        return max(v1, v2)

    def get_As_min(self, with_values: bool = False) -> FormulaResult:
        r = self.As_min
        fv = ""
        if with_values:
            bt = self.__b
            v1 = 0.26 * self.__fctm / self.__fyk * bt * self.__d if self.__fyk > 0 else 0.0
            v2 = 0.0013 * bt * self.__d
            fv = (
                f"0.26×{self.__fctm:.2f}/{self.__fyk:.1f}×{bt:.1f}×{self.__d:.1f}"
                f" = {v1:.2f} mm²\n"
                f"0.0013×{bt:.1f}×{self.__d:.1f} = {v2:.2f} mm²\n"
                f"As,min = max({v1:.2f} ; {v2:.2f}) = {r:.2f} mm²"
            )
        return FormulaResult(
            name="As,min",
            formula="As,min = max(0.26·fctm/fyk·b·d ; 0.0013·b·d)",
            formula_values=fv,
            result=r,
            unit="mm²",
            ref="EC2 §9.2.1.1 (1)",
        )

    @property
    def As_max(self) -> float:
        """Section maximale d'armatures As,max = 0.04·Ac [mm²].
        EC2 §9.2.1.1 (3).
        """
        Ac = self.__b * self.__h if self.__h > 0 else self.__b * self.__d / 0.9
        return 0.04 * Ac

    def get_As_max(self, with_values: bool = False) -> FormulaResult:
        r = self.As_max
        fv = ""
        if with_values:
            Ac = self.__b * self.__h if self.__h > 0 else self.__b * self.__d / 0.9
            fv = f"As,max = 0.04 × {Ac:.2f} = {r:.2f} mm²"
        return FormulaResult(
            name="As,max",
            formula="As,max = 0.04 · Ac",
            formula_values=fv,
            result=r,
            unit="mm²",
            ref="EC2 §9.2.1.1 (3)",
        )

    @property
    def As_final(self) -> float:
        """Section d'acier tendu retenue (bornée par As,min et As,max) [mm²]."""
        return max(self.As, self.As_min)

    @property
    def As2_final(self) -> float:
        """Section d'acier comprimé retenue [mm²]."""
        return self.As2

    # ==================================================================
    #  B — ELS  (section fissurée)
    # ==================================================================

    def _els_rect_x(self, As: float, As2: float = 0.0) -> float:
        """Position de l'axe neutre ELS section fissurée rectangulaire [mm].
        b·x²/2 + n·As'·(x − d') = n·As·(d − x)
        → (b/2)·x² + n·(As + As')·x − n·(As·d + As'·d') = 0
        """
        n = self.__n_eq
        b = self.__b
        a_coef = b / 2.0
        b_coef = n * (As + As2)
        c_coef = -n * (As * self.__d + As2 * self.__d_prime)
        disc = b_coef ** 2 - 4.0 * a_coef * c_coef
        if disc < 0:
            return 0.0
        return (-b_coef + math.sqrt(disc)) / (2.0 * a_coef)

    def _els_T_x(self, As: float, As2: float = 0.0) -> float:
        """Position de l'axe neutre ELS section fissurée en T [mm].
        On distingue x ≤ hf (→ rect largeur beff) ou x > hf.
        """
        # Essai AN dans la table (rect beff)
        n = self.__n_eq
        beff = self.__beff
        bw = self.__bw
        hf = self.__hf

        a_coef = beff / 2.0
        b_coef = n * (As + As2)
        c_coef = -n * (As * self.__d + As2 * self.__d_prime)
        disc = b_coef ** 2 - 4.0 * a_coef * c_coef
        x_trial = (-b_coef + math.sqrt(max(disc, 0.0))) / (2.0 * a_coef) if a_coef > 0 else 0.0

        if x_trial <= hf:
            return x_trial

        # AN dans l'âme : bw·x²/2 + (beff−bw)·hf·(x − hf/2) + n·As'·(x−d') = n·As·(d−x)
        a_coef = bw / 2.0
        b_coef = (beff - bw) * hf + n * (As + As2)
        c_coef = -(beff - bw) * hf ** 2 / 2.0 - n * (As * self.__d + As2 * self.__d_prime)
        disc = b_coef ** 2 - 4.0 * a_coef * c_coef
        if disc < 0:
            return 0.0
        return (-b_coef + math.sqrt(disc)) / (2.0 * a_coef)

    def _els_x(self, As: float, As2: float = 0.0) -> float:
        """Position AN ELS selon forme."""
        if self.__is_T:
            return self._els_T_x(As, As2)
        return self._els_rect_x(As, As2)

    def _els_I_fiss(self, x: float, As: float, As2: float = 0.0) -> float:
        """Inertie fissurée I_fiss [mm⁴]."""
        n = self.__n_eq
        if self.__is_T and x > self.__hf:
            beff = self.__beff
            bw = self.__bw
            hf = self.__hf
            I = (bw * x ** 3 / 3.0
                 + (beff - bw) * hf ** 3 / 12.0
                 + (beff - bw) * hf * (x - hf / 2.0) ** 2
                 + n * As * (self.__d - x) ** 2
                 + n * As2 * (x - self.__d_prime) ** 2)
        else:
            b = self.__beff if self.__is_T else self.__b
            I = (b * x ** 3 / 3.0
                 + n * As * (self.__d - x) ** 2
                 + n * As2 * (x - self.__d_prime) ** 2)
        return I

    # --- Contraintes ELS ---

    @property
    def x_els(self) -> float:
        """Position AN ELS [mm] – utilise As_exist / As2_exist."""
        As = self.__As_exist if self.__As_exist > 0 else self.As_final
        As2 = self.__As2_exist if self.__As2_exist > 0 else self.As2_final
        return self._els_x(As, As2)

    @property
    def I_fiss(self) -> float:
        """Inertie fissurée [mm⁴]."""
        As = self.__As_exist if self.__As_exist > 0 else self.As_final
        As2 = self.__As2_exist if self.__As2_exist > 0 else self.As2_final
        x = self.x_els
        return self._els_I_fiss(x, As, As2)

    @property
    def sigma_c(self) -> float:
        """Contrainte béton fibre comprimée ELS σc [MPa].
        σc = Mels · x / I_fiss
        """
        if not self.__has_els:
            return 0.0
        I = self.I_fiss
        if I < _EPS:
            return float("inf")
        return self.__med_els * self.x_els / I

    @property
    def sigma_c_lim(self) -> float:
        """Contrainte béton limite ELS σc,lim = 0.6·fck [MPa].
        EC2 §7.2 (2).
        """
        return 0.6 * self.__fck

    @property
    def sigma_s(self) -> float:
        """Contrainte acier ELS σs [MPa].
        σs = n · Mels · (d − x) / I_fiss
        """
        if not self.__has_els:
            return 0.0
        I = self.I_fiss
        if I < _EPS:
            return float("inf")
        return self.__n_eq * self.__med_els * (self.__d - self.x_els) / I

    @property
    def sigma_s_lim(self) -> float:
        """Contrainte acier limite ELS σs,lim = 0.8·fyk [MPa].
        EC2 §7.2 (5).
        """
        return 0.8 * self.__fyk

    def get_sigma_c(self, with_values: bool = False) -> FormulaResult:
        r = self.sigma_c
        fv = ""
        if with_values:
            status = "OK ✓" if r <= self.sigma_c_lim else "NON VÉRIFIÉ ✗"
            fv = (
                f"x_els = {self.x_els:.2f} mm  ;  I_fiss = {self.I_fiss:.2f} mm⁴\n"
                f"σc = {self.__med_els:.2f} × {self.x_els:.2f} / {self.I_fiss:.2f}"
                f" = {r:.2f} MPa\n"
                f"σc,lim = 0.6 × {self.__fck:.1f} = {self.sigma_c_lim:.2f} MPa"
                f"  →  {status}"
            )
        return FormulaResult(
            name="σc",
            formula="σc = Mels · x / I_fiss  ≤  0.6·fck",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2 (2)",
        )

    def get_sigma_s(self, with_values: bool = False) -> FormulaResult:
        r = self.sigma_s
        fv = ""
        if with_values:
            status = "OK ✓" if r <= self.sigma_s_lim else "NON VÉRIFIÉ ✗"
            fv = (
                f"σs = {self.__n_eq:.2f} × {self.__med_els:.2f}"
                f" × ({self.__d:.1f} − {self.x_els:.2f})"
                f" / {self.I_fiss:.2f} = {r:.2f} MPa\n"
                f"σs,lim = 0.8 × {self.__fyk:.1f} = {self.sigma_s_lim:.2f} MPa"
                f"  →  {status}"
            )
        return FormulaResult(
            name="σs",
            formula="σs = n · Mels · (d − x) / I_fiss  ≤  0.8·fyk",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2 (5)",
        )

    # ==================================================================
    #  Vérifications globales
    # ==================================================================

    @property
    def verif(self) -> float:
        """Taux de travail ELU : μbu / μlu (simplifié).
        ≤ 1.0 signifie simple armature suffisante.
        """
        if self.mu_lu < _EPS:
            return float("inf")
        return round(self.mu_bu / self.mu_lu, 4)

    @property
    def is_ok(self) -> bool:
        """True si la section est vérifiée (As ≤ As,max et contraintes ELS ok)."""
        ok_elu = self.As_final <= self.As_max
        if self.__has_els:
            ok_els = (self.sigma_c <= self.sigma_c_lim and
                      self.sigma_s <= self.sigma_s_lim)
            return ok_elu and ok_els
        return ok_elu

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            mode = "simple armature" if not self.is_double else "double armature"
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"μbu/μlu = {self.mu_bu:.4f}/{self.mu_lu:.4f} = {r:.4f}"
                f"  →  {mode}\n"
                f"As = {self.As_final:.2f} mm²  (As,min={self.As_min:.2f},"
                f" As,max={self.As_max:.2f})\n"
                f"Vérification globale : {status}"
            )
        return FormulaResult(
            name="μbu/μlu",
            formula="μbu / μlu",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 §6.1",
        )

    # ==================================================================
    #  Report
    # ==================================================================

    def report(self, with_values: bool = True) -> FormulaCollection:
        """Rapport complet ELU + ELS."""
        fc = FormulaCollection(
            title="Flexion simple — ELU & ELS",
            ref="EC2 §6.1, §7.2",
        )
        # ELU
        fc.add(self.get_mu_lu(with_values=with_values))
        fc.add(self.get_mu_bu(with_values=with_values))
        fc.add(self.get_alpha_u(with_values=with_values))
        fc.add(self.get_z(with_values=with_values))
        fc.add(self.get_pivot(with_values=with_values))
        fc.add(self.get_As(with_values=with_values))
        if self.is_double:
            fc.add(self.get_As2(with_values=with_values))
        fc.add(self.get_As_min(with_values=with_values))
        fc.add(self.get_As_max(with_values=with_values))
        # ELS
        if self.__has_els:
            fc.add(self.get_sigma_c(with_values=with_values))
            fc.add(self.get_sigma_s(with_values=with_values))
        # Verif
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"Flexion(Med={self.__med:.2f} N·mm, "
            f"μbu={self.mu_bu:.4f}, μlu={self.mu_lu:.4f}, "
            f"As={self.As_final:.2f} mm², "
            f"ok={self.is_ok})"
        )


# ======================================================================
#  Fonctions standalone
# ======================================================================

def as_flexion_simple(
    Med: float,
    b: float,
    d: float,
    fcd: float,
    fyd: float,
    fck: float = 25.0,
    eud: float = 10.0e-3,
    d_prime: float = 0.0,
    bw: Optional[float] = None,
    beff: Optional[float] = None,
    hf: float = 0.0,
    fctm: float = 2.6,
    fyk: float = 500.0,
    h: float = 0.0,
) -> dict:
    """
    Calcul rapide de la section d'acier à la flexion simple ELU.

    Returns
    -------
    dict avec clés : 'As', 'As2', 'mu_bu', 'mu_lu', 'z', 'pivot',
                     'is_double', 'As_min', 'As_max'.
    """
    is_T = hf > 0 and beff is not None and bw is not None
    kw = dict(
        b=b, d=d, fcd=fcd, fyd=fyd, fck=fck, eud=eud,
        d_prime=d_prime, fctm=fctm, fyk=fyk, h=h,
        bw=bw if bw else b,
        beff=beff if beff else b,
        hf=hf, is_T=is_T,
        Es=200000.0, Ecm=33000.0,
    )
    f = Flexion(Med=Med, **kw)
    return {
        "As": f.As_final,
        "As2": f.As2_final,
        "mu_bu": f.mu_bu,
        "mu_lu": f.mu_lu,
        "z": f.z,
        "pivot": f.pivot,
        "is_double": f.is_double,
        "As_min": f.As_min,
        "As_max": f.As_max,
    }


def sigma_els(
    Med_els: float,
    b: float,
    d: float,
    As: float,
    fck: float = 25.0,
    Es: float = 200000.0,
    Ecm: float = 33000.0,
    As2: float = 0.0,
    d_prime: float = 0.0,
    fyk: float = 500.0,
    bw: Optional[float] = None,
    beff: Optional[float] = None,
    hf: float = 0.0,
) -> dict:
    """
    Calcul rapide des contraintes ELS (section fissurée).

    Returns
    -------
    dict avec clés : 'sigma_c', 'sigma_c_lim', 'sigma_s', 'sigma_s_lim',
                     'x_els', 'I_fiss'.
    """
    is_T = hf > 0 and beff is not None and bw is not None
    kw = dict(
        b=b, d=d, fck=fck, fyd=fyk / 1.15, fcd=fck / 1.5,
        fyk=fyk, Es=Es, Ecm=Ecm,
        d_prime=d_prime,
        bw=bw if bw else b,
        beff=beff if beff else b,
        hf=hf, is_T=is_T,
        As_exist=As, As2_exist=As2,
        h=0.0, fctm=0.0, eud=10e-3,
    )
    f = Flexion(Med=0.0, Med_els=Med_els, **kw)
    return {
        "sigma_c": f.sigma_c,
        "sigma_c_lim": f.sigma_c_lim,
        "sigma_s": f.sigma_s,
        "sigma_s_lim": f.sigma_s_lim,
        "x_els": f.x_els,
        "I_fiss": f.I_fiss,
    }


# ======================================================================
#  Debug / démonstration
# ======================================================================

if __name__ == "__main__":

    print("=" * 70)
    print("  EXEMPLE 1 — Section rectangulaire 300×500, C25/30, Med=150 kN·m")
    print("=" * 70)

    f1 = Flexion(
        Med=150e6,        # 150 kN·m → N·mm
        Med_els=100e6,    # 100 kN·m ELS
        b=300, h=500, d=460, d_prime=40,
        fck=25, fcd=25 / 1.5, fctm=2.6,
        fyk=500, fyd=500 / 1.15,
        Es=200000, Ecm=31000,
        eud=10e-3,
        is_T=False,
        As_exist=900,  # 3HA20 ≈ 942 mm² — pour vérif ELS
    )
    print(f1)
    print(f1.report(with_values=True))

    print("\n")
    print("=" * 70)
    print("  EXEMPLE 2 — Section en T  beff=800, bw=300, hf=120, h=500")
    print("              C30/37, Med=350 kN·m")
    print("=" * 70)

    f2 = Flexion(
        Med=350e6,
        Med_els=230e6,
        b=300, bw=300, beff=800, hf=120,
        h=500, d=450, d_prime=40,
        fck=30, fcd=30 / 1.5, fctm=2.9,
        fyk=500, fyd=500 / 1.15,
        Es=200000, Ecm=33000,
        eud=10e-3,
        is_T=True,
        As_exist=2000,
    )
    print(f2)
    print(f2.report(with_values=True))

    print("\n")
    print("=" * 70)
    print("  EXEMPLE 3 — Fonction standalone as_flexion_simple")
    print("=" * 70)
    res = as_flexion_simple(
        Med=200e6, b=300, d=460, fcd=25 / 1.5, fyd=500 / 1.15,
        fck=25, h=500, fctm=2.6,
    )
    for k, v in res.items():
        print(f"  {k:12s} = {v}")

    print("\n")
    print("=" * 70)
    print("  EXEMPLE 4 — Fonction standalone sigma_els")
    print("=" * 70)
    res_els = sigma_els(
        Med_els=100e6, b=300, d=460, As=1200,
        fck=25, Ecm=31000,
    )
    for k, v in res_els.items():
        print(f"  {k:12s} = {v:.2f}" if isinstance(v, float) else f"  {k:12s} = {v}")
