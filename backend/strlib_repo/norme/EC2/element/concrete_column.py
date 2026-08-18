#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe orchestratrice pour la vérification d'un poteau en béton armé,
selon l'Eurocode 2 (EN 1992-1-1) ou la SIA 262:2013.

ConcreteColumn ne contient aucune logique de calcul : elle délègue aux
classes unitaires indépendantes (approche composition — même principe que
``SteelColumn`` / ``SteelBeam``) :

    norme="EC2"      norme.EC2.elu.compression          (§5.2, §5.8)
                     norme.EC2.elu.interaction_diagram  (§6.1, §3.1.7)
    norme="SIA262"   norme.SIA262.elu.compression       (§4.3.7)

Trois méthodes de prise en compte du second ordre (paramètre ``methode``) :

    "courbure"    §5.8.8  — courbure nominale     ← DÉFAUT
    "rigidite"    §5.8.7  — rigidité nominale
    "forfaitaire" Recommandations professionnelles FFB (NRd direct)

Pour la SIA 262, le §4.3.7 est une approche par excentricités cumulées
équivalente en principe à la courbure nominale : elle est utilisée quelle
que soit la méthode demandée, et la méthode retenue est reportée dans le
rapport. Les méthodes « rigidité nominale » et « forfaitaire » sont
propres à l'EC2 / aux RP françaises et n'ont pas d'équivalent SIA.

Unités attendues : forces N, moments N·mm, longueurs mm, contraintes MPa.
"""

__all__ = ['ConcreteColumn', 'METHODES']

import math
from typing import Dict, List, Optional

from core.formula import FormulaResult, FormulaCollection

from norme.EC2.elu.compression import (
    GAMMA_CE, Imperfections, SlendernessEC2,
    NominalStiffness, NominalCurvature, ForfaitaireFFB,
)
from norme.EC2.elu.interaction_diagram import InteractionDiagram
from norme.SIA262.elu.compression import (
    GAMMA_CE_SIA, ES_SIA, CompressedElementSIA,
)

#: Méthodes disponibles (clé → libellé).
METHODES = {
    "courbure": "Courbure nominale (EC2 §5.8.8)",
    "rigidite": "Rigidité nominale (EC2 §5.8.7)",
    "forfaitaire": "Forfaitaire (RP FFB)",
}

_NORMES = ("EC2", "SIA262")


class ConcreteColumn:
    """
    Orchestrateur de vérification d'un poteau béton armé.

    Parameters
    ----------
    norme : str
        ``"EC2"`` ou ``"SIA262"``.
    methode : str
        ``"courbure"`` (défaut), ``"rigidite"`` ou ``"forfaitaire"``.
    shape : str
        ``"rect"`` (rectangulaire) ou ``"circ"`` (circulaire).
    b, h : float
        Dimensions de la section rectangulaire [mm] — ``h`` = dimension
        dans le plan de flexion étudié.
    D : float
        Diamètre de la section circulaire [mm].
    l0 : float
        Longueur efficace de flambement [mm].
    l_real : float, optional
        Longueur réelle de l'élément [mm] (défaut = l0).
    Ned : float
        Effort normal de compression de calcul [N].
    M0Ed_top, M0Ed_bot : float
        Moments d'extrémité du premier ordre [N·mm] (M02 = le plus grand
        en valeur absolue).
    As : float
        Aire totale d'armatures longitudinales [mm²].
    d_prime : float
        Enrobage mécanique des aciers (axe des barres) [mm].
    fck, fyk : float
        Résistances caractéristiques [MPa].
    gamma_c, gamma_s : float
        Coefficients partiels matériaux.
    phi_ef : float
        Coefficient de fluage effectif φef (EC2 §5.8.4).
    c_curvature : float
        Coefficient de distribution des courbures (10 ≈ π² par défaut).
    c0_stiffness : float
        Coefficient c0 de distribution du moment du 1er ordre (8 par défaut).
    """

    def __init__(
        self,
        norme: str = "EC2",
        methode: str = "courbure",
        shape: str = "rect",
        b: float = 0.0,
        h: float = 0.0,
        D: float = 0.0,
        l0: float = 0.0,
        l_real: Optional[float] = None,
        Ned: float = 0.0,
        M0Ed_top: float = 0.0,
        M0Ed_bot: float = 0.0,
        As: float = 0.0,
        d_prime: float = 50.0,
        fck: float = 25.0,
        fyk: float = 500.0,
        gamma_c: float = 1.5,
        gamma_s: float = 1.15,
        Ecm: Optional[float] = None,
        Es: Optional[float] = None,
        phi_ef: float = 2.0,
        c_curvature: float = 10.0,
        c0_stiffness: float = 8.0,
        simplified_imperfections: bool = False,
    ) -> None:
        norme = norme.upper().strip()
        if norme not in _NORMES:
            raise ValueError(f"norme doit être 'EC2' ou 'SIA262' (reçu : '{norme}')")
        methode = methode.lower().strip()
        if methode not in METHODES:
            raise ValueError(
                f"methode doit être parmi {list(METHODES.keys())} (reçu : '{methode}')"
            )
        shape = shape.lower().strip()
        if shape not in ("rect", "circ"):
            raise ValueError(f"shape doit être 'rect' ou 'circ' (reçu : '{shape}')")

        self.__norme = norme
        self.__methode = methode
        self.__shape = shape
        self.__b = b
        self.__h = h
        self.__D = D
        self.__l0 = l0
        self.__l_real = l_real if l_real is not None else l0
        self.__ned = abs(Ned)
        self.__As = As
        self.__d_prime = d_prime
        self.__fck = fck
        self.__fyk = fyk
        self.__gamma_c = gamma_c
        self.__gamma_s = gamma_s
        self.__phi_ef = phi_ef
        self.__c_curv = c_curvature
        self.__c0 = c0_stiffness
        self.__simplified_imp = simplified_imperfections

        # Moments d'extrémité : M02 = |max|, M01 = |min| avec son signe relatif
        m_top, m_bot = M0Ed_top, M0Ed_bot
        if abs(m_bot) > abs(m_top):
            m_top, m_bot = m_bot, m_top
        self.__M02 = abs(m_top)
        self.__M01 = abs(m_bot) * (1.0 if m_top * m_bot >= 0 else -1.0)

        # Matériaux
        self.__Ecm = Ecm if Ecm is not None else self._ecm_default(fck)
        self.__Es = Es if Es is not None else (
            ES_SIA if norme == "SIA262" else 200000.0
        )

    # ------------------------------------------------------------------
    #  Matériaux et géométrie
    # ------------------------------------------------------------------
    @staticmethod
    def _ecm_default(fck: float) -> float:
        """Ecm = 22·((fck+8)/10)^0,3 [GPa] → MPa — EC2 Tableau 3.1."""
        return 22000.0 * ((fck + 8.0) / 10.0) ** 0.3

    @property
    def is_rect(self) -> bool:
        return self.__shape == "rect"

    @property
    def fcd(self) -> float:
        return self.__fck / self.__gamma_c

    @property
    def fyd(self) -> float:
        return self.__fyk / self.__gamma_s

    @property
    def Ac(self) -> float:
        """Aire de béton [mm²]."""
        if self.is_rect:
            return self.__b * self.__h
        return math.pi * self.__D ** 2 / 4.0

    @property
    def dim(self) -> float:
        """Dimension dans le plan de flexion (h ou D) [mm]."""
        return self.__h if self.is_rect else self.__D

    @property
    def Ic(self) -> float:
        """Inertie de la section de béton [mm⁴]."""
        if self.is_rect:
            return self.__b * self.__h ** 3 / 12.0
        return math.pi * self.__D ** 4 / 64.0

    @property
    def i_gyration(self) -> float:
        """Rayon de giration de la section de béton [mm]."""
        return math.sqrt(self.Ic / self.Ac) if self.Ac else 0.0

    @property
    def d(self) -> float:
        """Hauteur utile [mm]."""
        return self.dim - self.__d_prime

    @property
    def Is(self) -> float:
        """
        Inertie des armatures par rapport au centre de la section [mm⁴].
        Deux lits symétriques de As/2 chacun, au bras (dim/2 − d') :
            Is = 2 · (As/2) · bras² = As · bras²
        """
        arm = self.dim / 2.0 - self.__d_prime
        return self.__As * arm ** 2

    @property
    def rho(self) -> float:
        return self.__As / self.Ac if self.Ac else 0.0

    # ------------------------------------------------------------------
    #  Imperfections et moment du premier ordre
    # ------------------------------------------------------------------
    @property
    def imperfections(self) -> Imperfections:
        return Imperfections(
            l0=self.__l0, h=self.dim, l_real=self.__l_real,
            simplified=self.__simplified_imp,
        )

    @property
    def M0e(self) -> float:
        """M0e = 0,6·M02 + 0,4·M01 ≥ 0,4·M02 — éq. (5.32) [N·mm]."""
        val = 0.6 * self.__M02 + 0.4 * self.__M01
        return max(val, 0.4 * self.__M02)

    @property
    def M0Ed(self) -> float:
        """
        Moment du premier ordre incluant les imperfections [N·mm].
        M0Ed = M0e + NEd·ei, avec un plancher NEd·e0,min (§6.1 (4)).
        """
        imp = self.imperfections
        m = self.M0e + self.__ned * imp.ei
        return max(m, self.__ned * imp.e0_min)

    # ------------------------------------------------------------------
    #  Élancement
    # ------------------------------------------------------------------
    @property
    def slenderness(self) -> SlendernessEC2:
        rm = (self.__M01 / self.__M02) if self.__M02 else None
        return SlendernessEC2(
            l0=self.__l0, Ned=self.__ned, Ac=self.Ac, fcd=self.fcd,
            As=self.__As, fyd=self.fyd, i=self.i_gyration,
            phi_ef=self.__phi_ef, rm=rm,
        )

    @property
    def lambda_(self) -> float:
        return self.slenderness.lambda_

    # ------------------------------------------------------------------
    #  Diagramme d'interaction
    # ------------------------------------------------------------------
    @property
    def diagram(self) -> InteractionDiagram:
        """Diagramme N-M de la section (approximation rectangulaire
        équivalente pour les sections circulaires)."""
        b_eq = self.__b if self.is_rect else self.__D
        h_eq = self.__h if self.is_rect else self.__D
        return InteractionDiagram(
            b=b_eq, h=h_eq, As_tot=self.__As, d=self.d,
            d_prime=self.__d_prime, fck=self.__fck, fcd=self.fcd,
            fyd=self.fyd, Es=self.__Es,
        )

    def diagram_curve(self, n_points: int = 60) -> List[Dict[str, float]]:
        """Points (N [kN], M [kN·m]) de l'enveloppe résistante."""
        return self.diagram.curve(n_points=n_points)

    # ------------------------------------------------------------------
    #  Méthodes de second ordre
    # ------------------------------------------------------------------
    def _nominal_curvature(self) -> NominalCurvature:
        return NominalCurvature(
            M0Ed=self.M0Ed, Ned=self.__ned, l0=self.__l0, d=self.d,
            Ac=self.Ac, As=self.__As, fck=self.__fck, fcd=self.fcd,
            fyd=self.fyd, Es=self.__Es, lambda_=self.lambda_,
            phi_ef=self.__phi_ef, c=self.__c_curv,
        )

    def _nominal_stiffness(self) -> NominalStiffness:
        return NominalStiffness(
            M0Ed=self.M0Ed, Ned=self.__ned, l0=self.__l0, Ac=self.Ac,
            As=self.__As, Ic=self.Ic, Is=self.Is, fck=self.__fck,
            fcd=self.fcd, Ecm=self.__Ecm, Es=self.__Es,
            lambda_=self.lambda_, phi_ef=self.__phi_ef, c0=self.__c0,
            gamma_cE=GAMMA_CE,
        )

    def _forfaitaire(self) -> ForfaitaireFFB:
        return ForfaitaireFFB(
            Ned=self.__ned, shape=self.__shape, b=self.__b, h=self.__h,
            D=self.__D, l0=self.__l0, As=self.__As,
            d_prime=self.__d_prime, fcd=self.fcd, fyd=self.fyd,
            fyk=self.__fyk,
        )

    def _sia_element(self) -> CompressedElementSIA:
        return CompressedElementSIA(
            Nd=self.__ned, Md_1=self.M0e, l=self.__l0, d=self.d,
            d_prime=self.__d_prime, fsd=self.fyd, Es=self.__Es,
        )

    @property
    def MEd(self) -> float:
        """
        Moment de calcul total (2e ordre inclus) [N·mm].
        None de sens pour la méthode forfaitaire, qui vérifie directement
        en effort normal — on retourne alors M0Ed.
        """
        if self.__norme == "SIA262":
            return self._sia_element().Md
        if self.__methode == "rigidite":
            return self._nominal_stiffness().MEd
        if self.__methode == "forfaitaire":
            return self.M0Ed
        return self._nominal_curvature().MEd

    # ------------------------------------------------------------------
    #  Vérifications
    # ------------------------------------------------------------------
    def check_slenderness(self, with_values: bool = False) -> FormulaCollection:
        """Critère d'élancement — EC2 §5.8.3.1."""
        return self.slenderness.report(with_values=with_values)

    def check_second_order(self, with_values: bool = False) -> FormulaCollection:
        """Calcul du moment de second ordre selon la méthode retenue."""
        if self.__norme == "SIA262":
            return self._sia_element().report(with_values=with_values)
        if self.__methode == "rigidite":
            return self._nominal_stiffness().report(with_values=with_values)
        if self.__methode == "forfaitaire":
            return self._forfaitaire().report(with_values=with_values)
        return self._nominal_curvature().report(with_values=with_values)

    def check_section(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        Résistance de section en flexion composée sur le diagramme N-M.
        None pour la méthode forfaitaire (qui vérifie en NRd direct).
        """
        if self.__norme == "EC2" and self.__methode == "forfaitaire":
            return None
        return self.diagram.report(
            Ned=self.__ned, Med=self.MEd, with_values=with_values,
        )

    def full_check(self, with_values: bool = False) -> FormulaCollection:
        """Vérification complète."""
        norme_label = (
            "EN 1992-1-1" if self.__norme == "EC2" else "SIA 262:2013"
        )
        fc = FormulaCollection(
            title=(
                f"Vérification poteau béton — {norme_label} "
                f"[{METHODES[self.__methode]}]"
            ),
            ref=norme_label,
        )
        for r in self.imperfections.report(with_values=with_values):
            fc.add(r)
        for r in self.check_slenderness(with_values=with_values):
            fc.add(r)
        for r in self.check_second_order(with_values=with_values):
            fc.add(r)
        sect = self.check_section(with_values=with_values)
        if sect is not None:
            for r in sect:
                fc.add(r)
        return fc

    # ------------------------------------------------------------------
    #  Résumé
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        fc = self.full_check(with_values=False)
        checks = fc.checks
        # Le critère d'élancement est informatif : il indique si le 2e
        # ordre est nécessaire, ce n'est pas un critère de ruine.
        governing_checks = [c for c in checks if c.name != "λ/λlim"]
        ratio = max((c.result for c in governing_checks), default=None)
        governing = None
        if governing_checks:
            governing = max(governing_checks, key=lambda c: c.result).name
        return {
            "norme": self.__norme,
            "methode": self.__methode,
            "methode_label": METHODES[self.__methode],
            "lambda": round(self.lambda_, 2),
            "lambda_lim": round(self.slenderness.lambda_lim, 2),
            "second_order_required": not self.slenderness.second_order_negligible,
            "M0Ed": self.M0Ed,
            "MEd": self.MEd,
            "governing_check": governing,
            "max_ratio": ratio,
            "is_ok": (ratio <= 1.0) if ratio is not None else None,
        }

    def __repr__(self) -> str:
        geo = (
            f"{self.__b:.0f}×{self.__h:.0f}" if self.is_rect
            else f"Ø{self.__D:.0f}"
        )
        return (
            f"ConcreteColumn(norme={self.__norme}, methode={self.__methode}, "
            f"{geo}, l0={self.__l0 / 1e3:.2f}m, NEd={self.__ned / 1e3:.0f}kN, "
            f"λ={self.lambda_:.1f})"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 70

    base = dict(
        shape="rect", b=300.0, h=400.0, l0=3500.0, Ned=900e3,
        M0Ed_top=20e6, M0Ed_bot=10e6, As=1256.0, d_prime=50.0,
        fck=25.0, fyk=500.0, phi_ef=2.0,
    )

    def show(col: ConcreteColumn) -> None:
        s = col.summary()
        print(f"  {col!r}")
        print(
            f"    λ = {s['lambda']:.1f} / λlim = {s['lambda_lim']:.1f}"
            f"  → 2e ordre requis : {s['second_order_required']}"
        )
        print(
            f"    M0Ed = {s['M0Ed'] / 1e6:7.2f} kN·m   "
            f"MEd = {s['MEd'] / 1e6:7.2f} kN·m"
        )
        ratio = s["max_ratio"]
        rtxt = f"{ratio:.4f}" if ratio is not None else "  —  "
        print(
            f"    Déterminant : {str(s['governing_check'] or '—'):22s}"
            f" taux = {rtxt}  ok = {s['is_ok']}"
        )

    print(f"\n{sep}\n  EC2 — les trois méthodes\n{sep}")
    for m in ("courbure", "rigidite", "forfaitaire"):
        print(f"  --- {METHODES[m]} ---")
        show(ConcreteColumn(norme="EC2", methode=m, **base))

    print(f"\n{sep}\n  SIA 262 — §4.3.7\n{sep}")
    show(ConcreteColumn(norme="SIA262", methode="courbure", **base))

    print(f"\n{sep}\n  Diagramme de capacité (extrait)\n{sep}")
    col = ConcreteColumn(norme="EC2", methode="courbure", **base)
    pts = col.diagram_curve(n_points=12)
    for p in pts[::2]:
        print(f"    N = {p['N']:9.1f} kN   M = {p['M']:8.2f} kN·m")

    print(f"\n{sep}\n  Rapport détaillé — courbure nominale\n{sep}")
    print(col.full_check(with_values=True))

    print(f"\n{'=' * 70}\n  FIN DES TESTS\n{'=' * 70}")
