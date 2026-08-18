#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define material properties for structural engineering calculations.
"""

__all__ = ['Material']


class Material:
    """
    Classe de base pour les matériaux de structure.

    :param name: Nom du matériau
    :param E: Module d'élasticité [MPa]
    :param nu: Coefficient de Poisson [-]
    :param rho: Masse volumique [kg/m³]
    """

    def __init__(self, name: str = "", E: float = 0.0,
                 nu: float = 0.0, rho: float = 0.0) -> None:
        self._name = name
        self._E = E
        self._nu = nu
        self._rho = rho

    @property
    def name(self) -> str:
        return self._name

    @property
    def E(self) -> float:
        return self._E

    @property
    def nu(self) -> float:
        return self._nu

    @property
    def rho(self) -> float:
        return self._rho

    @property
    def G(self) -> float:
        """Module de cisaillement [MPa]"""
        if self._nu == 0:
            return 0.0
        return self._E / (2 * (1 + self._nu))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', E={self._E}, nu={self._nu}, rho={self._rho})"