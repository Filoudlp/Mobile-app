# ec3/ec3_1_1/resistance/__init__.py

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ec3/ec3_1_1/resistance/__init__.py
    ===================================
    Sous-package **Résistance des sections** — EC3-1-1 §6.2

    Contenu
    -------
    Classes de calcul :
        - Tension       : Vérification à la traction         (§6.2.3)
        - Compression   : Vérification à la compression       (§6.2.4)
        - Bending       : Vérification à la flexion           (§6.2.5)
        - Shear         : Vérification à l'effort tranchant   (§6.2.6)
        - Combined      : Vérifications aux sollicitations combinées (§6.2.9 / §6.2.10)

    Fonctions standalone :
        - nt_rd()   : Résistance nette à la traction
        - nc_rd()   : Résistance à la compression
        - mc_rd()   : Résistance au moment fléchissant
        - vc_rd()   : Résistance à l'effort tranchant

    Références
    ----------
    EN 1993-1-1:2005 — §6.2
"""

__all__ = [
    # --- Classes ---
    "Tension",
    "Compression",
    "Bending",
    "Shear",
    "Combined",
    # --- Fonctions standalone ---
    "nt_rd",
    "nc_rd",
    "mc_rd",
    "vc_rd",
]

# ── tension.py ──────────────────────────────────────────────────────────────
try:
    from .tension import Tension, nt_rd
except ImportError:  # TODO: créer tension.py
    pass

# ── compression.py ──────────────────────────────────────────────────────────
try:
    from .compression import Compression, nc_rd
except ImportError:  # TODO: créer compression.py
    pass

# ── bending.py ──────────────────────────────────────────────────────────────
try:
    from .bending import Bending, mc_rd
except ImportError:  # TODO: créer bending.py
    pass

# ── shear.py ─────────────────────────────────────────────────────────────────
try:
    from .shear import Shear, vc_rd
except ImportError:  # TODO: créer shear.py
    pass

# ── combined.py ──────────────────────────────────────────────────────────────
try:
    from .combined import Combined
except ImportError:  # TODO: créer combined.py
    pass
