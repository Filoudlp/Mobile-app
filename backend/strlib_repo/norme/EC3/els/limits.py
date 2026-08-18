# limits.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Limites de flèche verticale et de déplacement horizontal
selon l'EC3-1-1 — §7.2, Tableau 7.1 et recommandations courantes.

Ce module fournit des dictionnaires de limites et des fonctions utilitaires
pour obtenir la flèche ou le déplacement admissible en mm.
"""

__all__ = [
    "VERTICAL_LIMITS",
    "HORIZONTAL_LIMITS",
    "get_limit",
    "get_drift_limit",
]

from typing import Optional

# ---------------------------------------------------------------------------
# Limites de flèche verticale  (span / ratio)
# Clé → ratio  (ex. 250  ⇒  L / 250)
# Référence : EC3-1-1 Tableau 7.1 + pratique courante
# ---------------------------------------------------------------------------

VERTICAL_LIMITS: dict[str, float] = {
    "roof_general":               200.0,   # Toitures en général
    "floor_general":              250.0,   # Planchers en général
    "floor_brittle_partitions":   300.0,   # Planchers supportant cloisons fragiles
    "floor_supporting_columns":   400.0,   # Planchers supportant poteaux
    "cantilever":                 150.0,   # Consoles  (souvent exprimé L/150)
    "roofing_element":            200.0,   # Éléments de couverture
}

# ---------------------------------------------------------------------------
# Limites de déplacement horizontal  (height / ratio)
# Référence : EC3-1-1 §7.2 + pratique courante
# ---------------------------------------------------------------------------

HORIZONTAL_LIMITS: dict[str, float] = {
    "portal_top":                 300.0,   # Portique — tête de poteau  H/300
    "portal_inter_storey":        300.0,   # Portique — entre niveaux   h/300
    "multi_storey_total":         500.0,   # Bâtiment multi-étages — total  H/500
    "multi_storey_inter_storey":  300.0,   # Bâtiment multi-étages — entre niveaux h/300
}


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def get_limit(
    span: float,
    element_type: str = "floor_general",
    custom_ratio: Optional[float] = None,
) -> float:
    """
    Retourne la flèche verticale admissible en **mm**.

    :param span:          Portée (ou longueur de console) [mm].
    :param element_type:  Clé dans ``VERTICAL_LIMITS``.
    :param custom_ratio:  Si fourni, utilise ``span / custom_ratio``
                          au lieu du dictionnaire.
    :return:              Flèche limite [mm].
    :raises KeyError:     Si ``element_type`` inconnu et pas de ``custom_ratio``.
    """
    if custom_ratio is not None:
        if custom_ratio == 0:
            return 0.0
        return span / custom_ratio

    if element_type not in VERTICAL_LIMITS:
        raise KeyError(
            f"element_type '{element_type}' inconnu. "
            f"Clés disponibles : {list(VERTICAL_LIMITS.keys())}"
        )
    return span / VERTICAL_LIMITS[element_type]


def get_drift_limit(
    height: float,
    structure_type: str = "portal_top",
    custom_ratio: Optional[float] = None,
) -> float:
    """
    Retourne le déplacement horizontal admissible en **mm**.

    :param height:          Hauteur totale H ou entre niveaux h [mm].
    :param structure_type:  Clé dans ``HORIZONTAL_LIMITS``.
    :param custom_ratio:    Si fourni, utilise ``height / custom_ratio``
                            au lieu du dictionnaire.
    :return:                Déplacement limite [mm].
    :raises KeyError:       Si ``structure_type`` inconnu et pas de ``custom_ratio``.
    """
    if custom_ratio is not None:
        if custom_ratio == 0:
            return 0.0
        return height / custom_ratio

    if structure_type not in HORIZONTAL_LIMITS:
        raise KeyError(
            f"structure_type '{structure_type}' inconnu. "
            f"Clés disponibles : {list(HORIZONTAL_LIMITS.keys())}"
        )
    return height / HORIZONTAL_LIMITS[structure_type]


# ---------------------------------------------------------------------------
# Debug / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test flèche verticale — plancher L = 6 000 mm
    L = 6000.0
    dl = get_limit(L, element_type="floor_general")
    print(f"Plancher L={L:.0f} mm → flèche limite = L/250 = {dl:.2f} mm")

    # Test déplacement horizontal — H/300
    H = 6000.0
    dd = get_drift_limit(H, structure_type="portal_top")
    print(f"Portique H={H:.0f} mm → déplacement limite = H/300 = {dd:.2f} mm")

    # Test custom ratio
    dl_custom = get_limit(L, custom_ratio=350)
    print(f"Custom L/350 = {dl_custom:.2f} mm")
