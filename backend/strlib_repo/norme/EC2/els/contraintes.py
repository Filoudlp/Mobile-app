#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC2 — Vérification des contraintes à l'ELS (EN 1992-1-1 §7.2)

Section rectangulaire ou en T, béton armé sans précontrainte.
Effort normal optionnel (flexion composée ELS).
Prise en compte optionnelle du fluage pour la combinaison quasi-permanente.
"""

__all__ = [
    "Contraintes",
    "x_fissure",
    "i_fissure",
    "sigma_beton",
    "sigma_acier",
    "moment_fissuration",
]

import math
from typing import TypeVar, Optional
from formula import FormulaResult, FormulaCollection

sec_mat_rc = TypeVar("sec_mat_rc")


# ═══════════════════════════════════════════════════════════════════════════════
# Fonctions utilitaires internes
# ═══════════════════════════════════════════════════════════════════════════════

def _solve_quadratic_positive(a: float, b_coef: float, c: float) -> float:
    """
    Résout a·x² + b·x + c = 0 et renvoie la racine positive.
    Retourne 0.0 si aucune racine positive n'existe ou si a == 0.
    """
    if a == 0:
        if b_coef == 0:
            return 0.0
        root = -c / b_coef
        return root if root > 0 else 0.0
    delta = b_coef ** 2 - 4 * a * c
    if delta < 0:
        return 0.0
    sqrt_delta = math.sqrt(delta)
    x1 = (-b_coef + sqrt_delta) / (2 * a)
    x2 = (-b_coef - sqrt_delta) / (2 * a)
    # Prendre la plus petite racine positive (physiquement l'axe neutre)
    positives = sorted([x for x in (x1, x2) if x > 0])
    return positives[0] if positives else 0.0


def _calc_x_rect(b: float, d: float, d_prime: float,
                 As1: float, As2: float, n: float) -> float:
    """
    Axe neutre fissuré — section rectangulaire (simple ou double armature).

    Trinôme : b·x² + 2·[(n-1)·As2 + n·As1]·x − 2·[(n-1)·As2·d' + n·As1·d] = 0
    Si As2 == 0, se réduit à : b·x² + 2·n·As1·x − 2·n·As1·d = 0
    """
    a = b
    b_coef = 2.0 * ((n - 1) * As2 + n * As1)
    c = -2.0 * ((n - 1) * As2 * d_prime + n * As1 * d)
    return _solve_quadratic_positive(a, b_coef, c)


def _calc_I_rect(b: float, x: float, d: float, d_prime: float,
                 As1: float, As2: float, n: float) -> float:
    """
    Inertie fissurée — section rectangulaire.

    I_fiss = b·x³/3 + (n-1)·As2·(x − d')² + n·As1·(d − x)²
    """
    return (b * x ** 3 / 3.0
            + (n - 1) * As2 * (x - d_prime) ** 2
            + n * As1 * (d - x) ** 2)


def _calc_x_T(beff: float, bw: float, hf: float,
              d: float, d_prime: float,
              As1: float, As2: float, n: float) -> float:
    """
    Axe neutre fissuré — section en T.

    1) On teste d'abord si x ≤ hf (axe neutre dans la table) :
       → calcul rectangulaire avec beff
    2) Sinon on résout le trinôme pour x > hf (axe neutre dans l'âme) :

       Équilibre des moments statiques par rapport à l'axe neutre :
       beff·hf·(x − hf/2) + bw·(x − hf)²/2 + (n−1)·As2·(x − d') = n·As1·(d − x)

       Développement en trinôme :
       bw/2·x² + [beff·hf − bw·hf + (n−1)·As2 + n·As1]·x
       − [beff·hf²/2 − bw·hf²/2 + (n−1)·As2·d' + n·As1·d] = 0

       Soit :
       a = bw
       b = 2·[(beff − bw)·hf + (n−1)·As2 + n·As1]
       c = −[(beff − bw)·hf² + 2·(n−1)·As2·d' + 2·n·As1·d]
    """
    # --- Tentative : axe neutre dans la table ---
    x_table = _calc_x_rect(beff, d, d_prime, As1, As2, n)
    if x_table <= hf:
        return x_table

    # --- Axe neutre dans l'âme ---
    db = beff - bw  # différence de largeurs
    a = bw
    b_coef = 2.0 * (db * hf + (n - 1) * As2 + n * As1)
    c = -(db * hf ** 2 + 2.0 * (n - 1) * As2 * d_prime + 2.0 * n * As1 * d)
    return _solve_quadratic_positive(a, b_coef, c)


def _calc_I_T(beff: float, bw: float, hf: float, x: float,
              d: float, d_prime: float,
              As1: float, As2: float, n: float) -> float:
    """
    Inertie fissurée — section en T.

    Si x ≤ hf : formule rectangulaire avec beff.
    Sinon :
        I = beff·hf³/12 + beff·hf·(x − hf/2)²
          + bw·(x − hf)³/3
          + (n−1)·As2·(x − d')²
          + n·As1·(d − x)²
    """
    if x <= hf:
        return _calc_I_rect(beff, x, d, d_prime, As1, As2, n)

    return (beff * hf ** 3 / 12.0
            + beff * hf * (x - hf / 2.0) ** 2
            + bw * (x - hf) ** 3 / 3.0
            + (n - 1) * As2 * (x - d_prime) ** 2
            + n * As1 * (d - x) ** 2)


def _calc_section_homogene(b: float, bw: float, beff: float, hf: float,
                           h: float, d: float, d_prime: float,
                           As1: float, As2: float, n: float,
                           is_T: bool) -> tuple:
    """
    Calcule x_hom et I_hom pour la section homogène non fissurée.
    Retourne (x_hom, I_hom).

    Section rectangulaire :
        A_hom = b·h + (n−1)·As1 + (n−1)·As2
        x_hom = [b·h·h/2 + (n−1)·As2·d' + (n−1)·As1·d] / A_hom   (depuis fibre sup.)
        I_hom = b·h³/12 + b·h·(x_hom − h/2)² + (n−1)·As2·(x_hom − d')² + (n−1)·As1·(d − x_hom)²

    Section en T :
        Décomposition en table (beff × hf) + âme (bw × (h − hf))
    """
    if not is_T:
        # Section rectangulaire
        A_c = b * h
        S_c = b * h * h / 2.0  # moment statique / fibre sup.
        A_hom = A_c + (n - 1) * As2 + (n - 1) * As1
        S_hom = S_c + (n - 1) * As2 * d_prime + (n - 1) * As1 * d
        if A_hom == 0:
            return 0.0, 0.0
        x_hom = S_hom / A_hom

        I_hom = (b * h ** 3 / 12.0
                 + b * h * (x_hom - h / 2.0) ** 2
                 + (n - 1) * As2 * (x_hom - d_prime) ** 2
                 + (n - 1) * As1 * (d - x_hom) ** 2)
        return x_hom, I_hom
    else:
        # Section en T
        h_ame = h - hf
        # Table
        A_table = beff * hf
        S_table = A_table * hf / 2.0
        I_table = beff * hf ** 3 / 12.0
        # Âme sous table
        A_ame = bw * h_ame
        y_ame = hf + h_ame / 2.0  # centre de l'âme depuis fibre sup.
        S_ame = A_ame * y_ame
        I_ame = bw * h_ame ** 3 / 12.0

        A_hom = A_table + A_ame + (n - 1) * As2 + (n - 1) * As1
        S_hom = S_table + S_ame + (n - 1) * As2 * d_prime + (n - 1) * As1 * d
        if A_hom == 0:
            return 0.0, 0.0
        x_hom = S_hom / A_hom

        I_hom = (I_table + A_table * (x_hom - hf / 2.0) ** 2
                 + I_ame + A_ame * (x_hom - y_ame) ** 2
                 + (n - 1) * As2 * (x_hom - d_prime) ** 2
                 + (n - 1) * As1 * (d - x_hom) ** 2)
        return x_hom, I_hom


# ═══════════════════════════════════════════════════════════════════════════════
# Classe principale
# ═══════════════════════════════════════════════════════════════════════════════

class Contraintes:
    """
    Vérification des contraintes à l'ELS — EN 1992-1-1 §7.2

    Combinaisons :
      • Caractéristique → σc ≤ k1·fck, σs ≤ k3·fyk
      • Quasi-permanente → σc ≤ k2·fck (fluage linéaire)

    Supporte :
      • Section rectangulaire (simple ou double armature)
      • Section en T
      • Effort normal optionnel (flexion composée ELS)
      • Fluage (coefficient φ_eff optionnel)

    Parameters
    ----------
    M_carac : float
        Moment sous combinaison caractéristique [N·mm]
    M_qp : float
        Moment sous combinaison quasi-permanente [N·mm]
    N_carac : float, optional
        Effort normal sous combinaison caractéristique [N] (+ = compression)
    N_qp : float, optional
        Effort normal sous combinaison quasi-permanente [N] (+ = compression)
    phi_eff : float, optional
        Coefficient de fluage effectif (défaut = 0 → pas de fluage)
    sec : sec_mat_rc, optional
        Objet SecMatRC portant toutes les propriétés
    **kwargs : dict
        Propriétés individuelles si sec n'est pas fourni
    """

    def __init__(
        self,
        M_carac: float,
        M_qp: float,
        N_carac: float = 0.0,
        N_qp: float = 0.0,
        phi_eff: float = 0.0,
        sec: Optional[sec_mat_rc] = None,
        **kwargs,
    ) -> None:

        # --- Sollicitations ---
        self.__m_carac = abs(M_carac)
        self.__m_qp = abs(M_qp)
        self.__n_carac = N_carac  # + = compression, signe conservé
        self.__n_qp = N_qp
        self.__phi_eff = phi_eff

        # --- Géométrie ---
        self.__b: float = sec.b if sec else kwargs.get("b", 0.0)
        self.__bw: float = sec.bw if sec else kwargs.get("bw", self.__b)
        self.__beff: float = sec.beff if sec else kwargs.get("beff", self.__b)
        self.__hf: float = sec.hf if sec else kwargs.get("hf", 0.0)
        self.__h: float = sec.h if sec else kwargs.get("h", 0.0)
        self.__d: float = sec.d if sec else kwargs.get("d", 0.0)
        self.__d_prime: float = sec.d_prime if sec else kwargs.get("d_prime", 0.0)

        # --- Béton ---
        self.__fck: float = sec.fck if sec else kwargs.get("fck", 0.0)
        self.__fctm: float = sec.fctm if sec else kwargs.get("fctm", 0.0)
        self.__Ecm: float = sec.Ecm if sec else kwargs.get("Ecm", 0.0)

        # --- Acier ---
        self.__fyk: float = sec.fyk if sec else kwargs.get("fyk", 0.0)
        self.__Es: float = sec.Es if sec else kwargs.get("Es", 200000.0)

        # --- Armatures ---
        self.__As1: float = sec.As1 if sec else kwargs.get("As1", 0.0)
        self.__As2: float = sec.As2 if sec else kwargs.get("As2", 0.0)

        # --- Coefficient d'équivalence ---
        self.__n: float = (
            sec.n if (sec and hasattr(sec, "n"))
            else kwargs.get("n", self.__Es / self.__Ecm if self.__Ecm != 0 else 0.0)
        )

        # --- Section en T ---
        self.__is_T: bool = (
            sec.is_T if (sec and hasattr(sec, "is_T"))
            else kwargs.get("is_T", False)
        )

        # --- Coefficients AN (§7.2) ---
        self.__k1: float = kwargs.get("k1", 0.6)
        self.__k2: float = kwargs.get("k2", 0.45)
        self.__k3: float = kwargs.get("k3", 0.8)
        self.__k4: float = kwargs.get("k4", 1.0)

        # --- Coefficient d'équivalence effectif (fluage) ---
        if self.__phi_eff > 0 and self.__Ecm > 0:
            Ec_eff = self.__Ecm / (1.0 + self.__phi_eff)
            self.__n_eff: float = self.__Es / Ec_eff if Ec_eff > 0 else self.__n
        else:
            self.__n_eff = self.__n

    # ═══════════════════════════════════════════════════════════════════════
    # Propriétés d'entrée (lecture seule)
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def m_carac(self) -> float:
        """Moment sous combinaison caractéristique [N·mm]"""
        return self.__m_carac

    @property
    def m_qp(self) -> float:
        """Moment sous combinaison quasi-permanente [N·mm]"""
        return self.__m_qp

    @property
    def n_coeff(self) -> float:
        """Coefficient d'équivalence instantané n = Es / Ecm"""
        return self.__n

    @property
    def n_eff(self) -> float:
        """Coefficient d'équivalence effectif n_eff = Es / Ec,eff (fluage)"""
        return self.__n_eff

    # ═══════════════════════════════════════════════════════════════════════
    # A — Section homogène non fissurée
    # ═══════════════════════════════════════════════════════════════════════

    def _homogene(self, n_val: float) -> tuple:
        """(x_hom, I_hom) avec coefficient d'équivalence n_val."""
        return _calc_section_homogene(
            self.__b, self.__bw, self.__beff, self.__hf,
            self.__h, self.__d, self.__d_prime,
            self.__As1, self.__As2, n_val, self.__is_T,
        )

    @property
    def x_hom(self) -> float:
        """Position de l'axe neutre de la section homogène non fissurée [mm]"""
        return self._homogene(self.__n)[0]

    @property
    def I_hom(self) -> float:
        """Inertie de la section homogène non fissurée [mm⁴]"""
        return self._homogene(self.__n)[1]

    @property
    def A_hom(self) -> float:
        """Aire homogénéisée de la section non fissurée [mm²]"""
        if not self.__is_T:
            return (self.__b * self.__h
                    + (self.__n - 1) * self.__As2
                    + (self.__n - 1) * self.__As1)
        else:
            return (self.__beff * self.__hf
                    + self.__bw * (self.__h - self.__hf)
                    + (self.__n - 1) * self.__As2
                    + (self.__n - 1) * self.__As1)

    # --- Moment de fissuration ---

    @property
    def mcr(self) -> float:
        """
        Moment de fissuration Mcr = fctm · I_hom / (h − x_hom)  [N·mm]
        EC2 §7.1 — le béton fissure quand σ_inf = fctm
        """
        x_h = self.x_hom
        denom = self.__h - x_h
        if denom <= 0 or self.I_hom == 0:
            return 0.0
        return self.__fctm * self.I_hom / denom

    def get_mcr(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour le moment de fissuration Mcr"""
        r = self.mcr
        fv = ""
        if with_values:
            fv = (
                f"Mcr = fctm · I_hom / (h − x_hom) = "
                f"{self.__fctm:.2f} × {self.I_hom:.0f} / "
                f"({self.__h:.1f} − {self.x_hom:.2f}) = {r:.0f} N·mm"
            )
        return FormulaResult(
            name="Mcr",
            formula="Mcr = fctm · I_hom / (h − x_hom)",
            formula_values=fv,
            result=r,
            unit="N·mm",
            ref="EC2 §7.1 — Moment de fissuration",
        )

    @property
    def is_fissure_carac(self) -> bool:
        """True si la section est fissurée sous combinaison caractéristique"""
        return self.__m_carac >= self.mcr

    @property
    def is_fissure_qp(self) -> bool:
        """True si la section est fissurée sous combinaison quasi-permanente"""
        return self.__m_qp >= self.mcr

    # ═══════════════════════════════════════════════════════════════════════
    # A — Axe neutre et inertie en section fissurée
    # ═══════════════════════════════════════════════════════════════════════

    def _calc_x(self, n_val: float) -> float:
        """Axe neutre fissuré avec coefficient d'équivalence n_val."""
        if self.__is_T:
            return _calc_x_T(
                self.__beff, self.__bw, self.__hf,
                self.__d, self.__d_prime,
                self.__As1, self.__As2, n_val,
            )
        else:
            return _calc_x_rect(
                self.__b, self.__d, self.__d_prime,
                self.__As1, self.__As2, n_val,
            )

    def _calc_I(self, x: float, n_val: float) -> float:
        """Inertie fissurée avec axe neutre x et coefficient d'équivalence n_val."""
        if self.__is_T:
            return _calc_I_T(
                self.__beff, self.__bw, self.__hf, x,
                self.__d, self.__d_prime,
                self.__As1, self.__As2, n_val,
            )
        else:
            return _calc_I_rect(
                self.__b, x, self.__d, self.__d_prime,
                self.__As1, self.__As2, n_val,
            )

    # --- Axe neutre fissuré (instantané) ---

    @property
    def x_fiss(self) -> float:
        """Position de l'axe neutre en section fissurée [mm] — coeff. instantané n"""
        return self._calc_x(self.__n)

    def get_x_fiss(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la position de l'axe neutre fissuré"""
        r = self.x_fiss
        fv = ""
        if with_values:
            if self.__As2 > 0:
                eq = (
                    f"b·x² + 2·[(n−1)·As2 + n·As1]·x − 2·[(n−1)·As2·d' + n·As1·d] = 0\n"
                    f"{self.__b:.1f}·x² + 2·[({self.__n:.2f}−1)×{self.__As2:.1f} + "
                    f"{self.__n:.2f}×{self.__As1:.1f}]·x − "
                    f"2·[({self.__n:.2f}−1)×{self.__As2:.1f}×{self.__d_prime:.1f} + "
                    f"{self.__n:.2f}×{self.__As1:.1f}×{self.__d:.1f}] = 0\n"
                    f"x = {r:.2f} mm"
                )
            else:
                eq = (
                    f"b·x² + 2·n·As1·x − 2·n·As1·d = 0\n"
                    f"{self.__b:.1f}·x² + 2×{self.__n:.2f}×{self.__As1:.1f}·x − "
                    f"2×{self.__n:.2f}×{self.__As1:.1f}×{self.__d:.1f} = 0\n"
                    f"x = {r:.2f} mm"
                )
            if self.__is_T and r > self.__hf:
                eq = f"[Section en T — Axe neutre dans l'âme (x > hf = {self.__hf:.1f})]\n" + eq
            elif self.__is_T:
                eq = f"[Section en T — Axe neutre dans la table (x ≤ hf = {self.__hf:.1f})]\n" + eq
            fv = eq
        return FormulaResult(
            name="x_fiss",
            formula="b·x² + 2·[…]·x − 2·[…] = 0  (trinôme)",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2 — Section fissurée homogénéisée",
        )

    # --- Inertie fissurée (instantané) ---

    @property
    def I_fiss(self) -> float:
        """Inertie de la section fissurée [mm⁴] — coeff. instantané n"""
        return self._calc_I(self.x_fiss, self.__n)

    def get_I_fiss(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour l'inertie fissurée"""
        r = self.I_fiss
        x = self.x_fiss
        fv = ""
        if with_values:
            if self.__is_T and x > self.__hf:
                fv = (
                    f"I_fiss = beff·hf³/12 + beff·hf·(x−hf/2)² + bw·(x−hf)³/3 "
                    f"+ (n−1)·As2·(x−d')² + n·As1·(d−x)²\n"
                    f"= {self.__beff:.1f}×{self.__hf:.1f}³/12 "
                    f"+ {self.__beff:.1f}×{self.__hf:.1f}×({x:.2f}−{self.__hf/2:.1f})² "
                    f"+ {self.__bw:.1f}×({x:.2f}−{self.__hf:.1f})³/3 "
                    f"+ ({self.__n:.2f}−1)×{self.__As2:.1f}×({x:.2f}−{self.__d_prime:.1f})² "
                    f"+ {self.__n:.2f}×{self.__As1:.1f}×({self.__d:.1f}−{x:.2f})²\n"
                    f"= {r:.0f} mm⁴"
                )
            else:
                b_used = self.__beff if self.__is_T else self.__b
                fv = (
                    f"I_fiss = b·x³/3 + (n−1)·As2·(x−d')² + n·As1·(d−x)²\n"
                    f"= {b_used:.1f}×{x:.2f}³/3 "
                    f"+ ({self.__n:.2f}−1)×{self.__As2:.1f}×({x:.2f}−{self.__d_prime:.1f})² "
                    f"+ {self.__n:.2f}×{self.__As1:.1f}×({self.__d:.1f}−{x:.2f})²\n"
                    f"= {r:.0f} mm⁴"
                )
        return FormulaResult(
            name="I_fiss",
            formula="I_fiss = b·x³/3 + (n−1)·As2·(x−d')² + n·As1·(d−x)²",
            formula_values=fv,
            result=r,
            unit="mm⁴",
            ref="EC2 — Section fissurée homogénéisée",
        )

    # --- Axe neutre et inertie fissurée avec fluage ---

    @property
    def x_fiss_fluage(self) -> float:
        """Position de l'axe neutre en section fissurée avec fluage [mm]"""
        return self._calc_x(self.__n_eff)

    @property
    def I_fiss_fluage(self) -> float:
        """Inertie de la section fissurée avec fluage [mm⁴]"""
        return self._calc_I(self.x_fiss_fluage, self.__n_eff)

    def get_x_fiss_fluage(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour la position de l'axe neutre fissuré (fluage)"""
        r = self.x_fiss_fluage
        fv = ""
        if with_values:
            fv = (
                f"Ec,eff = Ecm / (1 + φ_eff) = {self.__Ecm:.0f} / "
                f"(1 + {self.__phi_eff:.2f}) = {self.__Ecm / (1 + self.__phi_eff):.0f} MPa\n"
                f"n_eff = Es / Ec,eff = {self.__Es:.0f} / "
                f"{self.__Ecm / (1 + self.__phi_eff):.0f} = {self.__n_eff:.2f}\n"
                f"x_fiss,fluage = {r:.2f} mm"
            )
        return FormulaResult(
            name="x_fiss,fluage",
            formula="n_eff = Es / [Ecm/(1+φ_eff)] → trinôme avec n_eff",
            formula_values=fv,
            result=r,
            unit="mm",
            ref="EC2 §7.2 — Prise en compte du fluage",
        )

    def get_I_fiss_fluage(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour l'inertie fissurée (fluage)"""
        r = self.I_fiss_fluage
        fv = ""
        if with_values:
            fv = f"I_fiss,fluage = {r:.0f} mm⁴  (calculé avec n_eff = {self.__n_eff:.2f})"
        return FormulaResult(
            name="I_fiss,fluage",
            formula="I_fiss calculé avec n_eff au lieu de n",
            formula_values=fv,
            result=r,
            unit="mm⁴",
            ref="EC2 §7.2 — Prise en compte du fluage",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # B — Contraintes sous combinaison caractéristique
    # ═══════════════════════════════════════════════════════════════════════

    def _sigma_c(self, M: float, N: float, x: float, I: float) -> float:
        """Contrainte béton fibre sup. [MPa] — positive = compression"""
        if I == 0:
            return 0.0
        sigma = M * x / I
        # Ajout de l'effort normal (compression positive)
        if N != 0 and self.A_hom > 0:
            sigma += N / self.A_hom
        return sigma

    def _sigma_s(self, M: float, N: float, x: float, I: float,
                 n_val: float) -> float:
        """Contrainte acier tendu [MPa] — positive = traction"""
        if I == 0:
            return 0.0
        sigma = n_val * M * (self.__d - x) / I
        # Ajout de l'effort normal (traction = négatif de N si N compressif)
        if N != 0 and self.A_hom > 0:
            sigma -= n_val * N / self.A_hom  # N>0 comprime → réduit σs
        return sigma

    def _sigma_s2(self, M: float, N: float, x: float, I: float,
                  n_val: float) -> float:
        """Contrainte acier comprimé [MPa] — positive = compression"""
        if I == 0 or self.__As2 == 0:
            return 0.0
        sigma = (n_val - 1) * M * (x - self.__d_prime) / I
        if N != 0 and self.A_hom > 0:
            sigma += (n_val - 1) * N / self.A_hom
        return sigma

    # --- σc caractéristique ---

    @property
    def sigma_c_carac(self) -> float:
        """Contrainte béton sous combinaison caractéristique σc,carac [MPa]"""
        return self._sigma_c(
            self.__m_carac, self.__n_carac,
            self.x_fiss, self.I_fiss,
        )

    @property
    def sigma_c_carac_limit(self) -> float:
        """Limite σc caractéristique = k1 · fck [MPa] — EC2 §7.2(2)"""
        return self.__k1 * self.__fck

    def get_sigma_c_carac(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σc sous combinaison caractéristique"""
        r = self.sigma_c_carac
        lim = self.sigma_c_carac_limit
        fv = ""
        if with_values:
            ok = "OK ✓" if r <= lim else "NON VÉRIFIÉ ✗"
            fv = (
                f"σc,carac = M_carac · x / I_fiss"
            )
            if self.__n_carac != 0:
                fv += f" + N_carac / A_hom"
            fv += (
                f"\n= {self.__m_carac:.0f} × {self.x_fiss:.2f} / {self.I_fiss:.0f}"
            )
            if self.__n_carac != 0:
                fv += f" + {self.__n_carac:.0f} / {self.A_hom:.0f}"
            fv += (
                f"\n= {r:.2f} MPa\n"
                f"Limite : k1·fck = {self.__k1}×{self.__fck:.1f} = {lim:.2f} MPa\n"
                f"σc,carac / (k1·fck) = {r:.2f} / {lim:.2f} = "
                f"{r / lim:.4f} ≤ 1.0 → {ok}" if lim > 0
                else f"fck = 0 → vérification impossible"
            )
        return FormulaResult(
            name="σc,carac",
            formula="σc,carac = M_carac · x / I_fiss ≤ k1·fck",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2(2)",
        )

    # --- σs caractéristique ---

    @property
    def sigma_s_carac(self) -> float:
        """Contrainte acier tendu sous combinaison caractéristique σs,carac [MPa]"""
        return self._sigma_s(
            self.__m_carac, self.__n_carac,
            self.x_fiss, self.I_fiss, self.__n,
        )

    @property
    def sigma_s_carac_limit(self) -> float:
        """Limite σs caractéristique = k3 · fyk [MPa] — EC2 §7.2(5)"""
        return self.__k3 * self.__fyk

    def get_sigma_s_carac(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σs sous combinaison caractéristique"""
        r = self.sigma_s_carac
        lim = self.sigma_s_carac_limit
        fv = ""
        if with_values:
            ok = "OK ✓" if r <= lim else "NON VÉRIFIÉ ✗"
            fv = (
                f"σs,carac = n · M_carac · (d − x) / I_fiss\n"
                f"= {self.__n:.2f} × {self.__m_carac:.0f} × "
                f"({self.__d:.1f} − {self.x_fiss:.2f}) / {self.I_fiss:.0f}\n"
                f"= {r:.2f} MPa\n"
                f"Limite : k3·fyk = {self.__k3}×{self.__fyk:.1f} = {lim:.2f} MPa\n"
                f"σs,carac / (k3·fyk) = {r:.2f} / {lim:.2f} = "
                f"{r / lim:.4f} ≤ 1.0 → {ok}" if lim > 0
                else f"fyk = 0 → vérification impossible"
            )
        return FormulaResult(
            name="σs,carac",
            formula="σs,carac = n · M_carac · (d − x) / I_fiss ≤ k3·fyk",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2(5)",
        )

    # --- σs2 caractéristique (informatif) ---

    @property
    def sigma_s2_carac(self) -> float:
        """Contrainte acier comprimé sous combinaison caractéristique [MPa]"""
        return self._sigma_s2(
            self.__m_carac, self.__n_carac,
            self.x_fiss, self.I_fiss, self.__n,
        )

    def get_sigma_s2_carac(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σs2 sous combinaison caractéristique (informatif)"""
        r = self.sigma_s2_carac
        fv = ""
        if with_values:
            fv = (
                f"σs2,carac = (n−1) · M_carac · (x − d') / I_fiss\n"
                f"= ({self.__n:.2f}−1) × {self.__m_carac:.0f} × "
                f"({self.x_fiss:.2f} − {self.__d_prime:.1f}) / {self.I_fiss:.0f}\n"
                f"= {r:.2f} MPa (compression)"
            )
        return FormulaResult(
            name="σs2,carac",
            formula="σs2,carac = (n−1) · M_carac · (x − d') / I_fiss",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 — Informatif",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # C — Contraintes sous combinaison quasi-permanente
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def sigma_c_qp(self) -> float:
        """Contrainte béton sous combinaison quasi-permanente σc,qp [MPa]"""
        return self._sigma_c(
            self.__m_qp, self.__n_qp,
            self.x_fiss, self.I_fiss,
        )

    @property
    def sigma_c_qp_limit(self) -> float:
        """Limite σc quasi-permanente = k2 · fck [MPa] — EC2 §7.2(3)"""
        return self.__k2 * self.__fck

    def get_sigma_c_qp(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σc sous combinaison quasi-permanente"""
        r = self.sigma_c_qp
        lim = self.sigma_c_qp_limit
        fv = ""
        if with_values:
            ok = "OK ✓" if r <= lim else "NON VÉRIFIÉ ✗"
            fv = (
                f"σc,qp = M_qp · x / I_fiss\n"
                f"= {self.__m_qp:.0f} × {self.x_fiss:.2f} / {self.I_fiss:.0f}\n"
                f"= {r:.2f} MPa\n"
                f"Limite : k2·fck = {self.__k2}×{self.__fck:.1f} = {lim:.2f} MPa\n"
                f"σc,qp / (k2·fck) = {r:.2f} / {lim:.2f} = "
                f"{r / lim:.4f} ≤ 1.0 → {ok}" if lim > 0
                else f"fck = 0 → vérification impossible"
            )
        return FormulaResult(
            name="σc,qp",
            formula="σc,qp = M_qp · x / I_fiss ≤ k2·fck",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2(3)",
        )

    @property
    def sigma_s_qp(self) -> float:
        """Contrainte acier tendu sous combinaison quasi-permanente σs,qp [MPa]"""
        return self._sigma_s(
            self.__m_qp, self.__n_qp,
            self.x_fiss, self.I_fiss, self.__n,
        )

    def get_sigma_s_qp(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σs sous combinaison quasi-permanente"""
        r = self.sigma_s_qp
        fv = ""
        if with_values:
            fv = (
                f"σs,qp = n · M_qp · (d − x) / I_fiss\n"
                f"= {self.__n:.2f} × {self.__m_qp:.0f} × "
                f"({self.__d:.1f} − {self.x_fiss:.2f}) / {self.I_fiss:.0f}\n"
                f"= {r:.2f} MPa\n"
                f"(Pas de limite normative directe — valeur utile pour §7.3 fissuration)"
            )
        return FormulaResult(
            name="σs,qp",
            formula="σs,qp = n · M_qp · (d − x) / I_fiss",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2 — Entrée pour §7.3",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # D — Contraintes quasi-permanentes avec fluage
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def sigma_c_qp_fluage(self) -> float:
        """Contrainte béton QP avec fluage [MPa]"""
        x_fl = self.x_fiss_fluage
        I_fl = self.I_fiss_fluage
        return self._sigma_c(self.__m_qp, self.__n_qp, x_fl, I_fl)

    @property
    def sigma_s_qp_fluage(self) -> float:
        """Contrainte acier tendu QP avec fluage [MPa]"""
        x_fl = self.x_fiss_fluage
        I_fl = self.I_fiss_fluage
        return self._sigma_s(self.__m_qp, self.__n_qp, x_fl, I_fl, self.__n_eff)

    def get_sigma_c_qp_fluage(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σc QP avec fluage"""
        r = self.sigma_c_qp_fluage
        lim = self.sigma_c_qp_limit
        fv = ""
        if with_values:
            ok = "OK ✓" if r <= lim else "NON VÉRIFIÉ ✗"
            fv = (
                f"σc,qp,fluage = M_qp · x_fluage / I_fiss,fluage\n"
                f"= {self.__m_qp:.0f} × {self.x_fiss_fluage:.2f} / "
                f"{self.I_fiss_fluage:.0f}\n"
                f"= {r:.2f} MPa\n"
                f"Limite : k2·fck = {lim:.2f} MPa → "
                f"{r:.2f} / {lim:.2f} = {r / lim:.4f} ≤ 1.0 → {ok}" if lim > 0
                else f"fck = 0"
            )
        return FormulaResult(
            name="σc,qp,fluage",
            formula="σc,qp,fluage = M_qp · x_fluage / I_fiss,fluage ≤ k2·fck",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2(3) — avec fluage",
        )

    def get_sigma_s_qp_fluage(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult pour σs QP avec fluage"""
        r = self.sigma_s_qp_fluage
        fv = ""
        if with_values:
            fv = (
                f"σs,qp,fluage = n_eff · M_qp · (d − x_fluage) / I_fiss,fluage\n"
                f"= {self.__n_eff:.2f} × {self.__m_qp:.0f} × "
                f"({self.__d:.1f} − {self.x_fiss_fluage:.2f}) / "
                f"{self.I_fiss_fluage:.0f}\n"
                f"= {r:.2f} MPa"
            )
        return FormulaResult(
            name="σs,qp,fluage",
            formula="σs,qp,fluage = n_eff · M_qp · (d − x_fluage) / I_fiss,fluage",
            formula_values=fv,
            result=r,
            unit="MPa",
            ref="EC2 §7.2 — avec fluage, entrée pour §7.3",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # F — Synthèse des vérifications
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def taux_c_carac(self) -> float:
        """Taux σc,carac / (k1·fck)"""
        lim = self.sigma_c_carac_limit
        if lim == 0:
            return float("inf")
        return round(self.sigma_c_carac / lim, 4)

    @property
    def taux_c_qp(self) -> float:
        """Taux σc,qp / (k2·fck) — sans fluage"""
        lim = self.sigma_c_qp_limit
        if lim == 0:
            return float("inf")
        return round(self.sigma_c_qp / lim, 4)

    @property
    def taux_c_qp_fluage(self) -> float:
        """Taux σc,qp,fluage / (k2·fck)"""
        lim = self.sigma_c_qp_limit
        if lim == 0:
            return float("inf")
        return round(self.sigma_c_qp_fluage / lim, 4)

    @property
    def taux_s_carac(self) -> float:
        """Taux σs,carac / (k3·fyk)"""
        lim = self.sigma_s_carac_limit
        if lim == 0:
            return float("inf")
        return round(self.sigma_s_carac / lim, 4)

    @property
    def fluage_non_lineaire(self) -> bool:
        """True si σc,qp > k2·fck → fluage non linéaire à considérer"""
        return self.sigma_c_qp > self.sigma_c_qp_limit

    @property
    def is_ok(self) -> bool:
        """True si toutes les vérifications sont satisfaites"""
        return (
            self.taux_c_carac <= 1.0
            and self.taux_c_qp <= 1.0
            and self.taux_s_carac <= 1.0
        )

    @property
    def verif(self) -> float:
        """Taux de travail maximal (enveloppe)"""
        return max(self.taux_c_carac, self.taux_c_qp, self.taux_s_carac)

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        """FormulaResult — synthèse de la vérification"""
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"Taux béton carac.     : σc/{self.__k1}fck = "
                f"{self.sigma_c_carac:.2f}/{self.sigma_c_carac_limit:.2f} = "
                f"{self.taux_c_carac:.4f}\n"
                f"Taux béton QP         : σc/{self.__k2}fck = "
                f"{self.sigma_c_qp:.2f}/{self.sigma_c_qp_limit:.2f} = "
                f"{self.taux_c_qp:.4f}\n"
                f"Taux acier carac.     : σs/{self.__k3}fyk = "
                f"{self.sigma_s_carac:.2f}/{self.sigma_s_carac_limit:.2f} = "
                f"{self.taux_s_carac:.4f}\n"
                f"Fluage non linéaire   : {'OUI ⚠' if self.fluage_non_lineaire else 'NON'}\n"
                f"Taux max              : {r:.4f} ≤ 1.0 → {status}"
            )
            if self.__phi_eff > 0:
                fv += (
                    f"\n--- Avec fluage (φ_eff = {self.__phi_eff:.2f}) ---\n"
                    f"Taux béton QP fluage  : "
                    f"{self.sigma_c_qp_fluage:.2f}/{self.sigma_c_qp_limit:.2f} = "
                    f"{self.taux_c_qp_fluage:.4f}"
                )
        return FormulaResult(
            name="Vérif. ELS contraintes",
            formula="max(σc,carac/k1fck ; σc,qp/k2fck ; σs,carac/k3fyk) ≤ 1.0",
            formula_values=fv,
            result=r,
            unit="-",
            ref="EC2 §7.2",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Rapport complet
    # ═══════════════════════════════════════════════════════════════════════

    def report(self, with_values: bool = True) -> FormulaCollection:
        """
        Génère un FormulaCollection regroupant toutes les étapes du calcul.
        """
        fc = FormulaCollection(
            title="Vérification des contraintes ELS",
            ref="EC2 §7.2",
        )

        # E — Section non fissurée
        fc.add(self.get_mcr(with_values=with_values))

        # A — Section fissurée
        fc.add(self.get_x_fiss(with_values=with_values))
        fc.add(self.get_I_fiss(with_values=with_values))

        # B — Contraintes caractéristiques
        fc.add(self.get_sigma_c_carac(with_values=with_values))
        fc.add(self.get_sigma_s_carac(with_values=with_values))
        if self.__As2 > 0:
            fc.add(self.get_sigma_s2_carac(with_values=with_values))

        # C — Contraintes quasi-permanentes
        fc.add(self.get_sigma_c_qp(with_values=with_values))
        fc.add(self.get_sigma_s_qp(with_values=with_values))

        # D — Fluage (si activé)
        if self.__phi_eff > 0:
            fc.add(self.get_x_fiss_fluage(with_values=with_values))
            fc.add(self.get_I_fiss_fluage(with_values=with_values))
            fc.add(self.get_sigma_c_qp_fluage(with_values=with_values))
            fc.add(self.get_sigma_s_qp_fluage(with_values=with_values))

        # F — Synthèse
        fc.add(self.get_verif(with_values=with_values))

        return fc

    def __repr__(self) -> str:
        return (
            f"Contraintes(σc_carac={self.sigma_c_carac:.2f} MPa, "
            f"σs_carac={self.sigma_s_carac:.2f} MPa, "
            f"σc_qp={self.sigma_c_qp:.2f} MPa, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Fonctions standalone
# ═══════════════════════════════════════════════════════════════════════════════

def x_fissure(
    b: float,
    d: float,
    As1: float,
    n: float,
    As2: float = 0.0,
    d_prime: float = 0.0,
    is_T: bool = False,
    bw: float = 0.0,
    beff: float = 0.0,
    hf: float = 0.0,
) -> float:
    """
    Calcul rapide de la position de l'axe neutre fissuré [mm].

    Parameters
    ----------
    b : float       Largeur section rectangulaire [mm] (ignoré si is_T)
    d : float       Hauteur utile [mm]
    As1 : float     Armature tendue [mm²]
    n : float       Coefficient d'équivalence Es/Ecm
    As2 : float     Armature comprimée [mm²]
    d_prime : float Enrobage armature comprimée [mm]
    is_T : bool     Section en T
    bw : float      Largeur de l'âme [mm]
    beff : float    Largeur efficace de la table [mm]
    hf : float      Épaisseur de la table [mm]

    Returns
    -------
    float : x [mm]
    """
    if is_T:
        return _calc_x_T(beff, bw, hf, d, d_prime, As1, As2, n)
    return _calc_x_rect(b, d, d_prime, As1, As2, n)


def i_fissure(
    b: float,
    d: float,
    As1: float,
    n: float,
    As2: float = 0.0,
    d_prime: float = 0.0,
    is_T: bool = False,
    bw: float = 0.0,
    beff: float = 0.0,
    hf: float = 0.0,
) -> float:
    """
    Calcul rapide de l'inertie fissurée [mm⁴].

    Returns
    -------
    float : I_fiss [mm⁴]
    """
    x = x_fissure(b, d, As1, n, As2, d_prime, is_T, bw, beff, hf)
    if is_T:
        return _calc_I_T(beff, bw, hf, x, d, d_prime, As1, As2, n)
    return _calc_I_rect(b, x, d, d_prime, As1, As2, n)


def sigma_beton(
    M: float,
    b: float,
    d: float,
    As1: float,
    n: float,
    As2: float = 0.0,
    d_prime: float = 0.0,
    is_T: bool = False,
    bw: float = 0.0,
    beff: float = 0.0,
    hf: float = 0.0,
) -> float:
    """
    Contrainte béton fibre comprimée [MPa].

    Parameters
    ----------
    M : float   Moment [N·mm]
    """
    x = x_fissure(b, d, As1, n, As2, d_prime, is_T, bw, beff, hf)
    I = i_fissure(b, d, As1, n, As2, d_prime, is_T, bw, beff, hf)
    if I == 0:
        return 0.0
    return abs(M) * x / I


def sigma_acier(
    M: float,
    b: float,
    d: float,
    As1: float,
    n: float,
    As2: float = 0.0,
    d_prime: float = 0.0,
    is_T: bool = False,
    bw: float = 0.0,
    beff: float = 0.0,
    hf: float = 0.0,
) -> float:
    """
    Contrainte acier tendu [MPa].

    Parameters
    ----------
    M : float   Moment [N·mm]
    """
    x = x_fissure(b, d, As1, n, As2, d_prime, is_T, bw, beff, hf)
    I = i_fissure(b, d, As1, n, As2, d_prime, is_T, bw, beff, hf)
    if I == 0:
        return 0.0
    return n * abs(M) * (d - x) / I


def moment_fissuration(
    fctm: float,
    b: float,
    h: float,
    d: float,
    As1: float,
    n: float,
    As2: float = 0.0,
    d_prime: float = 0.0,
    is_T: bool = False,
    bw: float = 0.0,
    beff: float = 0.0,
    hf: float = 0.0,
) -> float:
    """
    Moment de fissuration Mcr = fctm · I_hom / (h − x_hom) [N·mm].
    """
    x_hom, I_hom = _calc_section_homogene(
        b, bw, beff, hf, h, d, d_prime, As1, As2, n, is_T,
    )
    denom = h - x_hom
    if denom <= 0 or I_hom == 0:
        return 0.0
    return fctm * I_hom / denom


# ═══════════════════════════════════════════════════════════════════════════════
# Bloc de démonstration
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    separator = "=" * 80

    # ─────────────────────────────────────────────────────────────────────────
    # CAS 1 : Section rectangulaire, simple armature
    # ─────────────────────────────────────────────────────────────────────────
    print(separator)
    print("CAS 1 — Section rectangulaire, simple armature")
    print(separator)

    # Données :
    #   Section 300×500, enrobage 35 mm → d = 460 mm
    #   C25/30 : fck=25, fctm=2.6, Ecm=31000
    #   B500B  : fyk=500, Es=200000
    #   As1 = 1520 mm² (4HA22), As2 = 0
    #   M_carac = 180 kN·m, M_qp = 120 kN·m

    cas1 = Contraintes(
        M_carac=180e6,       # N·mm
        M_qp=120e6,          # N·mm
        b=300,               # mm
        h=500,               # mm
        d=460,               # mm
        d_prime=40,          # mm
        fck=25,              # MPa
        fctm=2.6,            # MPa
        Ecm=31000,           # MPa
        fyk=500,             # MPa
        Es=200000,           # MPa
        As1=1520,            # mm² (4HA22)
        As2=0,               # mm²
        is_T=False,
    )

    print(f"\nn = Es/Ecm = {cas1.n_coeff:.2f}")
    print(f"Mcr = {cas1.mcr / 1e6:.2f} kN·m")
    print(f"Section fissurée sous carac. : {cas1.is_fissure_carac}")
    print(f"Section fissurée sous QP     : {cas1.is_fissure_qp}")
    print()

    # Rapport complet
    rapport1 = cas1.report(with_values=True)
    for item in rapport1:
        print(f"--- {item.name} ---")
        print(f"  Formule : {item.formula}")
        if item.formula_values:
            for line in item.formula_values.split("\n"):
                print(f"  {line}")
        print(f"  Résultat : {item.result:.4f} {item.unit}")
        print(f"  Réf. : {item.ref}")
        print()

    print(repr(cas1))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # CAS 2 : Section rectangulaire, double armature + fluage
    # ─────────────────────────────────────────────────────────────────────────
    print(separator)
    print("CAS 2 — Section rectangulaire, double armature + fluage")
    print(separator)

    # Données :
    #   Section 300×600, d = 550 mm, d' = 50 mm
    #   C30/37 : fck=30, fctm=2.9, Ecm=33000
    #   B500B  : fyk=500, Es=200000
    #   As1 = 2260 mm² (4HA25+2HA16), As2 = 402 mm² (2HA16)
    #   M_carac = 300 kN·m, M_qp = 200 kN·m
    #   φ_eff = 2.0

    cas2 = Contraintes(
        M_carac=300e6,
        M_qp=200e6,
        phi_eff=2.0,
        b=300,
        h=600,
        d=550,
        d_prime=50,
        fck=30,
        fctm=2.9,
        Ecm=33000,
        fyk=500,
        Es=200000,
        As1=2260,
        As2=402,
        is_T=False,
    )

    print(f"\nn = {cas2.n_coeff:.2f}")
    print(f"n_eff (fluage) = {cas2.n_eff:.2f}")
    print(f"Mcr = {cas2.mcr / 1e6:.2f} kN·m")
    print()

    rapport2 = cas2.report(with_values=True)
    for item in rapport2:
        print(f"--- {item.name} ---")
        print(f"  Formule : {item.formula}")
        if item.formula_values:
            for line in item.formula_values.split("\n"):
                print(f"  {line}")
        print(f"  Résultat : {item.result:.4f} {item.unit}")
        print(f"  Réf. : {item.ref}")
        print()

    print(repr(cas2))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # CAS 3 : Section en T — axe neutre dans la table
    # ─────────────────────────────────────────────────────────────────────────
    print(separator)
    print("CAS 3 — Section en T — axe neutre dans la table")
    print(separator)

    # Données :
    #   beff=800, bw=300, hf=150, h=500, d=450, d'=50
    #   C25/30, B500B
    #   As1 = 1232 mm² (4HA20), As2 = 0
    #   M_carac = 150 kN·m, M_qp = 100 kN·m
    #   → Avec beff large et moment modéré, x devrait rester dans la table

    cas3 = Contraintes(
        M_carac=150e6,
        M_qp=100e6,
        b=300,          # ignoré pour T mais conservé par cohérence
        bw=300,
        beff=800,
        hf=150,
        h=500,
        d=450,
        d_prime=50,
        fck=25,
        fctm=2.6,
        Ecm=31000,
        fyk=500,
        Es=200000,
        As1=1232,
        As2=0,
        is_T=True,
    )

    print(f"\nn = {cas3.n_coeff:.2f}")
    x3 = cas3.x_fiss
    print(f"x_fiss = {x3:.2f} mm (hf = 150 mm → {'dans la table' if x3 <= 150 else 'dans l âme'})")
    print(f"I_fiss = {cas3.I_fiss:.0f} mm⁴")
    print(f"Mcr = {cas3.mcr / 1e6:.2f} kN·m")
    print()

    rapport3 = cas3.report(with_values=True)
    for item in rapport3:
        print(f"--- {item.name} ---")
        print(f"  Formule : {item.formula}")
        if item.formula_values:
            for line in item.formula_values.split("\n"):
                print(f"  {line}")
        print(f"  Résultat : {item.result:.4f} {item.unit}")
        print(f"  Réf. : {item.ref}")
        print()

    print(repr(cas3))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # CAS 4 : Section en T — axe neutre dans l'âme
    # ─────────────────────────────────────────────────────────────────────────
    print(separator)
    print("CAS 4 — Section en T — axe neutre dans l'âme")
    print(separator)

    # Données :
    #   beff=1000, bw=250, hf=120, h=600, d=550, d'=50
    #   C30/37, B500B
    #   As1 = 3216 mm² (4HA32), As2 = 402 mm² (2HA16)
    #   M_carac = 450 kN·m, M_qp = 300 kN·m
    #   → Fort taux d'armatures et âme étroite → x devrait dépasser hf

    cas4 = Contraintes(
        M_carac=450e6,
        M_qp=300e6,
        b=250,
        bw=250,
        beff=1000,
        hf=120,
        h=600,
        d=550,
        d_prime=50,
        fck=30,
        fctm=2.9,
        Ecm=33000,
        fyk=500,
        Es=200000,
        As1=3216,
        As2=402,
        is_T=True,
    )

    print(f"\nn = {cas4.n_coeff:.2f}")
    x4 = cas4.x_fiss
    print(f"x_fiss = {x4:.2f} mm (hf = 120 mm → {'dans la table' if x4 <= 120 else 'dans l âme'})")
    print(f"I_fiss = {cas4.I_fiss:.0f} mm⁴")
    print(f"Mcr = {cas4.mcr / 1e6:.2f} kN·m")
    print()

    rapport4 = cas4.report(with_values=True)
    for item in rapport4:
        print(f"--- {item.name} ---")
        print(f"  Formule : {item.formula}")
        if item.formula_values:
            for line in item.formula_values.split("\n"):
                print(f"  {line}")
        print(f"  Résultat : {item.result:.4f} {item.unit}")
        print(f"  Réf. : {item.ref}")
        print()

    print(repr(cas4))
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # Test des fonctions standalone
    # ─────────────────────────────────────────────────────────────────────────
    print(separator)
    print("FONCTIONS STANDALONE — vérification rapide")
    print(separator)

    # Reprise du cas 1 en standalone
    n_val = 200000 / 31000
    x_st = x_fissure(b=300, d=460, As1=1520, n=n_val)
    I_st = i_fissure(b=300, d=460, As1=1520, n=n_val)
    sc = sigma_beton(M=180e6, b=300, d=460, As1=1520, n=n_val)
    ss = sigma_acier(M=180e6, b=300, d=460, As1=1520, n=n_val)
    mcr_st = moment_fissuration(fctm=2.6, b=300, h=500, d=460, As1=1520, n=n_val)

    print(f"\nCas 1 (standalone) :")
    print(f"  x_fiss  = {x_st:.2f} mm   (classe: {cas1.x_fiss:.2f} mm)")
    print(f"  I_fiss  = {I_st:.0f} mm⁴  (classe: {cas1.I_fiss:.0f} mm⁴)")
    print(f"  σc      = {sc:.2f} MPa    (classe: {cas1.sigma_c_carac:.2f} MPa)")
    print(f"  σs      = {ss:.2f} MPa    (classe: {cas1.sigma_s_carac:.2f} MPa)")
    print(f"  Mcr     = {mcr_st / 1e6:.2f} kN·m (classe: {cas1.mcr / 1e6:.2f} kN·m)")

    # Reprise du cas 4 (T, âme) en standalone
    x_st4 = x_fissure(
        b=250, d=550, As1=3216, n=200000/33000,
        As2=402, d_prime=50,
        is_T=True, bw=250, beff=1000, hf=120,
    )
    I_st4 = i_fissure(
        b=250, d=550, As1=3216, n=200000/33000,
        As2=402, d_prime=50,
        is_T=True, bw=250, beff=1000, hf=120,
    )
    print(f"\nCas 4 (standalone) :")
    print(f"  x_fiss  = {x_st4:.2f} mm   (classe: {cas4.x_fiss:.2f} mm)")
    print(f"  I_fiss  = {I_st4:.0f} mm⁴  (classe: {cas4.I_fiss:.0f} mm⁴)")

    print(f"\n{separator}")
    print("Tous les cas de test exécutés avec succès.")
    print(separator)

