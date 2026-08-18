#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Diagramme d'interaction N-M d'une section rectangulaire en béton armé —
EN 1992-1-1 §3.1.7 (diagramme rectangulaire simplifié) et §6.1.

Construit la courbe de capacité (NRd, MRd) de la section par compatibilité
des déformations, en balayant la profondeur de l'axe neutre x. Permet de
situer le point de calcul (NEd, MEd) par rapport à l'enveloppe résistante.

Diagramme rectangulaire simplifié — §3.1.7 (3), Figure 3.5 :
    λ = 0,8              pour fck ≤ 50 MPa
    λ = 0,8 − (fck−50)/400   pour 50 < fck ≤ 90 MPa
    η = 1,0              pour fck ≤ 50 MPa
    η = 1,0 − (fck−50)/200   pour 50 < fck ≤ 90 MPa
    Contrainte = η·fcd sur une hauteur λ·x depuis la fibre la plus comprimée.

Déformations limites — Tableau 3.1 :
    εcu3 = 3,5 ‰                       pour fck ≤ 50
    εcu3 = 2,6 + 35·((90−fck)/100)⁴ ‰  pour fck > 50
    εc3  = 1,75 ‰                      pour fck ≤ 50
    εc3  = 1,75 + 0,55·(fck−50)/40 ‰   pour fck > 50

Pivots (§6.1, Figure 6.1) :
    - x ≤ h : pivot B — εcu3 sur la fibre supérieure.
    - x > h : pivot C — section entièrement comprimée, rotation autour du
      point situé à la profondeur y_C = h·(1 − εc3/εcu3) où ε = εc3.

Convention de signe : compression POSITIVE pour N ; M positif = traction
en fibre inférieure. Section symétrique (2 lits d'armatures) — le
diagramme est donc symétrique en M, seule la branche M ≥ 0 est calculée.
"""

__all__ = [
    'lambda_block', 'eta_block', 'eps_cu3', 'eps_c3',
    'InteractionDiagram',
]

import math
from typing import Dict, List, Optional, Tuple

from core.formula import FormulaResult, FormulaCollection


def lambda_block(fck: float) -> float:
    """λ — hauteur relative du diagramme rectangulaire, §3.1.7 (3)."""
    if fck <= 50.0:
        return 0.8
    return 0.8 - (fck - 50.0) / 400.0


def eta_block(fck: float) -> float:
    """η — coefficient de contrainte du diagramme rectangulaire, §3.1.7 (3)."""
    if fck <= 50.0:
        return 1.0
    return 1.0 - (fck - 50.0) / 200.0


def eps_cu3(fck: float) -> float:
    """εcu3 — Tableau 3.1 [-]."""
    if fck <= 50.0:
        return 3.5e-3
    return (2.6 + 35.0 * ((90.0 - fck) / 100.0) ** 4) * 1e-3


def eps_c3(fck: float) -> float:
    """εc3 — Tableau 3.1 [-]."""
    if fck <= 50.0:
        return 1.75e-3
    return (1.75 + 0.55 * (fck - 50.0) / 40.0) * 1e-3


class InteractionDiagram:
    """
    Diagramme d'interaction N-M d'une section rectangulaire armée
    symétriquement (2 lits).

    :param b: Largeur de la section [mm].
    :param h: Hauteur de la section dans le plan de flexion [mm].
    :param As_tot: Aire totale d'armatures longitudinales [mm²],
        répartie à parts égales entre les deux lits.
    :param d: Hauteur utile du lit tendu [mm].
    :param d_prime: Distance du lit comprimé à la fibre comprimée [mm].
    :param fck, fcd, fyd, Es: Propriétés matériaux [MPa].
    """

    def __init__(
        self,
        b: float,
        h: float,
        As_tot: float,
        d: float,
        d_prime: float,
        fck: float,
        fcd: float,
        fyd: float,
        Es: float = 200000.0,
    ) -> None:
        self.__b = b
        self.__h = h
        self.__As = As_tot
        self.__d = d
        self.__d_prime = d_prime
        self.__fck = fck
        self.__fcd = fcd
        self.__fyd = fyd
        self.__Es = Es

        # Deux lits symétriques : moitié de l'acier de chaque côté.
        self.__layers: List[Tuple[float, float]] = [
            (d_prime, As_tot / 2.0),   # lit proche de la fibre comprimée
            (d, As_tot / 2.0),         # lit opposé
        ]

    # ------------------------------------------------------------------
    #  Paramètres du diagramme rectangulaire
    # ------------------------------------------------------------------
    @property
    def lambda_(self) -> float:
        return lambda_block(self.__fck)

    @property
    def eta(self) -> float:
        return eta_block(self.__fck)

    @property
    def eps_cu(self) -> float:
        return eps_cu3(self.__fck)

    @property
    def eps_c(self) -> float:
        return eps_c3(self.__fck)

    @property
    def y_C(self) -> float:
        """Profondeur du pivot C : y_C = h·(1 − εc3/εcu3) [mm]."""
        return self.__h * (1.0 - self.eps_c / self.eps_cu)

    # ------------------------------------------------------------------
    #  Compatibilité des déformations
    # ------------------------------------------------------------------
    def strain_at(self, y: float, x: float) -> float:
        """
        Déformation à la profondeur ``y`` (depuis la fibre supérieure)
        pour une profondeur d'axe neutre ``x``. Compression positive.
        """
        if x <= 0:
            return 0.0
        if x <= self.__h:
            # Pivot B : εcu3 en fibre supérieure
            return self.eps_cu * (x - y) / x
        # Pivot C : rotation autour de (y_C, εc3)
        denom = x - self.y_C
        if denom == 0:
            return self.eps_c
        return self.eps_c * (x - y) / denom

    def sigma_s(self, eps: float) -> float:
        """Contrainte acier (élasto-plastique parfait), compression positive."""
        return max(min(self.__Es * eps, self.__fyd), -self.__fyd)

    # ------------------------------------------------------------------
    #  Un point du diagramme
    # ------------------------------------------------------------------
    def point(self, x: float) -> Tuple[float, float]:
        """
        (NRd, MRd) pour une profondeur d'axe neutre x [mm].
        NRd en N (compression +), MRd en N·mm (par rapport au centre).
        """
        # --- Béton : bloc rectangulaire de hauteur λx, plafonné à h ---
        a = min(self.lambda_ * x, self.__h) if x > 0 else 0.0
        Fc = self.eta * self.__fcd * self.__b * a
        Mc = Fc * (self.__h / 2.0 - a / 2.0)

        # --- Acier ---
        N = Fc
        M = Mc
        for (di, Asi) in self.__layers:
            eps = self.strain_at(di, x)
            sig = self.sigma_s(eps)
            # Le béton est déjà compté sur la hauteur a : on déduit la
            # contrainte béton là où l'acier comprimé s'y superpose.
            if di <= a:
                sig -= self.eta * self.__fcd
            Fs = sig * Asi
            N += Fs
            M += Fs * (self.__h / 2.0 - di)
        return N, M

    # ------------------------------------------------------------------
    #  Courbe complète
    # ------------------------------------------------------------------
    def curve(self, n_points: int = 60) -> List[Dict[str, float]]:
        """
        Points de l'enveloppe résistante, du point de traction pure au
        point de compression pure.

        :return: liste de ``{"N": [kN], "M": [kN·m]}`` triée par N croissant.
        """
        pts: List[Tuple[float, float]] = []

        # Traction pure : tout l'acier plastifié en traction, béton inactif.
        pts.append((-self.__As * self.__fyd, 0.0))

        # Balayage de l'axe neutre. La borne haute (3h) sature le pivot C
        # et donne la compression pure.
        x_max = 3.0 * self.__h
        for k in range(1, n_points + 1):
            # Répartition non linéaire : plus de points côté flexion.
            t = k / n_points
            x = x_max * t ** 2
            pts.append(self.point(x))

        # Compression pure (x → ∞) : béton sur toute la hauteur + acier à fyd.
        n_pure = (
            self.eta * self.__fcd * self.__b * self.__h
            + self.__As * self.__fyd
            - self.eta * self.__fcd * self.__As
        )
        pts.append((n_pure, 0.0))

        pts.sort(key=lambda p: p[0])
        return [
            {"N": round(n / 1e3, 3), "M": round(m / 1e6, 4)} for n, m in pts
        ]

    # ------------------------------------------------------------------
    #  Capacité en moment pour un effort normal donné
    # ------------------------------------------------------------------
    def M_rd_at_N(self, Ned: float, tol: float = 1e-3) -> float:
        """
        Moment résistant MRd [N·mm] correspondant à l'effort normal NEd [N]
        (compression positive), par recherche dichotomique sur x.
        """
        lo, hi = 1e-6, 5.0 * self.__h
        n_lo, _ = self.point(lo)
        n_hi, _ = self.point(hi)
        if Ned <= n_lo:
            return max(self.point(lo)[1], 0.0)
        if Ned >= n_hi:
            return 0.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            n_mid, _ = self.point(mid)
            if abs(n_mid - Ned) < tol * max(abs(Ned), 1.0):
                break
            if n_mid < Ned:
                lo = mid
            else:
                hi = mid
        return max(self.point(0.5 * (lo + hi))[1], 0.0)

    def utilisation(self, Ned: float, Med: float) -> float:
        """
        Taux de travail MEd/MRd(NEd) — position du point de calcul par
        rapport à l'enveloppe.
        """
        m_rd = self.M_rd_at_N(Ned)
        if m_rd <= 0:
            return float('inf') if abs(Med) > 0 else 0.0
        return round(abs(Med) / m_rd, 4)

    # ------------------------------------------------------------------
    #  Rapport
    # ------------------------------------------------------------------
    def get_verif(self, Ned: float, Med: float,
                  with_values: bool = False) -> FormulaResult:
        m_rd = self.M_rd_at_N(Ned)
        r = self.utilisation(Ned, Med)
        fv = ""
        if with_values:
            status = "OK ✓" if r <= 1.0 else "NON VÉRIFIÉ ✗"
            fv = (
                f"MEd / MRd(NEd) = {abs(Med) / 1e6:.2f} / {m_rd / 1e6:.2f} "
                f"kN·m = {r:.4f} ≤ 1,0 → {status}   "
                f"[NEd = {Ned / 1e3:.1f} kN]"
            )
        return FormulaResult(
            name="MEd/MRd(NEd)",
            formula="Vérification en flexion composée sur le diagramme N-M",
            formula_values=fv, result=r, unit="-",
            ref="EN 1992-1-1 — §6.1",
            is_check=True, limit=1.0,
        )

    def report(self, Ned: float, Med: float,
               with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Résistance de la section en flexion composée",
            ref="EN 1992-1-1 — §6.1 / §3.1.7",
        )
        m_rd = self.M_rd_at_N(Ned)
        fc.add(FormulaResult(
            name="MRd(NEd)",
            formula="Moment résistant pour NEd (diagramme d'interaction)",
            formula_values=(
                f"MRd = {m_rd:.0f} N·mm = {m_rd / 1e6:.2f} kN·m"
                if with_values else ""
            ),
            result=m_rd, unit="N·mm", ref="EN 1992-1-1 — §6.1",
        ))
        fc.add(self.get_verif(Ned, Med, with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"InteractionDiagram(b={self.__b:.0f}, h={self.__h:.0f}, "
            f"As={self.__As:.0f}mm², λ={self.lambda_:.2f}, η={self.eta:.2f})"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 66
    diag = InteractionDiagram(
        b=300.0, h=400.0, As_tot=1256.0, d=350.0, d_prime=50.0,
        fck=25.0, fcd=25.0 / 1.5, fyd=500.0 / 1.15, Es=200000.0,
    )
    print(f"\n{sep}\n  {diag!r}\n{sep}")

    print("\n  Quelques points caractéristiques :")
    for x in (50.0, 100.0, 200.0, 400.0, 1200.0):
        n, m = diag.point(x)
        print(f"    x = {x:7.1f} mm  →  N = {n / 1e3:9.1f} kN   M = {m / 1e6:8.2f} kN·m")

    pts = diag.curve(n_points=40)
    n_min = min(p["N"] for p in pts)
    n_max = max(p["N"] for p in pts)
    m_max = max(p["M"] for p in pts)
    print(f"\n  Enveloppe : N de {n_min:.0f} à {n_max:.0f} kN, M max = {m_max:.2f} kN·m")
    print(f"  Nombre de points : {len(pts)}")

    print(f"\n{sep}\n  Vérification NEd = 900 kN, MEd = 48 kN·m\n{sep}")
    print(diag.report(Ned=900e3, Med=48e6, with_values=True))

    print(f"\n{'=' * 66}\n  FIN DES TESTS\n{'=' * 66}")
