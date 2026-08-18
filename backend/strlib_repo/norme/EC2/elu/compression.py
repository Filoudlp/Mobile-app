#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Poteaux béton armé — effets du second ordre, EN 1992-1-1 §5.8
et méthode simplifiée des Recommandations professionnelles FFB.

Vérifications unitaires indépendantes (même principe que
``norme.EC3.elu.*``) : chaque classe accepte soit un ``sec_mat``
(``SecMatRC``), soit des ``**kwargs``.

────────────────────────────────────────────────────────────────────────
IMPERFECTIONS — §5.2
    θ0 = 1/200 (valeur recommandée)
    αh = 2/√l  avec 2/3 ≤ αh ≤ 1   (l en m)
    ei = θi·l0/2                                              éq. (5.2)
    Simplification admise pour poteaux contreventés : ei = l0/400
EXCENTRICITÉ MINIMALE — §6.1 (4)
    e0 = max(h/30 ; 20 mm)

────────────────────────────────────────────────────────────────────────
ÉLANCEMENT LIMITE — §5.8.3.1 (1), éq. (5.13N)
    λlim = 20·A·B·C / √n
    A = 1/(1 + 0,2·φef)   (défaut 0,7 si φef inconnu)
    B = √(1 + 2ω)         (défaut 1,1 si ω inconnu)
    C = 1,7 − rm          (défaut 0,7 si rm inconnu)
    ω = As·fyd/(Ac·fcd)  ;  n = NEd/(Ac·fcd)  ;  rm = M01/M02
    λ = l0/i   (§5.8.3.2, i sur section de béton non fissurée)

FLUAGE — §5.8.4
    φef = φ(∞,t0)·M0Eqp/M0Ed                                  éq. (5.19)

────────────────────────────────────────────────────────────────────────
MÉTHODE « RIGIDITÉ NOMINALE » — §5.8.7
    EI = Kc·Ecd·Ic + Ks·Es·Is                                 éq. (5.21)
    ρ ≥ 0,002 :  Ks = 1 ; Kc = k1·k2/(1 + φef)                éq. (5.22)
        k1 = √(fck/20)                                        éq. (5.23)
        k2 = n·λ/170 ≤ 0,20                                   éq. (5.24)
    ρ ≥ 0,01  :  Ks = 0 ; Kc = 0,3/(1 + 0,5·φef)              éq. (5.26)
    Ecd = Ecm/γcE , γcE = 1,2 (AN française : valeur recommandée retenue)
    MEd = M0Ed·[1 + β/((NB/NEd) − 1)]                         éq. (5.28)
        β = π²/c0 , c0 = 8 (M constant) / 9,6 (parabolique) / 12 (triangulaire)
        NB = π²·EI/l0²

MÉTHODE « COURBURE NOMINALE » — §5.8.8
    MEd = M0Ed + M2                                           éq. (5.31)
    M0e = 0,6·M02 + 0,4·M01 ≥ 0,4·M02                         éq. (5.32)
    M2 = NEd·e2 ,  e2 = (1/r)·l0²/c ,  c = 10 (≈π²)           éq. (5.33)
    1/r = Kr·Kφ·(1/r0)                                        éq. (5.34)
        1/r0 = εyd/(0,45·d) ,  εyd = fyd/Es
        Kr = (nu − n)/(nu − nbal) ≤ 1 , nu = 1+ω , nbal = 0,4 éq. (5.36)
        Kφ = 1 + β·φef ≥ 1 , β = 0,35 + fck/200 − λ/150       éq. (5.37)

────────────────────────────────────────────────────────────────────────
MÉTHODE « FORFAITAIRE » — Recommandations professionnelles FFB
(application de l'EC2 ; méthode nationale admise en alternative aux
§5.8.7/§5.8.8 pour les poteaux courants de bâtiment — transposition
Eurocode de l'ancienne méthode forfaitaire du BAEL, où la section
réduite Br est remplacée par les correctifs kh et ks) :

    NRd = kh·ks·α·(b·h·fcd + As·fyd)          section rectangulaire
    NRd = kh·ks·α·(π·D²/4·fcd + As·fyd)       section circulaire

    RECTANGULAIRE                        CIRCULAIRE
    λ = l0·√12/h                         λ = 4·l0/D
    α = 0,86/(1+(λ/62)²)   si λ ≤ 60     α = 0,84/(1+(λ/52)²)   si λ ≤ 60
    α = (32/λ)^1,3      si 60<λ≤120      α = (27/λ)^1,24     si 60<λ≤120
    kh = (0,75+0,5h)(1−6ρδ)  si h<0,50 m kh = (0,7+0,5D)(1−8ρδ) si D<0,60 m
    ks = 1,6−0,6·fyk/500                 ks = 1,6−0,65·fyk/500
         si fyk>500 et λ>40                   si fyk>500 et λ>30
    δ = d'/h  (d' = enrobage des aciers) ; ρ = As/Ac
    Domaine : λ ≤ 120. As = aciers en 2 lits symétriques (rect.) ou
    6 barres réparties (circ.).
"""

__all__ = [
    'GAMMA_CE', 'Imperfections', 'SlendernessEC2',
    'NominalStiffness', 'NominalCurvature', 'ForfaitaireFFB',
]

import math
from typing import Optional, TypeVar

from core.formula import FormulaResult, FormulaCollection

SecMatRC = TypeVar('SecMatRC')

#: γcE — §5.8.6 (3) éq. (5.20). AN française : valeur recommandée retenue.
GAMMA_CE = 1.2


def _sm(sec_mat, name: str, default=None):
    """Lecture tolérante d'une propriété du sec_mat."""
    if sec_mat is not None and hasattr(sec_mat, name):
        v = getattr(sec_mat, name)
        if v is not None:
            return v
    return default


# ======================================================================
#  §5.2 — Imperfections géométriques  /  §6.1 — excentricité minimale
# ======================================================================

class Imperfections:
    """
    Excentricité d'imperfection et excentricité minimale.

    :param l0: Longueur efficace de flambement [mm].
    :param l_real: Longueur réelle de l'élément [mm] (pour αh). Par
        défaut = l0.
    :param h: Hauteur de section dans le plan de flexion [mm].
    :param simplified: ``True`` → ei = l0/400 (simplification §5.2 (7)a
        pour poteaux contreventés).
    """

    THETA_0 = 1.0 / 200.0

    def __init__(
        self,
        l0: float,
        h: float,
        l_real: Optional[float] = None,
        simplified: bool = False,
    ) -> None:
        self.__l0 = l0
        self.__h = h
        self.__l_real = l_real if l_real is not None else l0
        self.__simplified = simplified

    @property
    def alpha_h(self) -> float:
        """αh = 2/√l  borné à [2/3 ; 1]  (l en m)."""
        l_m = self.__l_real / 1000.0
        if l_m <= 0:
            return 1.0
        return min(max(2.0 / math.sqrt(l_m), 2.0 / 3.0), 1.0)

    @property
    def theta_i(self) -> float:
        """θi = θ0·αh (élément isolé : αm = 1)."""
        return self.THETA_0 * self.alpha_h

    @property
    def ei(self) -> float:
        """Excentricité d'imperfection [mm] — éq. (5.2)."""
        if self.__simplified:
            return self.__l0 / 400.0
        return self.theta_i * self.__l0 / 2.0

    @property
    def e0_min(self) -> float:
        """Excentricité minimale = max(h/30 ; 20 mm) — §6.1 (4)."""
        return max(self.__h / 30.0, 20.0)

    def get_ei(self, with_values: bool = False) -> FormulaResult:
        r = self.ei
        fv = ""
        if with_values:
            if self.__simplified:
                fv = f"ei = l0/400 = {self.__l0:.0f}/400 = {r:.2f} mm"
            else:
                fv = (
                    f"ei = θi·l0/2 = ({self.THETA_0:.4f} × {self.alpha_h:.4f}) "
                    f"× {self.__l0:.0f}/2 = {r:.2f} mm"
                )
        return FormulaResult(
            name="ei", formula="ei = θi·l0/2  (ou l0/400 simplifié)",
            formula_values=fv, result=r, unit="mm",
            ref="EN 1992-1-1 — §5.2 (7), éq. (5.2)",
        )

    def get_e0_min(self, with_values: bool = False) -> FormulaResult:
        r = self.e0_min
        fv = (
            f"e0 = max(h/30 ; 20) = max({self.__h:.0f}/30 ; 20) = {r:.2f} mm"
        ) if with_values else ""
        return FormulaResult(
            name="e0,min", formula="e0 = max(h/30 ; 20 mm)",
            formula_values=fv, result=r, unit="mm",
            ref="EN 1992-1-1 — §6.1 (4)",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Imperfections et excentricité minimale",
            ref="EN 1992-1-1 — §5.2 / §6.1",
        )
        fc.add(self.get_ei(with_values=with_values))
        fc.add(self.get_e0_min(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return f"Imperfections(ei={self.ei:.2f}mm, e0,min={self.e0_min:.2f}mm)"


# ======================================================================
#  §5.8.3.1 — Critère d'élancement
# ======================================================================

class SlendernessEC2:
    """
    Élancement λ et élancement limite λlim — §5.8.3.1 / §5.8.3.2.

    :param l0: Longueur efficace [mm].
    :param Ned: Effort normal de calcul [N] (compression, valeur absolue).
    :param Ac: Aire de béton [mm²].
    :param fcd: Résistance de calcul du béton [MPa].
    :param As: Aire totale d'armatures longitudinales [mm²].
    :param fyd: Résistance de calcul de l'acier [MPa].
    :param i: Rayon de giration de la section de béton [mm].
    :param phi_ef: Coefficient de fluage effectif φef (None = inconnu → A = 0,7).
    :param rm: Rapport M01/M02 (None = inconnu → C = 0,7).
    """

    def __init__(
        self,
        l0: float = 0.0,
        Ned: float = 0.0,
        Ac: float = 0.0,
        fcd: float = 0.0,
        As: float = 0.0,
        fyd: float = 0.0,
        i: float = 0.0,
        phi_ef: Optional[float] = None,
        rm: Optional[float] = None,
    ) -> None:
        self.__l0 = l0
        self.__ned = abs(Ned)
        self.__Ac = Ac
        self.__fcd = fcd
        self.__As = As
        self.__fyd = fyd
        self.__i = i
        self.__phi_ef = phi_ef
        self.__rm = rm

    @property
    def lambda_(self) -> float:
        """λ = l0/i — éq. (5.14)."""
        if self.__i == 0:
            return float('inf')
        return self.__l0 / self.__i

    @property
    def omega(self) -> float:
        """ω = As·fyd/(Ac·fcd) — ratio mécanique d'armatures."""
        denom = self.__Ac * self.__fcd
        if denom == 0:
            return 0.0
        return self.__As * self.__fyd / denom

    @property
    def n(self) -> float:
        """n = NEd/(Ac·fcd) — effort normal relatif."""
        denom = self.__Ac * self.__fcd
        if denom == 0:
            return 0.0
        return self.__ned / denom

    @property
    def A(self) -> float:
        """A = 1/(1+0,2·φef) — 0,7 si φef inconnu."""
        if self.__phi_ef is None:
            return 0.7
        return 1.0 / (1.0 + 0.2 * self.__phi_ef)

    @property
    def B(self) -> float:
        """B = √(1+2ω) — 1,1 si ω inconnu (ici toujours calculable)."""
        if self.__As <= 0:
            return 1.1
        return math.sqrt(1.0 + 2.0 * self.omega)

    @property
    def C(self) -> float:
        """C = 1,7 − rm — 0,7 si rm inconnu."""
        if self.__rm is None:
            return 0.7
        return 1.7 - self.__rm

    @property
    def lambda_lim(self) -> float:
        """λlim = 20·A·B·C/√n — éq. (5.13N)."""
        if self.n <= 0:
            return float('inf')
        return 20.0 * self.A * self.B * self.C / math.sqrt(self.n)

    @property
    def second_order_negligible(self) -> bool:
        """True si λ ≤ λlim → effets du second ordre négligeables."""
        return self.lambda_ <= self.lambda_lim

    def get_lambda(self, with_values: bool = False) -> FormulaResult:
        r = self.lambda_
        fv = (
            f"λ = l0/i = {self.__l0:.0f}/{self.__i:.2f} = {r:.2f}"
        ) if with_values else ""
        return FormulaResult(
            name="λ", formula="λ = l0 / i",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="EN 1992-1-1 — §5.8.3.2, éq. (5.14)",
        )

    def get_lambda_lim(self, with_values: bool = False) -> FormulaResult:
        r = self.lambda_lim
        fv = ""
        if with_values:
            fv = (
                f"λlim = 20 × {self.A:.4f} × {self.B:.4f} × {self.C:.4f} / "
                f"√{self.n:.4f} = {r:.2f}"
            )
        return FormulaResult(
            name="λlim", formula="λlim = 20·A·B·C / √n",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="EN 1992-1-1 — §5.8.3.1 (1), éq. (5.13N)",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = round(self.lambda_ / self.lambda_lim, 4) if self.lambda_lim else float('inf')
        fv = ""
        if with_values:
            verdict = (
                "second ordre NÉGLIGEABLE" if self.second_order_negligible
                else "second ordre À PRENDRE EN COMPTE"
            )
            fv = (
                f"λ/λlim = {self.lambda_:.2f}/{self.lambda_lim:.2f} = {r:.4f} "
                f"→ {verdict}"
            )
        return FormulaResult(
            name="λ/λlim", formula="λ ≤ λlim → effets du 2e ordre négligeables",
            formula_values=fv, result=r, unit="-",
            ref="EN 1992-1-1 — §5.8.3.1 (1)",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Critère d'élancement", ref="EN 1992-1-1 — §5.8.3",
        )
        fc.add(self.get_lambda(with_values=with_values))
        fc.add(self.get_lambda_lim(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"SlendernessEC2(λ={self.lambda_:.2f}, λlim={self.lambda_lim:.2f}, "
            f"2e ordre négligeable={self.second_order_negligible})"
        )


# ======================================================================
#  §5.8.7 — Méthode de la rigidité nominale
# ======================================================================

class NominalStiffness:
    """
    Méthode basée sur une rigidité nominale — §5.8.7.

    :param M0Ed: Moment du premier ordre (imperfections incluses) [N·mm].
    :param Ned: Effort normal de calcul [N].
    :param l0: Longueur efficace [mm].
    :param Ic: Inertie de la section de béton [mm⁴].
    :param Is: Inertie des armatures / centre de la section [mm⁴].
    :param c0: Coefficient de distribution du moment du 1er ordre
        (8 = constant, 9,6 = parabolique, 12 = triangulaire).
    """

    def __init__(
        self,
        M0Ed: float = 0.0,
        Ned: float = 0.0,
        l0: float = 0.0,
        Ac: float = 0.0,
        As: float = 0.0,
        Ic: float = 0.0,
        Is: float = 0.0,
        fck: float = 0.0,
        fcd: float = 0.0,
        Ecm: float = 0.0,
        Es: float = 200000.0,
        lambda_: Optional[float] = None,
        phi_ef: float = 0.0,
        c0: float = 8.0,
        gamma_cE: float = GAMMA_CE,
    ) -> None:
        self.__m0ed = abs(M0Ed)
        self.__ned = abs(Ned)
        self.__l0 = l0
        self.__Ac = Ac
        self.__As = As
        self.__Ic = Ic
        self.__Is = Is
        self.__fck = fck
        self.__fcd = fcd
        self.__Ecm = Ecm
        self.__Es = Es
        self.__lambda = lambda_
        self.__phi_ef = phi_ef
        self.__c0 = c0
        self.__gamma_cE = gamma_cE

    @property
    def rho(self) -> float:
        """ρ = As/Ac — ratio géométrique d'armatures."""
        return self.__As / self.__Ac if self.__Ac else 0.0

    @property
    def n(self) -> float:
        denom = self.__Ac * self.__fcd
        return self.__ned / denom if denom else 0.0

    @property
    def Ecd(self) -> float:
        """Ecd = Ecm/γcE — éq. (5.20)."""
        return self.__Ecm / self.__gamma_cE if self.__gamma_cE else 0.0

    @property
    def k1(self) -> float:
        """k1 = √(fck/20) — éq. (5.23)."""
        return math.sqrt(self.__fck / 20.0) if self.__fck > 0 else 0.0

    @property
    def k2(self) -> float:
        """k2 = n·λ/170 ≤ 0,20 — éq. (5.24) ; sinon n·0,30 — éq. (5.25)."""
        if self.__lambda is None:
            return min(self.n * 0.30, 0.20)
        return min(self.n * self.__lambda / 170.0, 0.20)

    @property
    def uses_simplified(self) -> bool:
        """True si ρ < 0,002 → §5.8.7.2 (2) inapplicable, repli sur (3)."""
        return self.rho < 0.002

    @property
    def Kc(self) -> float:
        """Kc — éq. (5.22) si ρ ≥ 0,002, sinon éq. (5.26)."""
        if self.uses_simplified:
            return 0.3 / (1.0 + 0.5 * self.__phi_ef)
        return self.k1 * self.k2 / (1.0 + self.__phi_ef)

    @property
    def Ks(self) -> float:
        """Ks — 1 si ρ ≥ 0,002 (éq. 5.22), 0 sinon (éq. 5.26)."""
        return 0.0 if self.uses_simplified else 1.0

    @property
    def EI(self) -> float:
        """EI = Kc·Ecd·Ic + Ks·Es·Is — éq. (5.21) [N·mm²]."""
        return self.Kc * self.Ecd * self.__Ic + self.Ks * self.__Es * self.__Is

    @property
    def NB(self) -> float:
        """Charge critique de flambement NB = π²·EI/l0² [N]."""
        if self.__l0 <= 0:
            return 0.0
        return math.pi ** 2 * self.EI / self.__l0 ** 2

    @property
    def beta(self) -> float:
        """β = π²/c0 — éq. (5.29)."""
        return math.pi ** 2 / self.__c0 if self.__c0 else 1.0

    @property
    def MEd(self) -> float:
        """MEd = M0Ed·[1 + β/((NB/NEd) − 1)] — éq. (5.28) [N·mm]."""
        if self.__ned == 0 or self.NB == 0:
            return self.__m0ed
        ratio = self.NB / self.__ned
        if ratio <= 1.0:
            # NEd ≥ NB → instabilité : moment non borné
            return float('inf')
        return self.__m0ed * (1.0 + self.beta / (ratio - 1.0))

    @property
    def is_stable(self) -> bool:
        """False si NEd ≥ NB (instabilité de flambement)."""
        return self.NB > self.__ned

    def get_EI(self, with_values: bool = False) -> FormulaResult:
        r = self.EI
        fv = ""
        if with_values:
            src = "éq. (5.26), ρ < 0,002" if self.uses_simplified else "éq. (5.22)"
            fv = (
                f"EI = {self.Kc:.4f} × {self.Ecd:.0f} × {self.__Ic:.3e} + "
                f"{self.Ks:.0f} × {self.__Es:.0f} × {self.__Is:.3e} "
                f"= {r:.4e} N·mm²  [{src}]"
            )
        return FormulaResult(
            name="EI", formula="EI = Kc·Ecd·Ic + Ks·Es·Is",
            formula_values=fv, result=r, unit="N·mm²",
            ref="EN 1992-1-1 — §5.8.7.2, éq. (5.21)",
        )

    def get_NB(self, with_values: bool = False) -> FormulaResult:
        r = self.NB
        fv = (
            f"NB = π² × {self.EI:.4e} / {self.__l0:.0f}² = {r:.2f} N"
        ) if with_values else ""
        return FormulaResult(
            name="NB", formula="NB = π²·EI / l0²",
            formula_values=fv, result=r, unit="N",
            ref="EN 1992-1-1 — §5.8.7.3",
        )

    def get_MEd(self, with_values: bool = False) -> FormulaResult:
        r = self.MEd
        fv = ""
        if with_values:
            if not self.is_stable:
                fv = (
                    f"NEd = {self.__ned:.0f} N ≥ NB = {self.NB:.0f} N → "
                    f"INSTABILITÉ (moment non borné)"
                )
            else:
                fv = (
                    f"MEd = {self.__m0ed:.0f} × [1 + {self.beta:.4f}/"
                    f"(({self.NB:.0f}/{self.__ned:.0f}) − 1)] = {r:.2f} N·mm"
                )
        return FormulaResult(
            name="MEd", formula="MEd = M0Ed·[1 + β/((NB/NEd) − 1)]",
            formula_values=fv,
            result=r if not math.isinf(r) else 0.0, unit="N·mm",
            ref="EN 1992-1-1 — §5.8.7.3, éq. (5.28)",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Méthode de la rigidité nominale",
            ref="EN 1992-1-1 — §5.8.7",
        )
        fc.add(self.get_EI(with_values=with_values))
        fc.add(self.get_NB(with_values=with_values))
        fc.add(self.get_MEd(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"NominalStiffness(EI={self.EI:.3e}, NB={self.NB:.0f}N, "
            f"MEd={self.MEd:.3e}N·mm, stable={self.is_stable})"
        )


# ======================================================================
#  §5.8.8 — Méthode de la courbure nominale
# ======================================================================

class NominalCurvature:
    """
    Méthode basée sur une courbure nominale — §5.8.8.

    :param M0Ed: Moment du premier ordre (imperfections incluses) [N·mm].
    :param Ned: Effort normal de calcul [N].
    :param l0: Longueur efficace [mm].
    :param d: Hauteur utile [mm].
    :param c: Coefficient de distribution des courbures (10 ≈ π² par
        défaut ; 8 si moment du 1er ordre constant).
    """

    def __init__(
        self,
        M0Ed: float = 0.0,
        Ned: float = 0.0,
        l0: float = 0.0,
        d: float = 0.0,
        Ac: float = 0.0,
        As: float = 0.0,
        fck: float = 0.0,
        fcd: float = 0.0,
        fyd: float = 0.0,
        Es: float = 200000.0,
        lambda_: float = 0.0,
        phi_ef: float = 0.0,
        c: float = 10.0,
        n_bal: float = 0.4,
    ) -> None:
        self.__m0ed = abs(M0Ed)
        self.__ned = abs(Ned)
        self.__l0 = l0
        self.__d = d
        self.__Ac = Ac
        self.__As = As
        self.__fck = fck
        self.__fcd = fcd
        self.__fyd = fyd
        self.__Es = Es
        self.__lambda = lambda_
        self.__phi_ef = phi_ef
        self.__c = c
        self.__n_bal = n_bal

    @property
    def n(self) -> float:
        denom = self.__Ac * self.__fcd
        return self.__ned / denom if denom else 0.0

    @property
    def omega(self) -> float:
        """ω = As·fyd/(Ac·fcd)."""
        denom = self.__Ac * self.__fcd
        return self.__As * self.__fyd / denom if denom else 0.0

    @property
    def n_u(self) -> float:
        """nu = 1 + ω."""
        return 1.0 + self.omega

    @property
    def Kr(self) -> float:
        """Kr = (nu − n)/(nu − nbal) ≤ 1 — éq. (5.36)."""
        denom = self.n_u - self.__n_bal
        if denom <= 0:
            return 1.0
        return min((self.n_u - self.n) / denom, 1.0)

    @property
    def beta_phi(self) -> float:
        """β = 0,35 + fck/200 − λ/150 — éq. (5.37)."""
        return 0.35 + self.__fck / 200.0 - self.__lambda / 150.0

    @property
    def K_phi(self) -> float:
        """Kφ = 1 + β·φef ≥ 1 — éq. (5.37)."""
        return max(1.0 + self.beta_phi * self.__phi_ef, 1.0)

    @property
    def eps_yd(self) -> float:
        """εyd = fyd/Es."""
        return self.__fyd / self.__Es if self.__Es else 0.0

    @property
    def one_over_r0(self) -> float:
        """1/r0 = εyd/(0,45·d) [1/mm]."""
        denom = 0.45 * self.__d
        return self.eps_yd / denom if denom else 0.0

    @property
    def one_over_r(self) -> float:
        """1/r = Kr·Kφ·(1/r0) — éq. (5.34) [1/mm]."""
        return self.Kr * self.K_phi * self.one_over_r0

    @property
    def e2(self) -> float:
        """e2 = (1/r)·l0²/c [mm]."""
        if self.__c == 0:
            return 0.0
        return self.one_over_r * self.__l0 ** 2 / self.__c

    @property
    def M2(self) -> float:
        """M2 = NEd·e2 — éq. (5.33) [N·mm]."""
        return self.__ned * self.e2

    @property
    def MEd(self) -> float:
        """MEd = M0Ed + M2 — éq. (5.31) [N·mm]."""
        return self.__m0ed + self.M2

    def get_Kr(self, with_values: bool = False) -> FormulaResult:
        r = self.Kr
        fv = (
            f"Kr = ({self.n_u:.4f} − {self.n:.4f})/({self.n_u:.4f} − "
            f"{self.__n_bal}) = {r:.4f}  (≤ 1)"
        ) if with_values else ""
        return FormulaResult(
            name="Kr", formula="Kr = (nu − n)/(nu − nbal) ≤ 1",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="EN 1992-1-1 — §5.8.8.3 (3), éq. (5.36)",
        )

    def get_K_phi(self, with_values: bool = False) -> FormulaResult:
        r = self.K_phi
        fv = (
            f"β = 0,35 + {self.__fck:.0f}/200 − {self.__lambda:.2f}/150 = "
            f"{self.beta_phi:.4f} → Kφ = 1 + {self.beta_phi:.4f} × "
            f"{self.__phi_ef:.3f} = {r:.4f}  (≥ 1)"
        ) if with_values else ""
        return FormulaResult(
            name="Kφ", formula="Kφ = 1 + β·φef ≥ 1,  β = 0,35 + fck/200 − λ/150",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="EN 1992-1-1 — §5.8.8.3 (4), éq. (5.37)",
        )

    def get_e2(self, with_values: bool = False) -> FormulaResult:
        r = self.e2
        fv = ""
        if with_values:
            fv = (
                f"1/r = {self.Kr:.4f} × {self.K_phi:.4f} × {self.one_over_r0:.3e} "
                f"= {self.one_over_r:.3e} 1/mm  →  e2 = {self.one_over_r:.3e} × "
                f"{self.__l0:.0f}²/{self.__c:.0f} = {r:.2f} mm"
            )
        return FormulaResult(
            name="e2", formula="e2 = (1/r)·l0²/c ,  1/r = Kr·Kφ·εyd/(0,45d)",
            formula_values=fv, result=r, unit="mm",
            ref="EN 1992-1-1 — §5.8.8.2 (3) / §5.8.8.3",
        )

    def get_MEd(self, with_values: bool = False) -> FormulaResult:
        r = self.MEd
        fv = (
            f"MEd = {self.__m0ed:.0f} + {self.__ned:.0f} × {self.e2:.2f} "
            f"= {r:.2f} N·mm"
        ) if with_values else ""
        return FormulaResult(
            name="MEd", formula="MEd = M0Ed + M2 ,  M2 = NEd·e2",
            formula_values=fv, result=r, unit="N·mm",
            ref="EN 1992-1-1 — §5.8.8.2, éq. (5.31)/(5.33)",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Méthode de la courbure nominale",
            ref="EN 1992-1-1 — §5.8.8",
        )
        fc.add(self.get_Kr(with_values=with_values))
        fc.add(self.get_K_phi(with_values=with_values))
        fc.add(self.get_e2(with_values=with_values))
        fc.add(self.get_MEd(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"NominalCurvature(Kr={self.Kr:.4f}, Kφ={self.K_phi:.4f}, "
            f"e2={self.e2:.2f}mm, MEd={self.MEd:.3e}N·mm)"
        )


# ======================================================================
#  Méthode forfaitaire — Recommandations professionnelles FFB
# ======================================================================

class ForfaitaireFFB:
    """
    Méthode simplifiée « forfaitaire » pour poteaux courants —
    Recommandations professionnelles FFB (application de l'EC2).

    Donne directement l'effort normal résistant NRd, sans passer par un
    calcul de moment du second ordre. Domaine : λ ≤ 120, poteaux de
    bâtiment courants, armatures en 2 lits symétriques (section
    rectangulaire) ou 6 barres réparties (section circulaire).

    :param Ned: Effort normal de calcul [N].
    :param shape: ``"rect"`` ou ``"circ"``.
    :param b, h: Dimensions de la section rectangulaire [mm]
        (h = épaisseur dans le sens du flambement).
    :param D: Diamètre de la section circulaire [mm].
    :param l0: Longueur efficace [mm].
    :param As: Aire totale d'armatures [mm²].
    :param d_prime: Enrobage des aciers d' [mm].
    """

    def __init__(
        self,
        Ned: float = 0.0,
        shape: str = "rect",
        b: float = 0.0,
        h: float = 0.0,
        D: float = 0.0,
        l0: float = 0.0,
        As: float = 0.0,
        d_prime: Optional[float] = None,
        fcd: float = 0.0,
        fyd: float = 0.0,
        fyk: float = 500.0,
    ) -> None:
        shape = shape.lower().strip()
        if shape not in ("rect", "circ"):
            raise ValueError(f"shape doit être 'rect' ou 'circ' (reçu : '{shape}')")
        self.__shape = shape
        self.__ned = abs(Ned)
        self.__b = b
        self.__h = h
        self.__D = D
        self.__l0 = l0
        self.__As = As
        self.__d_prime = d_prime
        self.__fcd = fcd
        self.__fyd = fyd
        self.__fyk = fyk

    @property
    def is_rect(self) -> bool:
        return self.__shape == "rect"

    @property
    def Ac(self) -> float:
        """Aire de béton [mm²]."""
        if self.is_rect:
            return self.__b * self.__h
        return math.pi * self.__D ** 2 / 4.0

    @property
    def lambda_(self) -> float:
        """λ = l0·√12/h (rect.) ou 4·l0/D (circ.)."""
        if self.is_rect:
            return self.__l0 * math.sqrt(12.0) / self.__h if self.__h else float('inf')
        return 4.0 * self.__l0 / self.__D if self.__D else float('inf')

    @property
    def in_range(self) -> bool:
        """Domaine de validité : λ ≤ 120."""
        return self.lambda_ <= 120.0

    @property
    def alpha(self) -> float:
        """α — coefficient de flambement."""
        lam = self.lambda_
        if self.is_rect:
            if lam <= 60.0:
                return 0.86 / (1.0 + (lam / 62.0) ** 2)
            return (32.0 / lam) ** 1.3 if lam <= 120.0 else 0.0
        if lam <= 60.0:
            return 0.84 / (1.0 + (lam / 52.0) ** 2)
        return (27.0 / lam) ** 1.24 if lam <= 120.0 else 0.0

    @property
    def rho(self) -> float:
        """ρ = As/Ac."""
        return self.__As / self.Ac if self.Ac else 0.0

    @property
    def delta(self) -> Optional[float]:
        """δ = d'/h (rect.) ou d'/D (circ.). None si d' non renseigné."""
        if self.__d_prime is None:
            return None
        ref = self.__h if self.is_rect else self.__D
        return self.__d_prime / ref if ref else None

    @property
    def kh(self) -> float:
        """kh — correctif d'échelle (h en m). 0,93 si ρ ou δ inconnus."""
        dim_m = (self.__h if self.is_rect else self.__D) / 1000.0
        threshold = 0.50 if self.is_rect else 0.60
        if dim_m >= threshold:
            return 1.0
        if self.delta is None:
            return 0.93  # valeur conservative admise par les RP
        coef = 6.0 if self.is_rect else 8.0
        base = (0.75 + 0.5 * dim_m) if self.is_rect else (0.7 + 0.5 * dim_m)
        return base * (1.0 - coef * self.rho * self.delta)

    @property
    def ks(self) -> float:
        """ks — correctif de nuance d'acier."""
        lam_threshold = 40.0 if self.is_rect else 30.0
        if self.__fyk <= 500.0 or self.lambda_ <= lam_threshold:
            return 1.0
        coef = 0.6 if self.is_rect else 0.65
        return 1.6 - coef * self.__fyk / 500.0

    @property
    def n_rd(self) -> float:
        """NRd = kh·ks·α·(Ac·fcd + As·fyd) [N]."""
        return self.kh * self.ks * self.alpha * (
            self.Ac * self.__fcd + self.__As * self.__fyd
        )

    @property
    def verif(self) -> float:
        if self.n_rd == 0:
            return float('inf')
        return round(self.__ned / self.n_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def get_lambda(self, with_values: bool = False) -> FormulaResult:
        r = self.lambda_
        formula = "λ = l0·√12/h" if self.is_rect else "λ = 4·l0/D"
        dim = self.__h if self.is_rect else self.__D
        fv = ""
        if with_values:
            note = "" if self.in_range else "  ⚠ HORS DOMAINE (λ > 120)"
            fv = f"λ = {self.__l0:.0f} × {'√12' if self.is_rect else '4'} / {dim:.0f} = {r:.2f}{note}"
        return FormulaResult(
            name="λ", formula=formula,
            formula_values=fv, result=round(r, 4), unit="-",
            ref="RP FFB — méthode simplifiée poteaux",
        )

    def get_alpha(self, with_values: bool = False) -> FormulaResult:
        r = self.alpha
        lam = self.lambda_
        if self.is_rect:
            branch = "0,86/(1+(λ/62)²)" if lam <= 60 else "(32/λ)^1,3"
        else:
            branch = "0,84/(1+(λ/52)²)" if lam <= 60 else "(27/λ)^1,24"
        fv = f"α = {branch} = {r:.4f}  (λ = {lam:.2f})" if with_values else ""
        return FormulaResult(
            name="α", formula=f"α = {branch}",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="RP FFB — méthode simplifiée poteaux",
        )

    def get_kh(self, with_values: bool = False) -> FormulaResult:
        r = self.kh
        fv = ""
        if with_values:
            dim_m = (self.__h if self.is_rect else self.__D) / 1000.0
            threshold = 0.50 if self.is_rect else 0.60
            if dim_m >= threshold:
                fv = f"{'h' if self.is_rect else 'D'} = {dim_m:.3f} m ≥ {threshold} m → kh = 1"
            elif self.delta is None:
                fv = "δ inconnu (d' non renseigné) → kh = 0,93 (valeur conservative RP)"
            else:
                coef = 6.0 if self.is_rect else 8.0
                base = (0.75 + 0.5 * dim_m) if self.is_rect else (0.7 + 0.5 * dim_m)
                fv = (
                    f"kh = {base:.4f} × (1 − {coef:.0f} × {self.rho:.5f} × "
                    f"{self.delta:.4f}) = {r:.4f}"
                )
        formula = (
            "kh = (0,75+0,5h)(1−6ρδ)" if self.is_rect
            else "kh = (0,7+0,5D)(1−8ρδ)"
        )
        return FormulaResult(
            name="kh", formula=formula,
            formula_values=fv, result=round(r, 4), unit="-",
            ref="RP FFB — méthode simplifiée poteaux",
        )

    def get_ks(self, with_values: bool = False) -> FormulaResult:
        r = self.ks
        coef = 0.6 if self.is_rect else 0.65
        lam_threshold = 40.0 if self.is_rect else 30.0
        fv = ""
        if with_values:
            if r == 1.0:
                fv = (
                    f"fyk = {self.__fyk:.0f} MPa ≤ 500 ou λ = {self.lambda_:.1f} "
                    f"≤ {lam_threshold:.0f} → ks = 1"
                )
            else:
                fv = f"ks = 1,6 − {coef} × {self.__fyk:.0f}/500 = {r:.4f}"
        return FormulaResult(
            name="ks", formula=f"ks = 1,6 − {coef}·fyk/500  (si fyk>500 et λ>{lam_threshold:.0f})",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="RP FFB — méthode simplifiée poteaux",
        )

    def get_n_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.n_rd
        fv = ""
        if with_values:
            ac_term = "b·h" if self.is_rect else "πD²/4"
            fv = (
                f"NRd = {self.kh:.4f} × {self.ks:.4f} × {self.alpha:.4f} × "
                f"({self.Ac:.0f} × {self.__fcd:.2f} + {self.__As:.0f} × "
                f"{self.__fyd:.2f}) = {r:.2f} N   [{ac_term}]"
            )
        return FormulaResult(
            name="NRd", formula="NRd = kh·ks·α·(Ac·fcd + As·fyd)",
            formula_values=fv, result=r, unit="N",
            ref="RP FFB — méthode simplifiée poteaux",
        )

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"NEd / NRd = {self.__ned:.0f} / {self.n_rd:.0f} = {r:.4f} "
                f"≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="NEd/NRd", formula="NEd / NRd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="RP FFB — méthode simplifiée poteaux",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Méthode forfaitaire (RP FFB)",
            ref="Recommandations professionnelles FFB — EC2",
        )
        fc.add(self.get_lambda(with_values=with_values))
        fc.add(self.get_alpha(with_values=with_values))
        fc.add(self.get_kh(with_values=with_values))
        fc.add(self.get_ks(with_values=with_values))
        fc.add(self.get_n_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"ForfaitaireFFB(λ={self.lambda_:.2f}, α={self.alpha:.4f}, "
            f"kh={self.kh:.4f}, ks={self.ks:.4f}, NRd={self.n_rd:.0f}N, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 66
    # Poteau 300×400, C25/30, 4HA20 (12,57 cm²), l0 = 3,5 m, NEd = 900 kN
    b, h = 300.0, 400.0
    Ac = b * h
    As = 1256.0
    fck, fcd = 25.0, 25.0 / 1.5
    fyk, fyd, Es = 500.0, 500.0 / 1.15, 200000.0
    Ecm = 31000.0
    Ic = b * h ** 3 / 12.0
    i = h / math.sqrt(12.0)
    l0 = 3500.0
    Ned = 900e3
    d, d_prime = 350.0, 50.0
    Is = As / 2.0 * (h / 2 - d_prime) ** 2 * 2  # 2 lits symétriques

    print(f"\n{sep}\n  Imperfections\n{sep}")
    imp = Imperfections(l0=l0, h=h)
    print(f"  {imp!r}")

    print(f"\n{sep}\n  §5.8.3.1 — Élancement\n{sep}")
    sl = SlendernessEC2(l0=l0, Ned=Ned, Ac=Ac, fcd=fcd, As=As, fyd=fyd,
                        i=i, phi_ef=2.0, rm=None)
    print(f"  {sl!r}")
    print(sl.report(with_values=True))

    M0Ed = Ned * (imp.ei + max(imp.e0_min, 0))
    print(f"\n{sep}\n  §5.8.7 — Rigidité nominale\n{sep}")
    ns = NominalStiffness(
        M0Ed=M0Ed, Ned=Ned, l0=l0, Ac=Ac, As=As, Ic=Ic, Is=Is,
        fck=fck, fcd=fcd, Ecm=Ecm, Es=Es, lambda_=sl.lambda_, phi_ef=2.0,
    )
    print(f"  {ns!r}")

    print(f"\n{sep}\n  §5.8.8 — Courbure nominale\n{sep}")
    nc = NominalCurvature(
        M0Ed=M0Ed, Ned=Ned, l0=l0, d=d, Ac=Ac, As=As,
        fck=fck, fcd=fcd, fyd=fyd, Es=Es, lambda_=sl.lambda_, phi_ef=2.0,
    )
    print(f"  {nc!r}")
    print(nc.report(with_values=True))

    print(f"\n{sep}\n  Forfaitaire FFB\n{sep}")
    ff = ForfaitaireFFB(
        Ned=Ned, shape="rect", b=b, h=h, l0=l0, As=As,
        d_prime=d_prime, fcd=fcd, fyd=fyd, fyk=fyk,
    )
    print(f"  {ff!r}")
    print(ff.report(with_values=True))

    print(f"\n{'=' * 66}\n  FIN DES TESTS\n{'=' * 66}")
