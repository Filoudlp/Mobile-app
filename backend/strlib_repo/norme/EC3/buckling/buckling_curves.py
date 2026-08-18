#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EC3-1-1 — Courbes de flambement et fonctions utilitaires communes.

Contient :
- Facteurs d'imperfection (Tableau 6.1)
- Sélection automatique des courbes de flambement (Tableau 6.2)
- Sélection automatique des courbes de déversement (Tableaux 6.4 / 6.5)
- Calcul de Φ, χ (flambement) et Φ_LT, χ_LT (déversement)
- Helpers longueur de flambement
"""

__all__ = [
    "IMPERFECTION_FACTORS",
    "get_imperfection_factor",
    "get_buckling_curve",
    "get_lt_buckling_curve",
    "phi",
    "phi_LT",
    "chi",
    "chi_LT",
    "buckling_length_factor",
    "buckling_length",
]

import math
from typing import Optional, Dict, Tuple

# ---------------------------------------------------------------------------
# Tableau 6.1 — Facteurs d'imperfection α
# ---------------------------------------------------------------------------
IMPERFECTION_FACTORS: Dict[str, float] = {
    "a0": 0.13,
    "a":  0.21,
    "b":  0.34,
    "c":  0.49,
    "d":  0.76,
}

# ---------------------------------------------------------------------------
# Tableau 6.2 — Courbes de flambement par flexion
# ---------------------------------------------------------------------------
# Clé : (section_type, fabrication, axis, condition)
#   condition = "hb_le_1.2"  → h/b ≤ 1.2
#               "hb_gt_1.2"  → h/b > 1.2
#               "tf_le_40"   → tf ≤ 40 mm
#               "tf_gt_40"   → tf > 40 mm
#               "any"        → pas de condition supplémentaire
#
# Pour les profilés laminés I/H la norme croise h/b et tf :
#   h/b > 1.2  ⇒  tf ≤ 40 : y→a, z→b  |  tf > 40 : y→b, z→c
#   h/b ≤ 1.2  ⇒  tf ≤ 100: y→b, z→c  |  tf > 100: y→d, z→d
# Pour simplifier, on expose deux conditions combinées.

_BUCKLING_CURVE_TABLE: Dict[Tuple[str, str, str, str], str] = {
    # --- Profilés laminés I/H, h/b > 1.2 ---
    ("I", "rolled", "y", "hb_gt_1.2_tf_le_40"):  "a",
    ("I", "rolled", "z", "hb_gt_1.2_tf_le_40"):  "b",
    ("I", "rolled", "y", "hb_gt_1.2_tf_gt_40"):  "b",
    ("I", "rolled", "z", "hb_gt_1.2_tf_gt_40"):  "c",
    ("H", "rolled", "y", "hb_gt_1.2_tf_le_40"):  "a",
    ("H", "rolled", "z", "hb_gt_1.2_tf_le_40"):  "b",
    ("H", "rolled", "y", "hb_gt_1.2_tf_gt_40"):  "b",
    ("H", "rolled", "z", "hb_gt_1.2_tf_gt_40"):  "c",
    # --- Profilés laminés I/H, h/b ≤ 1.2 ---
    ("I", "rolled", "y", "hb_le_1.2_tf_le_100"): "b",
    ("I", "rolled", "z", "hb_le_1.2_tf_le_100"): "c",
    ("I", "rolled", "y", "hb_le_1.2_tf_gt_100"): "d",
    ("I", "rolled", "z", "hb_le_1.2_tf_gt_100"): "d",
    ("H", "rolled", "y", "hb_le_1.2_tf_le_100"): "b",
    ("H", "rolled", "z", "hb_le_1.2_tf_le_100"): "c",
    ("H", "rolled", "y", "hb_le_1.2_tf_gt_100"): "d",
    ("H", "rolled", "z", "hb_le_1.2_tf_gt_100"): "d",
    # --- Profilés soudés I/H ---
    ("I", "welded", "y", "tf_le_40"):  "b",
    ("I", "welded", "z", "tf_le_40"):  "c",
    ("I", "welded", "y", "tf_gt_40"):  "c",
    ("I", "welded", "z", "tf_gt_40"):  "d",
    ("H", "welded", "y", "tf_le_40"):  "b",
    ("H", "welded", "z", "tf_le_40"):  "c",
    ("H", "welded", "y", "tf_gt_40"):  "c",
    ("H", "welded", "z", "tf_gt_40"):  "d",
    # --- Tubes creux ---
    ("RHS", "rolled",  "y", "any"): "a",
    ("RHS", "rolled",  "z", "any"): "a",
    ("RHS", "welded",  "y", "any"): "b",
    ("RHS", "welded",  "z", "any"): "b",
    ("CHS", "rolled",  "y", "any"): "a",
    ("CHS", "rolled",  "z", "any"): "a",
    ("CHS", "welded",  "y", "any"): "b",
    ("CHS", "welded",  "z", "any"): "b",
    # --- Profils en U ---
    ("U", "rolled",  "y", "any"): "b",
    ("U", "rolled",  "z", "any"): "c",
    ("U", "welded",  "y", "any"): "c",
    ("U", "welded",  "z", "any"): "d",
    # --- Profils en L ---
    ("L", "rolled",  "y", "any"): "b",
    ("L", "rolled",  "z", "any"): "b",
    ("L", "welded",  "y", "any"): "c",
    ("L", "welded",  "z", "any"): "c",
    # --- Profils en T ---
    ("T", "rolled",  "y", "any"): "b",
    ("T", "rolled",  "z", "any"): "c",
    ("T", "welded",  "y", "any"): "c",
    ("T", "welded",  "z", "any"): "d",
}

# ---------------------------------------------------------------------------
# Tableaux 6.4 / 6.5 — Courbes de déversement
# ---------------------------------------------------------------------------
# Méthode générale §6.3.2.2 — Tableau 6.4
_LT_CURVE_GENERAL: Dict[str, str] = {
    "I":   "b",
    "H":   "c",
    "RHS": "d",
    "CHS": "d",
    "U":   "d",
    "L":   "d",
    "T":   "d",
}

# Méthode profilés laminés §6.3.2.3 — Tableau 6.5
# Clé : condition sur h/b → courbe
_LT_CURVE_ROLLED: Dict[str, str] = {
    "hb_le_2": "b",
    "hb_gt_2": "c",
}

# ---------------------------------------------------------------------------
# Conditions d'appui → coefficient k de longueur de flambement (Euler)
# ---------------------------------------------------------------------------
_K_FACTORS: Dict[Tuple[str, str], float] = {
    ("fixed",  "fixed"):  0.5,
    ("fixed",  "pinned"): 0.7,
    ("pinned", "fixed"):  0.7,
    ("pinned", "pinned"): 1.0,
    ("fixed",  "free"):   2.0,
    ("free",   "fixed"):  2.0,
    ("fixed",  "slide"):  1.0,
    ("slide",  "fixed"):  1.0,
}


# ===================================================================
#  Fonctions publiques
# ===================================================================

def get_imperfection_factor(curve: str) -> float:
    """
    Retourne le facteur d'imperfection α pour la courbe de flambement donnée.

    :param curve: Nom de la courbe ('a0', 'a', 'b', 'c', 'd')
    :return: α
    :raises ValueError: si la courbe est inconnue.

    Ref: EC3-1-1 — Tableau 6.1
    """
    curve = curve.lower().strip()
    if curve not in IMPERFECTION_FACTORS:
        raise ValueError(
            f"Courbe '{curve}' inconnue. "
            f"Valeurs admises : {list(IMPERFECTION_FACTORS.keys())}"
        )
    return IMPERFECTION_FACTORS[curve]


def _resolve_condition_flexural(
    section_type: str,
    fabrication: str,
    h: float,
    b: float,
    tf: float,
) -> str:
    """Détermine la clé *condition* du dictionnaire ``_BUCKLING_CURVE_TABLE``."""
    st = section_type.upper()
    fab = fabrication.lower()

    if st in ("RHS", "CHS", "L", "U", "T"):
        return "any"

    # Profilés I/H
    if fab == "rolled":
        ratio_hb = h / b if b > 0 else 999.0
        if ratio_hb > 1.2:
            return "hb_gt_1.2_tf_le_40" if tf <= 40 else "hb_gt_1.2_tf_gt_40"
        else:
            return "hb_le_1.2_tf_le_100" if tf <= 100 else "hb_le_1.2_tf_gt_100"
    elif fab == "welded":
        return "tf_le_40" if tf <= 40 else "tf_gt_40"
    else:
        raise ValueError(f"Fabrication '{fabrication}' inconnue (attendu 'rolled' ou 'welded').")


def get_buckling_curve(
    section_type: str,
    fabrication: str,
    axis: str,
    h: float = 0.0,
    b: float = 0.0,
    tf: float = 0.0,
) -> str:
    """
    Détermine la courbe de flambement selon le Tableau 6.2.

    :param section_type: Type de section ('I', 'H', 'RHS', 'CHS', 'U', 'L', 'T')
    :param fabrication: 'rolled' ou 'welded'
    :param axis: 'y' ou 'z'
    :param h: Hauteur du profilé [mm]
    :param b: Largeur du profilé [mm]
    :param tf: Épaisseur de semelle [mm]
    :return: Nom de la courbe ('a0', 'a', 'b', 'c', 'd')
    :raises ValueError: si la combinaison n'est pas trouvée.

    Ref: EC3-1-1 — Tableau 6.2
    """
    st = section_type.upper()
    fab = fabrication.lower()
    ax = axis.lower()
    cond = _resolve_condition_flexural(st, fab, h, b, tf)
    key = (st, fab, ax, cond)
    if key not in _BUCKLING_CURVE_TABLE:
        raise ValueError(
            f"Pas de courbe de flambement pour la combinaison "
            f"({st}, {fab}, {ax}, {cond}). Vérifiez les paramètres."
        )
    return _BUCKLING_CURVE_TABLE[key]


def get_lt_buckling_curve(
    section_type: str,
    h: float = 0.0,
    b: float = 0.0,
    method: str = "general",
) -> str:
    """
    Détermine la courbe de déversement.

    :param section_type: Type de section ('I', 'H', 'RHS', 'CHS', 'U', 'L', 'T')
    :param h: Hauteur du profilé [mm]
    :param b: Largeur du profilé [mm]
    :param method: 'general' (§6.3.2.2, Tab 6.4) ou 'rolled' (§6.3.2.3, Tab 6.5)
    :return: Nom de la courbe
    :raises ValueError: si la combinaison est introuvable.

    Ref: EC3-1-1 — Tableau 6.4 / 6.5
    """
    st = section_type.upper()
    meth = method.lower()

    if meth == "general":
        if st not in _LT_CURVE_GENERAL:
            raise ValueError(
                f"Pas de courbe de déversement (méthode générale) pour '{st}'."
            )
        return _LT_CURVE_GENERAL[st]

    elif meth == "rolled":
        ratio = h / b if b > 0 else 999.0
        cond = "hb_le_2" if ratio <= 2.0 else "hb_gt_2"
        return _LT_CURVE_ROLLED[cond]

    else:
        raise ValueError(f"Méthode '{method}' inconnue. Attendu 'general' ou 'rolled'.")


# -----------------------------------------------------------------------
# Fonctions de calcul Φ et χ
# -----------------------------------------------------------------------

def phi(lambda_bar: float, alpha: float) -> float:
    """
    Calcule le coefficient intermédiaire Φ pour le flambement par flexion.

    Φ = 0.5 · [1 + α·(λ̄ − 0.2) + λ̄²]

    :param lambda_bar: Élancement réduit λ̄
    :param alpha: Facteur d'imperfection α
    :return: Φ

    Ref: EC3-1-1 — §6.3.1.2 (1)
    """
    return 0.5 * (1.0 + alpha * (lambda_bar - 0.2) + lambda_bar ** 2)


def phi_LT(
    lambda_bar_LT: float,
    alpha_LT: float,
    lambda_LT_0: float = 0.2,
    beta: float = 1.0,
) -> float:
    """
    Calcule le coefficient intermédiaire Φ_LT pour le déversement.

    Φ_LT = 0.5 · [1 + α_LT·(λ̄_LT − λ̄_LT,0) + β·λ̄_LT²]

    :param lambda_bar_LT: Élancement réduit de déversement λ̄_LT
    :param alpha_LT: Facteur d'imperfection
    :param lambda_LT_0: Plateau (0.2 méthode générale, 0.4 méthode rolled)
    :param beta: Coefficient (1.0 méthode générale, 0.75 méthode rolled)
    :return: Φ_LT

    Ref: EC3-1-1 — §6.3.2.2 / §6.3.2.3
    """
    return 0.5 * (
        1.0 + alpha_LT * (lambda_bar_LT - lambda_LT_0) + beta * lambda_bar_LT ** 2
    )


def chi(lambda_bar: float, curve: str) -> float:
    """
    Calcule le coefficient de réduction χ pour le flambement par flexion.

    χ = 1 / (Φ + √(Φ² − λ̄²))  ≤ 1.0

    Si λ̄ ≤ 0.2 → χ = 1.0  (pas de flambement).

    :param lambda_bar: Élancement réduit λ̄
    :param curve: Courbe de flambement ('a0', 'a', 'b', 'c', 'd')
    :return: χ ∈ ]0 ; 1]

    Ref: EC3-1-1 — §6.3.1.2 (1)
    """
    if lambda_bar <= 0.2:
        return 1.0

    alpha = get_imperfection_factor(curve)
    p = phi(lambda_bar, alpha)
    discriminant = p ** 2 - lambda_bar ** 2
    if discriminant < 0:
        discriminant = 0.0
    result = 1.0 / (p + math.sqrt(discriminant))
    return min(result, 1.0)


def chi_LT(
    lambda_bar_LT: float,
    curve: str,
    method: str = "general",
    f: float = 1.0,
) -> float:
    """
    Calcule le coefficient de réduction χ_LT pour le déversement.

    - method='general' (§6.3.2.2) :
        λ̄_LT,0 = 0.2, β = 1.0
        χ_LT = 1 / (Φ_LT + √(Φ_LT² − λ̄_LT²))  ≤ 1.0
    - method='rolled' (§6.3.2.3) :
        λ̄_LT,0 = 0.4, β = 0.75
        χ_LT = 1 / (Φ_LT + √(Φ_LT² − β·λ̄_LT²))  ≤ 1.0  et  ≤ 1/λ̄_LT²
        puis χ_LT,mod = χ_LT / f  ≤ 1.0

    :param lambda_bar_LT: Élancement réduit de déversement λ̄_LT
    :param curve: Courbe de déversement
    :param method: 'general' ou 'rolled'
    :param f: Facteur de correction (§6.3.2.3 (2)), 1.0 par défaut
    :return: χ_LT

    Ref: EC3-1-1 — §6.3.2.2 / §6.3.2.3
    """
    meth = method.lower()

    if meth == "general":
        lam0 = 0.2
        beta = 1.0
    elif meth == "rolled":
        lam0 = 0.4
        beta = 0.75
    else:
        raise ValueError(f"Méthode '{method}' inconnue.")

    if lambda_bar_LT <= lam0:
        return 1.0

    alpha_lt = get_imperfection_factor(curve)
    p = phi_LT(lambda_bar_LT, alpha_lt, lam0, beta)
    discriminant = p ** 2 - beta * lambda_bar_LT ** 2
    if discriminant < 0:
        discriminant = 0.0
    result = 1.0 / (p + math.sqrt(discriminant))
    result = min(result, 1.0)

    if meth == "rolled":
        # Borne supplémentaire : χ_LT ≤ 1/λ̄_LT²
        if lambda_bar_LT > 0:
            result = min(result, 1.0 / (lambda_bar_LT ** 2))
        # Modification par f
        if f > 0:
            result = result / f
        result = min(result, 1.0)

    return result


# -----------------------------------------------------------------------
# Helpers longueur de flambement
# -----------------------------------------------------------------------

def buckling_length_factor(
    support_top: str,
    support_bottom: str,
) -> float:
    """
    Retourne le coefficient k pour la longueur de flambement Lcr = k · L.

    Cas classiques (Euler théorique) :
    - ('fixed', 'fixed')   → 0.5
    - ('fixed', 'pinned')  → 0.7
    - ('pinned', 'pinned') → 1.0
    - ('fixed', 'free')    → 2.0
    - ('fixed', 'slide')   → 1.0

    :param support_top: Condition d'appui supérieure ('fixed', 'pinned', 'free', 'slide')
    :param support_bottom: Condition d'appui inférieure
    :return: k

    Ref: EC3-1-1 — Figure 6.1
    """
    key = (support_bottom.lower().strip(), support_top.lower().strip())
    if key not in _K_FACTORS:
        # Essai dans l'autre sens
        key_rev = (support_top.lower().strip(), support_bottom.lower().strip())
        if key_rev not in _K_FACTORS:
            raise ValueError(
                f"Combinaison d'appuis ({support_bottom}, {support_top}) non reconnue. "
                f"Valeurs admises : {list(_K_FACTORS.keys())}"
            )
        return _K_FACTORS[key_rev]
    return _K_FACTORS[key]


def buckling_length(
    L: float,
    support_top: str = "pinned",
    support_bottom: str = "pinned",
    k: Optional[float] = None,
) -> float:
    """
    Calcule la longueur de flambement Lcr = k · L.

    Si *k* est fourni directement, il est utilisé.
    Sinon, k est déduit des conditions d'appui.

    :param L: Longueur du poteau [mm]
    :param support_top: Condition d'appui supérieure
    :param support_bottom: Condition d'appui inférieure
    :param k: Coefficient de longueur de flambement (prioritaire)
    :return: Lcr [mm]

    Ref: EC3-1-1 — Figure 6.1
    """
    if k is None:
        k = buckling_length_factor(support_top, support_bottom)
    return k * L


# ===================================================================
#  Tests
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST — buckling_curves.py")
    print("=" * 60)

    # Test χ pour λ̄ = 1.0, différentes courbes
    lam = 1.0
    print(f"\nχ pour λ̄ = {lam} :")
    for c in ("a0", "a", "b", "c", "d"):
        val = chi(lam, c)
        print(f"  Courbe {c:>2s} : α = {get_imperfection_factor(c):.2f}  →  χ = {val:.4f}")

    # Test get_buckling_curve pour un IPE 300 laminé (h=300, b=150, tf=10.7)
    print("\nCourbes de flambement — IPE 300 laminé (h=300, b=150, tf=10.7) :")
    for ax in ("y", "z"):
        c = get_buckling_curve("I", "rolled", ax, h=300, b=150, tf=10.7)
        print(f"  Axe {ax} → courbe '{c}'")

    # Test χ_LT
    print(f"\nχ_LT pour λ̄_LT = 1.0, courbe 'b' :")
    print(f"  Méthode générale : {chi_LT(1.0, 'b', 'general'):.4f}")
    print(f"  Méthode rolled   : {chi_LT(1.0, 'b', 'rolled'):.4f}")

    # Test longueur de flambement
    print(f"\nLongueur de flambement (L = 5000 mm) :")
    for top, bot in [("pinned", "pinned"), ("fixed", "pinned"), ("fixed", "fixed"), ("fixed", "free")]:
        k = buckling_length_factor(top, bot)
        lcr = buckling_length(5000, top, bot)
        print(f"  ({bot:>6s}, {top:>6s}) → k = {k:.1f}  →  Lcr = {lcr:.0f} mm")