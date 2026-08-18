# ec3/ec3_1_1/serviceability/__init__.py

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ec3/ec3_1_1/serviceability/__init__.py
    ========================================
    Sous-package **États limites de service (ELS)** — EC3-1-1 §7

    Contenu
    -------
    Classes de calcul :
        - Deflection : Vérification des flèches             (§7.2)
        - Drift      : Vérification des déplacements inter-étage (§7.2)
        - Vibration  : Vérification aux vibrations / fréquence propre (§7.2.3)

    Fonctions standalone :
        - deflection_check()   : Vérification rapide de flèche
        - drift_check()        : Vérification rapide de déplacement horizontal
        - natural_frequency()  : Calcul de la fréquence propre

    Fonctions utilitaires (limites ELS) :
        - get_limit()       : Retourne la limite de flèche selon le contexte
        - get_drift_limit() : Retourne la limite de déplacement inter-étage

    Références
    ----------
    EN 1993-1-1:2005 — §7
"""

__all__ = [
    # --- Classes ---
    "Deflection",
    "Drift",
    "Vibration",
    # --- Fonctions standalone ---
    "deflection_check",
    "drift_check",
    "natural_frequency",
    # --- Utilitaires limites ELS ---
    "get_limit",
    "get_drift_limit",
]

# ── deflection.py ────────────────────────────────────────────────────────────
try:
    from .deflection import Deflection, deflection_check
except ImportError:  # TODO: créer deflection.py
    pass

# ── drift.py ─────────────────────────────────────────────────────────────────
try:
    from .drift import Drift, drift_check
except ImportError:  # TODO: créer drift.py
    pass

# ── vibration.py ─────────────────────────────────────────────────────────────
try:
    from .vibration import Vibration, natural_frequency
except ImportError:  # TODO: créer vibration.py
    pass

# ── limits.py ────────────────────────────────────────────────────────────────
try:
    from .limits import get_limit, get_drift_limit
except ImportError:  # TODO: créer limits.py
    pass
