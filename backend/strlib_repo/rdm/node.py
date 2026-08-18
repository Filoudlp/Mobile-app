#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Node (point) for 2D frame FEM analysis.

    Each node has 3 DOFs: dx, dy, θz
    
    Convention de signe:
        - Forces/déplacements positifs selon X+ et Y+
        - Moment positif en anti-horaire
    
    Units: user-consistent (typiquement N, mm, rad)
"""

__all__ = ['Node']

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class Support:
    """
        Conditions d'appui sur un nœud.
        
        True  = bloqué (déplacement imposé = 0)
        False = libre
    """
    rx: bool = False    # Bloqué en X
    ry: bool = False    # Bloqué en Y
    rz: bool = False    # Bloqué en rotation

    @property
    def dof_blocked(self) -> list[bool]:
        """Liste ordonnée [dx, dy, θz] des DOFs bloqués."""
        return [self.rx, self.ry, self.rz]

    @property
    def nb_blocked(self) -> int:
        """Nombre de DDL bloqués (degré hyperstatique local)."""
        return sum(self.dof_blocked)

    def __repr__(self) -> str:
        labels = []
        if self.rx: labels.append("Rx")
        if self.ry: labels.append("Ry")
        if self.rz: labels.append("Mz")
        return f"Support({', '.join(labels) if labels else 'free'})"


@dataclass
class NodalForces:
    """Forces nodales externes appliquées."""
    fx: float = 0.0     # Force en X (N)
    fy: float = 0.0     # Force en Y (N)
    mz: float = 0.0     # Moment en Z (N·mm)

    def as_array(self) -> np.ndarray:
        return np.array([self.fx, self.fy, self.mz], dtype=float)

    def __repr__(self) -> str:
        return f"F({self.fx:.1f}, {self.fy:.1f}, {self.mz:.1f})"


@dataclass
class NodalResults:
    """Résultats après résolution."""
    # Déplacements
    dx: float = 0.0      # Déplacement en X (mm)
    dy: float = 0.0      # Déplacement en Y (mm)
    theta: float = 0.0   # Rotation (rad)

    # Réactions d'appui
    rx: float = 0.0      # Réaction en X (N)
    ry: float = 0.0      # Réaction en Y (N)
    mz: float = 0.0      # Moment de réaction (N·mm)

    # Efforts internes (somme des contributions des barres)
    n: float = 0.0       # Effort normal (N)
    v: float = 0.0       # Effort tranchant (N)
    m: float = 0.0       # Moment fléchissant (N·mm)

    @property
    def displacement_array(self) -> np.ndarray:
        return np.array([self.dx, self.dy, self.theta], dtype=float)

    @property
    def reaction_array(self) -> np.ndarray:
        return np.array([self.rx, self.ry, self.mz], dtype=float)


class Node:
    """
        Nœud 2D pour analyse de portique.
        
        3 DDL par nœud : dx, dy, θz
        
        Parameters
        ----------
        x : float
            Coordonnée X du nœud
        y : float
            Coordonnée Y du nœud
        name : str, optional
            Nom du nœud (auto-généré si non fourni)
        
        Examples
        --------
        >>> n1 = Node(0, 0, name="A")
        >>> n1.set_support(ry=True)          # appui simple vertical
        >>> n1.set_forces(fy=-10000)         # charge descendante
        >>> print(n1)
        Node 'A' (0.00, 0.00) | Support(Ry) | F(0.0, -10000.0, 0.0)
    """

    _counter: int = 0  # Compteur global de nœuds

    def __init__(self, x: float, y: float, name: Optional[str] = None) -> None:
        Node._counter += 1
        self._id: int = Node._counter
        self._name: str = name or f"N{self._id}"

        # --- Géométrie ---
        self._x: float = float(x)
        self._y: float = float(y)

        # --- Conditions d'appui ---
        self._support: Support = Support()

        # --- Chargement externe ---
        self._forces: NodalForces = NodalForces()

        # --- Résultats (remplis par le solver) ---
        self._results: NodalResults = NodalResults()

    # =================================================================
    #  Setters pratiques
    # =================================================================

    def set_support(self, rx: bool = False, ry: bool = False,
                    rz: bool = False) -> 'Node':
        """
            Définit les conditions d'appui.
            
            Parameters
            ----------
            rx : bool
                Bloqué en X
            ry : bool
                Bloqué en Y
            rz : bool
                Bloqué en rotation
            
            Returns
            -------
            Node
                self (pour chaînage)
            
            Examples
            --------
            >>> n.set_support(rx=True, ry=True)          # Appui fixe
            >>> n.set_support(rx=True, ry=True, rz=True) # Encastrement
        """
        self._support = Support(rx=rx, ry=ry, rz=rz)
        return self

    def set_forces(self, fx: float = 0.0, fy: float = 0.0,
                   mz: float = 0.0) -> 'Node':
        """
            Applique des forces nodales externes.
            
            Parameters
            ----------
            fx : float
                Force horizontale (N), positif vers la droite
            fy : float
                Force verticale (N), positif vers le haut
            mz : float
                Moment (N·mm), positif anti-horaire
            
            Returns
            -------
            Node
                self (pour chaînage)
        """
        self._forces = NodalForces(fx=fx, fy=fy, mz=mz)
        return self

    # =================================================================
    #  Properties — Géométrie
    # =================================================================

    @property
    def id(self) -> int:
        """Identifiant unique du nœud."""
        return self._id

    @property
    def name(self) -> str:
        """Nom du nœud."""
        return self._name

    @name.setter
    def name(self, val: str) -> None:
        self._name = str(val)

    @property
    def x(self) -> float:
        """Coordonnée X (mm)."""
        return self._x

    @property
    def y(self) -> float:
        """Coordonnée Y (mm)."""
        return self._y

    @property
    def coords(self) -> np.ndarray:
        """Coordonnées [x, y] comme array numpy."""
        return np.array([self._x, self._y], dtype=float)

    # =================================================================
    #  Properties — Appui
    # =================================================================

    @property
    def support(self) -> Support:
        """Conditions d'appui du nœud."""
        return self._support

    @property
    def is_free(self) -> bool:
        """True si le nœud n'a aucun appui."""
        return self._support.nb_blocked == 0

    @property
    def hyper_degree(self) -> int:
        """Nombre de DDL bloqués (contribution au degré hyperstatique)."""
        return self._support.nb_blocked

    # =================================================================
    #  Properties — Chargement
    # =================================================================

    @property
    def forces(self) -> NodalForces:
        """Forces nodales externes."""
        return self._forces

    # =================================================================
    #  Properties — Résultats
    # =================================================================

    @property
    def results(self) -> NodalResults:
        """Résultats après résolution (déplacements, réactions, efforts)."""
        return self._results

    # =================================================================
    #  Méthodes utilitaires
    # =================================================================

    def distance_to(self, other: 'Node') -> float:
        """Distance euclidienne vers un autre nœud."""
        return float(np.linalg.norm(self.coords - other.coords))

    def reset_results(self) -> None:
        """Remet les résultats à zéro (avant un nouveau calcul)."""
        self._results = NodalResults()

    @classmethod
    def reset_counter(cls) -> None:
        """Remet le compteur de nœuds à zéro."""
        cls._counter = 0

    # =================================================================
    #  Méthodes spéciales
    # =================================================================

    def __repr__(self) -> str:
        return (f"Node '{self._name}' ({self._x:.2f}, {self._y:.2f}) "
                f"| {self._support} | {self._forces}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


# =============================================================================
#  TESTS
# =============================================================================

if __name__ == "__main__":
    Node.reset_counter()

    # Création
    n1 = Node(0, 0, name="A")
    n2 = Node(5000, 0, name="B")
    n3 = Node(10000, 0, name="C")

    # Appuis
    n1.set_support(rx=True, ry=True)       # Appui fixe
    n2.set_support(ry=True)                # Appui simple
    n3.set_support(rx=True, ry=True, rz=True)  # Encastrement

    # Chargement
    n2.set_forces(fy=-50000, mz=10000)

    # Affichage
    for n in [n1, n2, n3]:
        print(n)
        print(f"  Free: {n.is_free} | Hyper degree: {n.hyper_degree}")

    # Distance
    print(f"\nDistance A→B : {n1.distance_to(n2):.0f} mm")
    print(f"Distance A→C : {n1.distance_to(n3):.0f} mm")
