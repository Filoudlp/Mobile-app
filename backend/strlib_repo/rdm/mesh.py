#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Maillage (subdivision) des éléments barres.
    
    Divise un élément en N sous-éléments pour affiner
    l'analyse (charges ponctuelles, post-traitement, etc.)
    
    Units: cohérent avec Node / Element
"""

__all__ = ['Mesh']

from typing import List, Tuple, Optional
import numpy as np

from .node import Node
from .element import Element


class Mesh:
    """
        Subdivise des éléments en sous-éléments.
        
        Parameters
        ----------
        nodes : list of Node
            Liste originale des nœuds
        elements : list of Element
            Liste originale des éléments
        
        Examples
        --------
        >>> mesh = Mesh(nodes, elements)
        >>> new_nodes, new_elements = mesh.subdivide(beam, n=10)
        >>> # ou tout d'un coup :
        >>> new_nodes, new_elements = mesh.subdivide_all(n=10)
    """

    def __init__(self, nodes: List[Node], elements: List[Element]) -> None:
        self._nodes: List[Node] = list(nodes)
        self._elements: List[Element] = list(elements)

    def subdivide(self, elem: Element, n: int = 10,
                  **elem_kwargs) -> Tuple[List[Node], List[Element]]:
        """
            Divise un élément en n sous-éléments.
            
            Parameters
            ----------
            elem : Element
                Élément à subdiviser
            n : int
                Nombre de sous-éléments
            **elem_kwargs
                Propriétés mécaniques (E, A, I) — par défaut reprises de elem
            
            Returns
            -------
            (new_nodes, new_elements) : tuple
                new_nodes : n-1 nœuds intermédiaires créés
                new_elements : n sous-éléments (l'original est supprimé)
            
            Note
            ----
            - Les nœuds d'extrémité originaux sont conservés
            - L'élément original est retiré de self._elements
            - Les chargements sont reportés sur chaque sous-élément
        """
        if n < 2:
            return [], [elem]

        ni = elem.node_i
        nj = elem.node_j

        # Propriétés mécaniques
        E = elem_kwargs.get("E", elem.E)
        A = elem_kwargs.get("A", elem.A)
        I = elem_kwargs.get("I", elem.I)

        # Coordonnées intermédiaires
        x_arr = np.linspace(ni.x, nj.x, n + 1)
        y_arr = np.linspace(ni.y, nj.y, n + 1)

        # Créer les nœuds intermédiaires (index 1 à n-1)
        new_nodes: List[Node] = []
        for k in range(1, n):
            name = f"{elem.name}_N{k}"
            nd = Node(float(x_arr[k]), float(y_arr[k]), name=name)
            new_nodes.append(nd)

        # Liste ordonnée de tous les nœuds de la subdivision
        all_sub_nodes = [ni] + new_nodes + [nj]

        # Créer les sous-éléments
        new_elements: List[Element] = []
        for k in range(n):
            name = f"{elem.name}_{k + 1}"

            # Conditions aux extrémités
            beg = elem._beg_type.value if k == 0 else "FIXED"
            end = elem._end_type.value if k == n - 1 else "FIXED"

            sub_elem = Element(
                all_sub_nodes[k], all_sub_nodes[k + 1],
                E=E, A=A, I=I,
                beg_type=beg, end_type=end,
                name=name,
            )

            # Reporter les charges réparties sur chaque sous-élément
            from .loads import DistributedLoad
            for load in elem.loads:
                if isinstance(load, DistributedLoad):
                    sub_elem.add_load(DistributedLoad(
                        fx=load.fx, fy=load.fy, frame=load.frame
                    ))

            new_elements.append(sub_elem)

        # Mettre à jour les listes globales
        # if elem in self._elements:
        #     self._elements.remove(elem)
        # self._nodes.extend(new_nodes)
        # self._elements.extend(new_elements)
        if elem in self._elements:
            idx_elem = self._elements.index(elem)
            self._elements.remove(elem)
            self._elements[idx_elem:idx_elem] = new_elements

        idx_ni = self._nodes.index(ni)
        idx_nj = self._nodes.index(nj)
        insert_idx = max(idx_ni, idx_nj)
        self._nodes[insert_idx:insert_idx] = new_nodes

        return new_nodes, new_elements

    def subdivide_all(self, n: int = 10) -> Tuple[List[Node], List[Element]]:
        """
            Subdivise TOUS les éléments en n sous-éléments.
            
            Returns
            -------
            (all_new_nodes, all_new_elements)
        """
        # Copier la liste car on la modifie pendant l'itération
        original_elements = list(self._elements)
        all_new_nodes = []
        all_new_elements = []

        for elem in original_elements:
            nodes, elems = self.subdivide(elem, n)
            all_new_nodes.extend(nodes)
            all_new_elements.extend(elems)

        return all_new_nodes, all_new_elements

    @property
    def nodes(self) -> List[Node]:
        """Liste actuelle des nœuds (après subdivision)."""
        return self._nodes

    @property
    def elements(self) -> List[Element]:
        """Liste actuelle des éléments (après subdivision)."""
        return self._elements

    def __repr__(self) -> str:
        return (f"Mesh | {len(self._nodes)} nœuds | "
                f"{len(self._elements)} éléments")


# =============================================================================
#  TESTS
# =============================================================================

if __name__ == "__main__":
    Node.reset_counter()
    Element.reset_counter()

    from .loads import DistributedLoad

    n1 = Node(0, 0, name="A")
    n2 = Node(6000, 0, name="B")

    n1.set_support(rx=True, ry=True, rz=True)
    n2.set_support(rx=True, ry=True, rz=True)

    beam = Element(n1, n2, E=210000, A=5000, I=8.356e7, name="Poutre")
    beam.add_load(DistributedLoad(fy=-10))

    mesh = Mesh([n1, n2], [beam])
    print(f"Avant : {mesh}")

    mesh.subdivide(beam, n=5)
    print(f"Après : {mesh}")

    for nd in mesh.nodes:
        print(f"  {nd}")
    for el in mesh.elements:
        print(f"  {el}")
