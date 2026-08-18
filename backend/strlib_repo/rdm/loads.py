#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Chargements sur éléments barres pour analyse 2D.
    
    Chaque type de chargement est une dataclass indépendante 
    qui sait calculer ses forces nodales équivalentes.
    
    Types supportés:
        - DistributedLoad  : charge répartie uniforme (N/mm)
        - PointLoadOnBeam  : charge ponctuelle sur barre (N)
        - MomentOnBeam     : moment ponctuel sur barre (N·mm)
        - ThermalLoad      : gradient thermique (°C)
        - PrestressLoad    : précontrainte (N)
    
    Convention:
        - "GLOBAL" : les forces sont dans le repère global (X, Y)
        - "LOCAL"  : les forces sont dans le repère local (x_barre, y_barre)
    
    Forces nodales équivalentes:
        Retournées sous forme [Fx_beg, Fy_beg, Mz_beg, Fx_end, Fy_end, Mz_end]
        dans le repère LOCAL de la barre.
    
    References:
        - Méthode des éléments finis — Barres bi-encastrées
        - Formules classiques RDM
    
    Units: N, mm, rad, °C
"""

__all__ = [
    'DistributedLoad', 'PointLoadOnBeam', 'MomentOnBeam',
    'ThermalLoad', 'PrestressLoad'
]

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import numpy as np
import math


class LoadFrame(Enum):
    """Repère d'application de la charge."""
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"


@dataclass
class DistributedLoad:
    """
        Charge répartie uniforme sur toute la longueur de la barre.
        
        Parameters
        ----------
        fy : float
            Intensité transversale (N/mm), positif = sens Y+ (ou y+ local)
        fx : float
            Intensité axiale (N/mm), positif = sens X+ (ou x+ local)
        frame : str
            "GLOBAL" ou "LOCAL"
        
        Forces nodales équivalentes (barre bi-encastrée):
            Fy : Fy_beg = Fy_end = q·L/2
                 Mz_beg = +q·L²/12
                 Mz_end = -q·L²/12
            Fx : Fx_beg = Fx_end = p·L/2
        
        Examples
        --------
        >>> load = DistributedLoad(fy=-25.0)  # 25 N/mm vers le bas
        >>> f_eq = load.equivalent_nodal_forces(L=6000)
    """
    fy: float = 0.0
    fx: float = 0.0
    frame: str = "GLOBAL"

    def __post_init__(self):
        self.frame = self.frame.upper()
        if self.frame not in ("GLOBAL", "LOCAL"):
            raise ValueError(f"frame must be 'GLOBAL' or 'LOCAL', got '{self.frame}'")

    def equivalent_nodal_forces(self, L: float) -> np.ndarray:
        """
            Calcule les forces nodales équivalentes en repère LOCAL.
            
            Parameters
            ----------
            L : float
                Longueur de la barre (mm)
            
            Returns
            -------
            np.ndarray
                [Fx_beg, Fy_beg, Mz_beg, Fx_end, Fy_end, Mz_end]
            
            Note
            ----
            La rotation global → local doit être gérée par l'élément,
            pas par le chargement. Ici on retourne les valeurs brutes.
        """
        f = np.zeros(6, dtype=float)

        # Transversal
        f[1] = self.fy * L / 2           # Fy_beg
        f[2] = self.fy * L**2 / 12       # Mz_beg
        f[4] = self.fy * L / 2           # Fy_end
        f[5] = -self.fy * L**2 / 12      # Mz_end

        # Axial
        f[0] = self.fx * L / 2           # Fx_beg
        f[3] = self.fx * L / 2           # Fx_end

        return f

    @property
    def has_load(self) -> bool:
        return self.fx != 0 or self.fy != 0

    def __repr__(self) -> str:
        parts = []
        if self.fx != 0: parts.append(f"fx={self.fx:.2f} N/mm")
        if self.fy != 0: parts.append(f"fy={self.fy:.2f} N/mm")
        return f"DistributedLoad({', '.join(parts)}, {self.frame})"


@dataclass
class PointLoadOnBeam:
    """
        Charge ponctuelle sur la barre à une distance 'a' du début.
        
        Parameters
        ----------
        fy : float
            Force transversale (N)
        fx : float
            Force axiale (N)
        a : float
            Distance depuis le nœud de début (mm)
        frame : str
            "GLOBAL" ou "LOCAL"
        
        Forces nodales équivalentes (barre bi-encastrée):
            b = L - a
            Fy_beg = P·b²·(3a+b) / L³
            Fy_end = P·a²·(a+3b) / L³
            Mz_beg = +P·a·b² / L²
            Mz_end = -P·a²·b / L²
    """
    fy: float = 0.0
    fx: float = 0.0
    a: float = 0.0
    frame: str = "GLOBAL"

    def __post_init__(self):
        self.frame = self.frame.upper()
        if self.a < 0:
            raise ValueError(f"Distance 'a' must be >= 0, got {self.a}")

    def equivalent_nodal_forces(self, L: float) -> np.ndarray:
        """
            Forces nodales équivalentes en repère local.
            
            Parameters
            ----------
            L : float
                Longueur de la barre (mm)
            
            Returns
            -------
            np.ndarray
                [Fx_beg, Fy_beg, Mz_beg, Fx_end, Fy_end, Mz_end]
        """
        if self.a > L:
            raise ValueError(f"a={self.a} > L={L} : charge hors de la barre")

        f = np.zeros(6, dtype=float)
        a = self.a
        b = L - a

        # Transversal (formules barre bi-encastrée)
        if L > 0 and self.fy != 0:
            f[1] = self.fy * b**2 * (3 * a + b) / L**3     # Fy_beg
            f[2] = self.fy * a * b**2 / L**2                # Mz_beg
            f[4] = self.fy * a**2 * (a + 3 * b) / L**3     # Fy_end
            f[5] = -self.fy * a**2 * b / L**2               # Mz_end

        # Axial (répartition linéaire)
        if L > 0 and self.fx != 0:
            f[0] = self.fx * b / L    # Fx_beg
            f[3] = self.fx * a / L    # Fx_end

        return f

    @property
    def has_load(self) -> bool:
        return self.fx != 0 or self.fy != 0

    def __repr__(self) -> str:
        parts = []
        if self.fx != 0: parts.append(f"fx={self.fx:.1f} N")
        if self.fy != 0: parts.append(f"fy={self.fy:.1f} N")
        return f"PointLoad({', '.join(parts)}, a={self.a:.1f}, {self.frame})"


@dataclass
class MomentOnBeam:
    """
        Moment ponctuel appliqué sur la barre à distance 'a' du début.
        
        Parameters
        ----------
        mz : float
            Moment (N·mm), positif anti-horaire
        a : float
            Distance depuis le nœud de début (mm)
        
        Forces nodales équivalentes (barre bi-encastrée):
            Fy_beg = +6·M·a·b / L³
            Fy_end = -6·M·a·b / L³
            Mz_beg = M·b·(2a-b) / L²
            Mz_end = M·a·(2b-a) / L²
    """
    mz: float = 0.0
    a: float = 0.0

    def __post_init__(self):
        if self.a < 0:
            raise ValueError(f"Distance 'a' must be >= 0, got {self.a}")

    def equivalent_nodal_forces(self, L: float) -> np.ndarray:
        """
            Forces nodales équivalentes.
            
            Parameters
            ----------
            L : float
                Longueur de la barre (mm)
            
            Returns
            -------
            np.ndarray
                [Fx_beg, Fy_beg, Mz_beg, Fx_end, Fy_end, Mz_end]
        """
        if self.a > L:
            raise ValueError(f"a={self.a} > L={L} : moment hors de la barre")

        f = np.zeros(6, dtype=float)
        a = self.a
        b = L - a
        M = self.mz

        if L > 0 and M != 0:
            f[1] = 6 * M * a * b / L**3              # Fy_beg
            f[2] = M * b * (2 * a - b) / L**2        # Mz_beg
            f[4] = -6 * M * a * b / L**3             # Fy_end
            f[5] = M * a * (2 * b - a) / L**2        # Mz_end

        return f

    @property
    def has_load(self) -> bool:
        return self.mz != 0

    def __repr__(self) -> str:
        return f"Moment({self.mz:.1f} N·mm, a={self.a:.1f})"


@dataclass
class ThermalLoad:
    """
        Chargement thermique sur la barre.
        
        Parameters
        ----------
        delta_t_uniform : float
            Variation uniforme de température (°C)
            → effort axial N = E·A·α·ΔT
        delta_t_gradient : float
            Gradient thermique entre fibres sup/inf (°C)
            → courbure κ = α·ΔTg/h
        alpha : float
            Coefficient de dilatation thermique (1/°C)
            Acier : ~12e-6, Béton : ~10e-6
        
        Note
        ----
        Les forces nodales équivalentes dépendent de E, A, I, h
        qui sont des propriétés de l'élément. Cette classe ne fait
        que stocker les paramètres thermiques.
    """
    delta_t_uniform: float = 0.0
    delta_t_gradient: float = 0.0
    alpha: float = 12e-6  # acier par défaut

    def equivalent_nodal_forces(self, L: float, E: float, A: float,
                                 I: float, h: float) -> np.ndarray:
        """
            Forces nodales équivalentes.
            
            Parameters
            ----------
            L : float
                Longueur (mm)
            E : float
                Module d'Young (MPa)
            A : float
                Aire de la section (mm²)
            I : float
                Inertie (mm⁴)
            h : float
                Hauteur de la section (mm)
            
            Returns
            -------
            np.ndarray
                [Fx_beg, Fy_beg, Mz_beg, Fx_end, Fy_end, Mz_end]
        """
        f = np.zeros(6, dtype=float)

        # Effort axial dû à ΔT uniforme
        N_thermal = E * A * self.alpha * self.delta_t_uniform
        f[0] = -N_thermal    # compression au début
        f[3] = N_thermal     # traction à la fin

        # Moment dû au gradient
        if h > 0:
            M_thermal = E * I * self.alpha * self.delta_t_gradient / h
            f[2] = M_thermal      # Mz_beg
            f[5] = -M_thermal     # Mz_end

        return f

    @property
    def has_load(self) -> bool:
        return self.delta_t_uniform != 0 or self.delta_t_gradient != 0

    def __repr__(self) -> str:
        return (f"Thermal(ΔTu={self.delta_t_uniform:.1f}°C, "
                f"ΔTg={self.delta_t_gradient:.1f}°C)")


@dataclass
class PrestressLoad:
    """
        Chargement de précontrainte sur la barre.
        
        Le tracé du câble est défini par des polynômes par morceaux.
        Chaque morceau est un polynôme [a, b, c] tel que:
            e(x) = a·x² + b·x + c
        où e(x) est l'excentrement par rapport au centre de gravité.
        
        Parameters
        ----------
        force : float
            Force de précontrainte (N), positif = compression
        profile : list of list
            Polynômes par morceaux [[a1,b1,c1], [a2,b2,c2], ...]
        breaks : list of float
            Abscisses de changement de polynôme (mm)
            len(breaks) = len(profile) - 1
        kind : str
            "RIVE" ou "INTER" (type d'about)
        
        Examples
        --------
        >>> ps = PrestressLoad(
        ...     force=1500000,
        ...     profile=[[0.0053, -0.2253, 2.513], [-0.0279, 2.785, -65.55]],
        ...     breaks=[42.5],
        ...     kind="RIVE"
        ... )
    """
    force: float = 0.0
    profile: list = None
    breaks: list = None
    kind: str = "RIVE"

    def __post_init__(self):
        self.profile = self.profile or []
        self.breaks = self.breaks or []
        self.kind = self.kind.upper()

    def eccentricity_at(self, x: float, L: float) -> float:
        """
            Excentrement du câble à l'abscisse x.
            
            Parameters
            ----------
            x : float
                Abscisse le long de la barre (mm)
            L : float
                Longueur de la barre (mm)
            
            Returns
            -------
            float
                Excentrement e(x) (mm)
        """
        if not self.profile:
            return 0.0

        # Déterminer quel polynôme utiliser
        idx = 0
        for i, brk in enumerate(self.breaks):
            if x > brk:
                idx = i + 1
            else:
                break

        idx = min(idx, len(self.profile) - 1)
        a, b, c = self.profile[idx]
        return a * x**2 + b * x + c

    def equivalent_nodal_forces(self, L: float) -> np.ndarray:
        """
            Forces nodales équivalentes dues à la précontrainte.
            
            Modèle simplifié:
                Fx = -P (compression)
                Mz = P · e(x) aux extrémités
            
            Parameters
            ----------
            L : float
                Longueur de la barre (mm)
            
            Returns
            -------
            np.ndarray
                [Fx_beg, Fy_beg, Mz_beg, Fx_end, Fy_end, Mz_end]
        """
        f = np.zeros(6, dtype=float)
        P = self.force

        e_beg = self.eccentricity_at(0, L)
        e_end = self.eccentricity_at(L, L)

        # Effort axial
        f[0] = -P      # compression début
        f[3] = -P      # compression fin

        # Moments dus à l'excentrement
        f[2] = P * e_beg     # Mz_beg
        f[5] = -P * e_end    # Mz_end

        return f

    @property
    def has_load(self) -> bool:
        return self.force != 0 and len(self.profile) > 0

    def __repr__(self) -> str:
        return f"Prestress(P={self.force:.0f} N, {self.kind}, {len(self.profile)} segments)"


# =============================================================================
#  TESTS
# =============================================================================

if __name__ == "__main__":
    L = 6000.0  # mm

    # --- Charge répartie ---
    q = DistributedLoad(fy=-25.0)
    print(q)
    print(f"  Forces nodales : {q.equivalent_nodal_forces(L)}")

    # --- Charge ponctuelle à mi-portée ---
    P = PointLoadOnBeam(fy=-50000, a=3000)
    print(P)
    print(f"  Forces nodales : {P.equivalent_nodal_forces(L)}")

    # --- Moment à mi-portée ---
    M = MomentOnBeam(mz=1e6, a=3000)
    print(M)
    print(f"  Forces nodales : {M.equivalent_nodal_forces(L)}")

    # --- Thermique ---
    T = ThermalLoad(delta_t_uniform=30, delta_t_gradient=10)
    print(T)
    print(f"  Forces nodales : {T.equivalent_nodal_forces(L, 210000, 5000, 1e8, 500)}")

    # --- Précontrainte ---
    ps = PrestressLoad(
        force=1_500_000,
        profile=[[0.0053, -0.2253, 2.513], [-0.0279, 2.785, -65.55]],
        breaks=[42.5],
        kind="RIVE"
    )
    print(ps)
    print(f"  Forces nodales : {ps.equivalent_nodal_forces(L)}")
