#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Modèle structurel — orchestre nœuds, éléments, maillage et résolution.
    
    C'est le point d'entrée principal pour l'utilisateur.
"""

__all__ = ['Model']

from typing import List, Dict, Optional, Tuple
import numpy as np

from .node import Node
from .element import Element
from .solver import Solver
from .mesh import Mesh
from .loads import (
    DistributedLoad, PointLoadOnBeam, MomentOnBeam,
    ThermalLoad, PrestressLoad
)


class Model:
    """
        Modèle structurel 2D complet.
        
        Examples
        --------
        >>> model = Model()
        >>> n1 = model.add_node(0, 0, name="A", rx=True, ry=True)
        >>> n2 = model.add_node(6000, 0, name="B", ry=True)
        >>> b1 = model.add_element(n1, n2, E=210000, A=5000, I=8.356e7)
        >>> b1.add_load(DistributedLoad(fy=-10))
        >>> model.solve()
        >>> print(model.summary())
    """

    def __init__(self) -> None:
        self._nodes: List[Node] = []
        self._elements: List[Element] = []
        self._solver: Optional[Solver] = None

    # =================================================================
    #  Construction du modèle
    # =================================================================

    def add_node(self, x: float, y: float, name: Optional[str] = None,
                 rx: bool = False, ry: bool = False,
                 rz: bool = False,
                 fx: float = 0.0, fy: float = 0.0,
                 mz: float = 0.0) -> Node:
        """
            Crée et ajoute un nœud au modèle.
            
            Parameters
            ----------
            x, y : float
                Coordonnées
            name : str, optional
                Nom du nœud
            rx, ry, rz : bool
                Conditions d'appui
            fx, fy, mz : float
                Forces nodales externes
            
            Returns
            -------
            Node
        """
        node = Node(x, y, name=name)

        if rx or ry or rz:
            node.set_support(rx=rx, ry=ry, rz=rz)

        if fx != 0 or fy != 0 or mz != 0:
            node.set_forces(fx=fx, fy=fy, mz=mz)

        self._nodes.append(node)
        return node

    def add_element(self, node_i: Node, node_j: Node,
                    name: Optional[str] = None,
                    beg_type: str = "FIXED", end_type: str = "FIXED",
                    **kwargs) -> Element:
        """
            Crée et ajoute un élément au modèle.
            
            Parameters
            ----------
            node_i, node_j : Node
            name : str, optional
            beg_type, end_type : str
                "FIXED" ou "PINNED"
            **kwargs
                E, A, I, h ou section/material
            
            Returns
            -------
            Element
        """
        elem = Element(node_i, node_j, name=name,
                        beg_type=beg_type, end_type=end_type, **kwargs)
        self._elements.append(elem)
        return elem

    # =================================================================
    #  Maillage
    # =================================================================

    def subdivide(self, elem: Element, n: int = 10) -> None:
        """Subdivise un élément en n sous-éléments."""
        mesh = Mesh(self._nodes, self._elements)
        mesh.subdivide(elem, n)
        self._nodes = mesh.nodes
        self._elements = mesh.elements

    def subdivide_all(self, n: int = 10) -> None:
        """Subdivise tous les éléments."""
        mesh = Mesh(self._nodes, self._elements)
        mesh.subdivide_all(n)
        self._nodes = mesh.nodes
        self._elements = mesh.elements

    # =================================================================
    #  Résolution
    # =================================================================

    def solve(self, verbose: bool = False) -> 'Model':
        """
            Résout le modèle.
            
            Returns
            -------
            Model
                self (pour chaînage)
        """
        self._solver = Solver(self._nodes, self._elements, verbose=verbose)
        self._solver.solve()
        return self

    @property
    def is_solved(self) -> bool:
        return self._solver is not None and self._solver.is_solved

    # =================================================================
    #  Résultats
    # =================================================================

    def internal_forces(self, elem: Element, nb_points: int = 50) -> Dict[str, np.ndarray]:
        """Efforts internes le long d'un élément."""
        if not self.is_solved:
            raise RuntimeError("Appeler solve() d'abord")
        return self._solver.internal_forces(elem, nb_points=nb_points)

    def all_internal_forces(self, nb_points: int = 50) -> Dict:
        """Efforts internes de tous les éléments."""
        if not self.is_solved:
            raise RuntimeError("Appeler solve() d'abord")
        return self._solver.all_internal_forces(nb_points=nb_points)
    
    def displacements(self, elem: Element, nb_points: int = 50) -> Dict[str, np.ndarray]:
        """
        Déplacements le long d'un élément.
        
        Returns
        -------
        dict avec clés :
            'x'     : np.ndarray — abscisses locales (0 à L)
            'u'     : np.ndarray — déplacement axial
            'v'     : np.ndarray — déplacement transversal
            'theta' : np.ndarray — rotation
        """
        if not self.is_solved:
            raise RuntimeError("Appeler solve() d'abord")
        return self._solver.displacements(elem, nb_points=nb_points)

    def all_displacements(self, nb_points: int = 50) -> Dict:
        """Déplacements de tous les éléments."""
        if not self.is_solved:
            raise RuntimeError("Appeler solve() d'abord")
        return self._solver.all_displacements(nb_points=nb_points)

    @property
    def hyperstaticity(self) -> Tuple[int, str]:
        """Degré d'hyperstaticité."""
        return Solver.hyperstaticity(self._nodes)

    # =================================================================
    #  Accès
    # =================================================================

    @property
    def nodes(self) -> List[Node]:
        return self._nodes

    @property
    def elements(self) -> List[Element]:
        return self._elements

    @property
    def solver(self) -> Optional[Solver]:
        return self._solver

    # =================================================================
    #  Résumé
    # =================================================================

    def summary(self) -> str:
        """Résumé textuel du modèle et des résultats."""
        lines = []
        deg, label = self.hyperstaticity
        lines.append(f"=== MODÈLE : {len(self._nodes)} nœuds | "
                      f"{len(self._elements)} éléments | {label} ===")
        lines.append("")

        if self.is_solved:
            lines.append("--- DÉPLACEMENTS ---")
            for n in self._nodes:
                r = n.results
                lines.append(
                    f"  {n.name:>6s} : "
                    f"x = {n.x:+.4f} mm  "
                    f"dx={r.dx:+.4f} mm  "
                    f"dy={r.dy:+.4f} mm  "
                    f"θ={r.theta:+.6f} rad"
                    f"Rx={r.rx:+.1f} N  "
                    f"Ry={r.ry:+.1f} N  "
                    f"Mz={r.mz:+.1f} N·mm"
                    f"N={r.n:+.1f} N  "
                    f"V={r.v:+.1f} N  "
                    f"M={r.m:+.1f} N·mm"
                )

            lines.append("")
            lines.append("--- RÉACTIONS ---")
            for n in self._nodes:
                if n.hyper_degree > 0:
                    r = n.results
                    lines.append(
                        f"  {n.name:>6s} : "
                        f"Rx={r.rx:+.1f} N  "
                        f"Ry={r.ry:+.1f} N  "
                        f"Mz={r.mz:+.1f} N·mm"
                    )
        else:
            lines.append("(non résolu)")

        return "\n".join(lines)

    def __repr__(self) -> str:
        status = "✅" if self.is_solved else "⏳"
        return (f"Model {status} | {len(self._nodes)} nœuds | "
                f"{len(self._elements)} éléments")


# =============================================================================
#  TESTS
# =============================================================================

if __name__ == "__main__":
    Node.reset_counter()
    Element.reset_counter()

    # Poutre continue sur 3 appuis
    model = Model()

    n1 = model.add_node(0, 0, name="A", rx=True, ry=True)
    n2 = model.add_node(4000, 0, name="B", ry=True)
    n3 = model.add_node(10000, 0, name="C", ry=True)

    b1 = model.add_element(n1, n2, E=210000, A=5000, I=8.356e7, name="AB")
    b2 = model.add_element(n2, n3, E=210000, A=5000, I=8.356e7, name="BC")

    b1.add_load(DistributedLoad(fy=-10))
    b2.add_load(DistributedLoad(fy=-10))

    model.solve(verbose=True)
    print(model.summary())
