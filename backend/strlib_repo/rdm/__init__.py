#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    fem — Module d'analyse de portique 2D par éléments finis.
    
    Méthode de rigidité directe (Direct Stiffness Method).
    
    Classes principales:
        - Node      : Nœud (3 DDL : dx, dy, θz)
        - Element   : Barre (bi-encastrée, articulée, etc.)
        - Solver    : Assemblage et résolution
        - Mesh      : Subdivision des éléments
        - Model     : Orchestrateur (point d'entrée)
    
    Chargements (loads):
        - DistributedLoad
        - PointLoadOnBeam
        - MomentOnBeam
        - ThermalLoad
        - PrestressLoad
    
    Usage:
        >>> from fem import Model, DistributedLoad
        >>> m = Model()
        >>> n1 = m.add_node(0, 0, rx=True, ry=True)
        >>> n2 = m.add_node(6000, 0, ry=True)
        >>> b = m.add_element(n1, n2, E=210000, A=5000, I=8.356e7)
        >>> b.add_load(DistributedLoad(fy=-10))
        >>> m.solve()
        >>> print(m.summary())
"""

from .node import Node
from .element import Element
from .solver import Solver
from .mesh import Mesh
from .model import Model
from .loads import (
    DistributedLoad,
    PointLoadOnBeam,
    MomentOnBeam,
    ThermalLoad,
    PrestressLoad,
)

__all__ = [
    'Node', 'Element', 'Solver', 'Mesh', 'Model',
    'DistributedLoad', 'PointLoadOnBeam', 'MomentOnBeam',
    'ThermalLoad', 'PrestressLoad',
]
