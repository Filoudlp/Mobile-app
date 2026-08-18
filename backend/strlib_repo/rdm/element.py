#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Élément barre 2D pour analyse de portique.
    
    Chaque élément relie 2 nœuds et possède:
        - Des propriétés géométriques (section, inertie)
        - Des propriétés matériau (module d'Young)
        - Des conditions aux extrémités (encastré, articulé)
        - Une liste de chargements
    
    L'élément sait calculer:
        - Sa matrice de rigidité locale et globale
        - Sa matrice de rotation
        - Ses forces nodales équivalentes
    
    Convention:
        - DDL locaux : [u1, v1, θ1, u2, v2, θ2]
        - Matrice 6×6
    
    Units: N, mm, rad
"""

__all__ = ['Element', 'EndCondition']

from typing import Optional, List, Union, TypeVar
from enum import Enum
import numpy as np
import math

from .node import Node
from .loads import (DistributedLoad, PointLoadOnBeam, MomentOnBeam,
                    ThermalLoad, PrestressLoad)

section_type = TypeVar('section_type')
material_type = TypeVar('material_type')

# Types de chargement acceptés
LoadType = Union[DistributedLoad, PointLoadOnBeam, MomentOnBeam,
                 ThermalLoad, PrestressLoad]


class EndCondition(Enum):
    """
        Conditions aux extrémités de la barre.
        
        FIXED    : encastré (transmet N, V, M)
        PINNED   : articulé (transmet N, V, pas M)
    """
    FIXED = "FIXED"
    PINNED = "PINNED"


class Element:
    """
        Élément barre 2D (poutre d'Euler-Bernoulli).
        
        Parameters
        ----------
        node_i : Node
            Nœud de début
        node_j : Node
            Nœud de fin
        section : section_type, optional
            Objet section (doit avoir .area et .iy)
        material : material_type, optional
            Objet matériau (doit avoir .E)
        beg_type : str
            Condition au début : "FIXED" ou "PINNED"
        end_type : str
            Condition à la fin : "FIXED" ou "PINNED"
        name : str, optional
            Nom de l'élément
        
        Examples
        --------
        >>> n1 = Node(0, 0)
        >>> n2 = Node(6000, 0)
        >>> beam = Element(n1, n2, E=210000, A=5000, I=1e8)
        >>> beam.add_load(DistributedLoad(fy=-25))
        >>> K = beam.k_global
    """

    _counter: int = 0

    def __init__(self, node_i: Node, node_j: Node,
                 section: Optional[section_type] = None,
                 material: Optional[material_type] = None,
                 beg_type: str = "FIXED", end_type: str = "FIXED",
                 name: Optional[str] = None,
                 **kwargs) -> None:

        # --- Validation ---
        if node_i == node_j:
            raise ValueError("Un élément ne peut pas relier un nœud à lui-même")

        Element._counter += 1
        self._id: int = Element._counter
        self._name: str = name or f"E{self._id}"

        # --- Nœuds ---
        self._node_i: Node = node_i
        self._node_j: Node = node_j

        # --- Propriétés mécaniques ---
        # Priorité : objet section/material > kwargs > défaut 1.0
        self._E: float = float(material.E if material else kwargs.get("E", 1.0))
        self._A: float = float(section.area if section else kwargs.get("A", 1.0))
        self._I: float = float(section.iy if section else kwargs.get("I", 1.0))
        self._h: float = float(section.h if section and hasattr(section, 'h')
                                else kwargs.get("h", 0.0))

        # --- Conditions aux extrémités ---
        self._beg_type: EndCondition = EndCondition(beg_type.upper())
        self._end_type: EndCondition = EndCondition(end_type.upper())

        # --- Chargements ---
        self._loads: List[LoadType] = []

        # --- Géométrie dérivée (calculée une fois) ---
        dx = self._node_j.x - self._node_i.x
        dy = self._node_j.y - self._node_i.y
        self._length: float = math.sqrt(dx**2 + dy**2)
        self._angle: float = math.degrees(math.atan2(dy, dx))

        if self._length == 0:
            raise ValueError(f"Longueur nulle pour l'élément {self._name}")

    # =================================================================
    #  Chargements
    # =================================================================

    def add_load(self, load: LoadType) -> 'Element':
        """
            Ajoute un chargement à l'élément.
            
            Parameters
            ----------
            load : LoadType
                Un des types de chargement définis dans loads.py
            
            Returns
            -------
            Element
                self (pour chaînage)
            
            Examples
            --------
            >>> beam.add_load(DistributedLoad(fy=-25))
            >>> beam.add_load(PointLoadOnBeam(fy=-50000, a=3000))
        """
        self._loads.append(load)
        return self

    def clear_loads(self) -> None:
        """Supprime tous les chargements."""
        self._loads.clear()

    @property
    def loads(self) -> List[LoadType]:
        """Liste des chargements appliqués."""
        return self._loads

    # =================================================================
    #  Géométrie
    # =================================================================

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_i(self) -> Node:
        """Nœud de début."""
        return self._node_i

    @property
    def node_j(self) -> Node:
        """Nœud de fin."""
        return self._node_j

    @property
    def length(self) -> float:
        """Longueur de la barre (mm)."""
        return self._length

    @property
    def angle(self) -> float:
        """Angle de la barre en degrés par rapport à l'horizontale."""
        return self._angle

    @property
    def angle_rad(self) -> float:
        """Angle de la barre en radians."""
        return math.radians(self._angle)

    # =================================================================
    #  Propriétés mécaniques
    # =================================================================

    @property
    def E(self) -> float:
        """Module d'Young (MPa)."""
        return self._E

    @property
    def A(self) -> float:
        """Aire de la section (mm²)."""
        return self._A

    @property
    def I(self) -> float:
        """Inertie (mm⁴)."""
        return self._I

    @property
    def h(self) -> float:
        """Hauteur de la section (mm)."""
        return self._h

    # =================================================================
    #  Matrices
    # =================================================================

    @property
    def rotation_matrix(self) -> np.ndarray:
        """
            Matrice de rotation 6×6 (local → global).
            
            [c  s  0  0  0  0]
            [-s c  0  0  0  0]
            [0  0  1  0  0  0]
            [0  0  0  c  s  0]
            [0  0  0 -s  c  0]
            [0  0  0  0  0  1]
        """
        c = math.cos(self.angle_rad)
        s = math.sin(self.angle_rad)

        R = np.zeros((6, 6), dtype=float)
        R[0, 0] = c;  R[0, 1] = s
        R[1, 0] = -s; R[1, 1] = c
        R[2, 2] = 1
        R[3, 3] = c;  R[3, 4] = s
        R[4, 3] = -s; R[4, 4] = c
        R[5, 5] = 1

        return R

    @property
    def k_local(self) -> np.ndarray:
        """
            Matrice de rigidité 6×6 en repère LOCAL.
            
            Prend en compte les conditions aux extrémités:
                - FIXED-FIXED  : matrice complète
                - PINNED-FIXED : condensation statique début
                - FIXED-PINNED : condensation statique fin
                - PINNED-PINNED: treillis pur (pas de flexion)
        """
        E = self._E
        A = self._A
        I = self._I
        L = self._length

        # Matrice barre bi-encastrée complète
        ea_l = E * A / L
        ei_l3 = E * I / L**3
        ei_l2 = E * I / L**2
        ei_l = E * I / L

        k = np.array([
            [ ea_l,    0,         0,        -ea_l,    0,         0       ],
            [ 0,       12*ei_l3,  6*ei_l2,   0,      -12*ei_l3, 6*ei_l2 ],
            [ 0,       6*ei_l2,   4*ei_l,    0,      -6*ei_l2,  2*ei_l  ],
            [-ea_l,    0,         0,         ea_l,    0,         0       ],
            [ 0,      -12*ei_l3, -6*ei_l2,   0,       12*ei_l3,-6*ei_l2 ],
            [ 0,       6*ei_l2,   2*ei_l,    0,      -6*ei_l2,  4*ei_l  ],
        ], dtype=float)

        # --- Condensation statique pour articulations ---
        beg_pinned = self._beg_type == EndCondition.PINNED
        end_pinned = self._end_type == EndCondition.PINNED

        if beg_pinned and end_pinned:
            # Treillis pur : seul l'effort normal passe
            k_truss = np.zeros((6, 6), dtype=float)
            k_truss[0, 0] = ea_l
            k_truss[0, 3] = -ea_l
            k_truss[3, 0] = -ea_l
            k_truss[3, 3] = ea_l
            return k_truss

        elif beg_pinned:
            # Condensation du DDL θ1 (index 2)
            # k_red = k - k[:,2] * k[2,:] / k[2,2]
            k = k - np.outer(k[:, 2], k[2, :]) / k[2, 2]
            k[2, :] = 0
            k[:, 2] = 0

        elif end_pinned:
            # Condensation du DDL θ2 (index 5)
            k = k - np.outer(k[:, 5], k[5, :]) / k[5, 5]
            k[5, :] = 0
            k[:, 5] = 0

        return k

    @property
    def k_global(self) -> np.ndarray:
        """
            Matrice de rigidité 6×6 en repère GLOBAL.
            
            K_global = R^T · K_local · R
        """
        R = self.rotation_matrix
        return R.T @ self.k_local @ R

    # =================================================================
    #  Forces nodales équivalentes
    # =================================================================

    @property
    def equivalent_nodal_forces_local(self) -> np.ndarray:
        """
            Somme des forces nodales équivalentes de tous les
            chargements, en repère LOCAL.
            
            Returns
            -------
            np.ndarray
                [Fx_i, Fy_i, Mz_i, Fx_j, Fy_j, Mz_j]
        """
        f_total = np.zeros(6, dtype=float)

        for load in self._loads:
            if isinstance(load, ThermalLoad):
                f_total += load.equivalent_nodal_forces(
                    self._length, self._E, self._A, self._I, self._h
                )
            else:
                f_total += load.equivalent_nodal_forces(self._length)

        return f_total

    @property
    def equivalent_nodal_forces_global(self) -> np.ndarray:
        """
            Forces nodales équivalentes en repère GLOBAL.
            
            F_global = R^T · F_local
        """
        R = self.rotation_matrix
        return R.T @ self.equivalent_nodal_forces_local

    # =================================================================
    #  Efforts internes
    # =================================================================

    def internal_forces_at(self, x: float,
                            displacements_global: np.ndarray) -> np.ndarray:
        """
            Calcule N, V, M à l'abscisse x le long de la barre.
            
            Parameters
            ----------
            x : float
                Abscisse locale (0 = nœud i, L = nœud j)
            displacements_global : np.ndarray
                Vecteur [u_i, v_i, θ_i, u_j, v_j, θ_j] en global
            
            Returns
            -------
            np.ndarray
                [N, V, M] à l'abscisse x
            
            Note
            ----
            Formule : f_local = K_local · R · d_global - f_eq_local
            Puis intégration le long de la barre pour les efforts en x.
        """
        R = self.rotation_matrix
        d_local = R @ displacements_global
        f_nodal = self.k_local @ d_local - self.equivalent_nodal_forces_local

        print(f"f_nodal E2 = {f_nodal}")

        # Efforts aux nœuds : [Nx_i, Vy_i, Mz_i, Nx_j, Vy_j, Mz_j]
        # N(x) = -Nx_i  (constant si pas de charge axiale répartie)
        # V(x) = Vy_i   (constant si pas de charge transversale répartie)
        # M(x) = Mz_i + Vy_i * x (si pas de charge répartie)

        N_i = -f_nodal[0]
        V_i = -f_nodal[1]
        M_i = -f_nodal[2]

        # Ajout de l'effet des charges réparties
        q_y = sum(ld.fy for ld in self._loads if isinstance(ld, DistributedLoad))
        q_x = sum(ld.fx for ld in self._loads if isinstance(ld, DistributedLoad))

        N = N_i + q_x * x
        V = V_i - q_y * x
        M = M_i + V_i * x - q_y * x**2 / 2

        return np.array([N, V, M], dtype=float)

    # =================================================================
    #  Utilitaires
    # =================================================================

    @classmethod
    def reset_counter(cls) -> None:
        """Remet le compteur d'éléments à zéro."""
        cls._counter = 0

    def __repr__(self) -> str:
        return (f"Element '{self._name}' | "
                f"{self._node_i.name}→{self._node_j.name} | "
                f"L={self._length:.0f} mm | "
                f"θ={self._angle:.1f}° | "
                f"{self._beg_type.value}-{self._end_type.value} | "
                f"{len(self._loads)} loads")

    def __len__(self) -> int:
        """Retourne la longueur (arrondie) en mm."""
        return int(round(self._length))


# =============================================================================
#  TESTS
# =============================================================================

if __name__ == "__main__":
    Node.reset_counter()
    Element.reset_counter()

    # Portique simple
    n1 = Node(0, 0, name="A")
    n2 = Node(6000, 0, name="B")
    n3 = Node(6000, 4000, name="C")

    n1.set_support(rx=True, ry=True, rz=True)
    n3.set_support(rx=True, ry=True, rz=True)

    # Poutre horizontale
    beam = Element(n1, n2, E=210000, A=5000, I=8.356e7, name="Poutre")
    beam.add_load(DistributedLoad(fy=-25))

    # Poteau vertical
    col = Element(n2, n3, E=210000, A=3000, I=2.5e7, name="Poteau")

    print(beam)
    print(col)
    print(f"\nK_local poutre :\n{beam.k_local}")
    print(f"\nForces eq poutre : {beam.equivalent_nodal_forces_local}")
