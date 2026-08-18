# ec3/ec3_1_1/__init__.py

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ec3/ec3_1_1/__init__.py
    ========================
    Package **EC3-1-1** — Règles générales et règles pour les bâtiments

    Ce package regroupe l'ensemble des vérifications de l'Eurocode 3 partie 1-1.
    Il ré-exporte tous les symboles des sous-packages pour un accès simplifié.

    Structure
    ---------
    ec3_1_1/
    ├── classification.py   : Classement des sections transversales    (§5.5)
    ├── elu/         : Résistance des sections                  (§6.2)
    ├── buckling/           : Flambement et déversement                (§6.3)
    └── els/     : États limites de service (ELS)           (§7)

    Utilisation rapide
    ------------------
    >>> from ec3.ec3_1_1 import Tension, FlexuralBuckling, Deflection, Classification
    >>> from ec3.ec3_1_1 import nb_rd, mc_rd, deflection_check

    Références
    ----------
    EN 1993-1-1:2005 — Eurocode 3 : Calcul des structures en acier
                        Partie 1-1 : Règles générales et règles pour les bâtiments
"""

__all__ = [
    # ── Classification ────────────────────────────────────────────────────────
    "Classification",

    # ── Resistance — Classes ─────────────────────────────────────────────────
    "Tension",
    "Compression",
    "Bending",
    "Shear",
    "Combined",

    # ── Resistance — Fonctions standalone ────────────────────────────────────
    "nt_rd",
    "nc_rd",
    "mc_rd",
    "vc_rd",

    # ── Buckling — Classes ───────────────────────────────────────────────────
    "FlexuralBuckling",
    "LateralTorsionalBuckling",
    "InteractionNM",

    # ── Buckling — Fonctions standalone ──────────────────────────────────────
    "nb_rd",
    "mb_rd",

    # ── Buckling — Helpers courbes de flambement ──────────────────────────────
    "get_alpha",
    "get_curve",
    "chi",

    # ── Serviceability — Classes ──────────────────────────────────────────────
    "Deflection",
    "Drift",
    "Vibration",

    # ── Serviceability — Fonctions standalone ─────────────────────────────────
    "deflection_check",
    "drift_check",
    "natural_frequency",

    # ── Serviceability — Utilitaires limites ELS ──────────────────────────────
    "get_limit",
    "get_drift_limit",
]

# ── classification.py ────────────────────────────────────────────────────────
try:
    from .classification import Classification
except ImportError:  # TODO: créer classification.py
    pass

# ── resistance/ ──────────────────────────────────────────────────────────────
try:
    from .resistance import (
        Tension,
        Compression,
        Bending,
        Shear,
        Combined,
        nt_rd,
        nc_rd,
        mc_rd,
        vc_rd,
    )
except ImportError:  # TODO: compléter le sous-package resistance/
    pass

# ── buckling/ ────────────────────────────────────────────────────────────────
try:
    from .buckling import (
        FlexuralBuckling,
        LateralTorsionalBuckling,
        InteractionNM,
        nb_rd,
        mb_rd,
        get_alpha,
        get_curve,
        chi,
    )
except ImportError:  # TODO: compléter le sous-package buckling/
    pass

# ── serviceability/ ──────────────────────────────────────────────────────────
try:
    from .serviceability import (
        Deflection,
        Drift,
        Vibration,
        deflection_check,
        drift_check,
        natural_frequency,
        get_limit,
        get_drift_limit,
    )
except ImportError:  # TODO: compléter le sous-package serviceability/
    pass
