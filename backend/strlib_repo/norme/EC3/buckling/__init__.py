# ec3/ec3_1_1/buckling/__init__.py

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ec3/ec3_1_1/buckling/__init__.py
    =================================
    Sous-package **Flambement et déversement** — EC3-1-1 §6.3

    Contenu
    -------
    Classes de calcul :
        - FlexuralBuckling         : Flambement par flexion             (§6.3.1)
        - LateralTorsionalBuckling : Déversement (flambement latéral)   (§6.3.2)
        - InteractionNM            : Interaction flexion + compression  (§6.3.3)

    Fonctions standalone :
        - nb_rd()     : Résistance au flambement axial
        - mb_rd()     : Résistance au déversement

    Fonctions helpers (courbes de flambement) :
        - get_alpha() : Facteur d'imperfection α selon la courbe
        - get_curve() : Sélection de la courbe de flambement
        - chi()       : Facteur de réduction χ (flambement / déversement)

    Références
    ----------
    EN 1993-1-1:2005 — §6.3
"""

__all__ = [
    # --- Classes ---
    "FlexuralBuckling",
    "LateralTorsionalBuckling",
    "InteractionNM",
    # --- Fonctions standalone ---
    "nb_rd",
    "mb_rd",
    # --- Helpers courbes de flambement ---
    "get_alpha",
    "get_curve",
    "chi",
]

# ── flexural_buckling.py ─────────────────────────────────────────────────────
try:
    from .flexural_buckling import FlexuralBuckling, nb_rd
except ImportError:  # TODO: créer flexural_buckling.py
    pass

# ── lateral_torsional.py ─────────────────────────────────────────────────────
try:
    from .lateral_torsional import LateralTorsionalBuckling, mb_rd
except ImportError:  # TODO: créer lateral_torsional.py
    pass

# ── interaction_NM.py ────────────────────────────────────────────────────────
try:
    from .interaction_NM import InteractionNM
except ImportError:  # TODO: créer interaction_NM.py
    pass

# ── buckling_curves.py ───────────────────────────────────────────────────────
try:
    from .buckling_curves import get_alpha, get_curve, chi
except ImportError:  # TODO: créer buckling_curves.py
    pass
