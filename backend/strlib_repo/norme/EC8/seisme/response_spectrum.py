#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Spectre de réponse sismique — France (NF EN 1998-1 + NF EN 1998-1/NA) et
Suisse (SIA 261:2020, chapitre 16 "Séisme").

Vérification unitaire indépendante (même principe que ``norme.EC1.neige.*`` /
``norme.EC1.vent.*``) : chaque classe ne dépend que des grandeurs qui lui
sont propres (zone/classe de terrain, ou zone/terrain/q/classe d'ouvrage),
pas d'un objet "site" composite.

Forme du spectre — commune aux deux pays (forme normalisée EC8, reprise
telle quelle par la SIA 261) : voir ``_elastic_se`` / ``_design_sd``
ci-dessous pour les 4 branches (0-TB, TB-TC, TC-TD, TD-∞).

────────────────────────────────────────────────────────────────────────
FRANCE — NF EN 1998-1:2005 (§3.1.2, §3.2.1, §3.2.2.2, §3.2.2.5) + NA
────────────────────────────────────────────────────────────────────────
Classes de sol A à E et valeurs recommandées de S/TB/TC/TD — lues
directement dans le corps de l'Eurocode (Tableau 3.1 : classes de sol ;
Tableau 3.3 : spectre de type 2, retenu ici — voir avertissement plus bas).

    ag = γI · agR                                   éq. non numérotée, §3.2.1(3)
    Se(T) = ag·S·[1 + (T/TB)·(2,5·η − 1)]            0 ≤ T < TB      éq. (3.2)
    Se(T) = ag·S·2,5·η                                TB ≤ T ≤ TC     éq. (3.3)
    Se(T) = ag·S·2,5·η·(TC/T)                         TC < T ≤ TD     éq. (3.4)
    Se(T) = ag·S·2,5·η·(TC·TD/T²)                     TD < T          éq. (3.5)
    η = max(√(10/(5+ξ)) ; 0,55)                                       éq. (3.6)

    Sd(T) = ag·S·[2/3 + (T/TB)·(2,5/q − 2/3)]        0 ≤ T < TB      éq. (3.13)
    Sd(T) = ag·S·2,5/q                                TB ≤ T ≤ TC     éq. (3.14)
    Sd(T) = ag·S·(2,5/q)·(TC/T)  ≥ β·ag               TC < T ≤ TD     éq. (3.15)
    Sd(T) = ag·S·(2,5/q)·(TC·TD/T²)  ≥ β·ag           TD < T          éq. (3.16)
    β = 0,2 (valeur recommandée — confirmée retenue pour la France par la NA,
    clause 3.2.2.5(4)P : « La valeur de β à utiliser pour les bâtiments est
    celle recommandée »).

    Point important : contrairement à la Suisse (où γf n'intervient qu'au
    stade du spectre de dimensionnement), en EC8 le facteur d'importance γI
    est incorporé UNE SEULE FOIS dans ag = γI·agR, en amont ; Se(T) ET Sd(T)
    utilisent ensuite le même ag (§3.2.2.5(4)P : « ag, S, TC et TD sont
    définis en 3.2.2.2 »).

    ⚠ AVERTISSEMENT — deux jeux de données distincts, deux niveaux de
    confiance :
    1) Classes de sol A-E et Tableau 3.3 (S/TB/TC/TD, spectre type 2) :
       lus directement dans NF EN 1998-1:2005 (texte réel, non OCRisé) —
       fiables.
    2) Zones sismiques françaises (1 à 5) → agR, et catégories d'importance
       (I à IV) → γI : la NF EN 1998-1/NA lue intégralement (18 pages) NE
       CONTIENT PAS ces valeurs — elle renvoie explicitement à
       « l'Administration française » pour chacune (le zonage et les agR
       sont publiés séparément par l'arrêté du 22 octobre 2010 modifié,
       hors Eurocode/AFNOR). Les valeurs ci-dessous (agR : 0,4/0,7/1,1/1,6/
       3,0 m/s² ; γI : 0,8/1,0/1,2/1,4) proviennent de la connaissance
       générale de cet arrêté, PAS d'un document lu dans cette session —
       à vérifier contre le texte réglementaire consolidé (Légifrance)
       avant tout usage réel. Le choix du spectre de type 2 pour la France
       (séismes de magnitude modérée) est également une inférence non
       vérifiée contre un document source.
       La zone sismique est une saisie directe (pas de table par commune
       ici) — comme les zones neige/vent CH, mais ici faute de document
       source plutôt que par nature cartographique.

────────────────────────────────────────────────────────────────────────
SUISSE — SIA 261:2020, chapitre 16 "Séisme"
────────────────────────────────────────────────────────────────────────
Zones sismiques — SIA 261 §16.2.1, valeurs de dimensionnement de
l'accélération horizontale du sol agd (classe de terrain A, période de
retour de référence 475 ans) :
    Z1a = 0,6 m/s² ; Z1b = 0,8 m/s² ; Z2 = 1,0 m/s² ;
    Z3a = 1,3 m/s² ; Z3b = 1,6 m/s².
    L'Annexe F (carte des zones) n'est pas une table par commune mais une
    carte à isolignes (https://map.geo.admin.ch, comme l'Annexe D pour la
    neige et l'Annexe E pour le vent) — la zone est donc une saisie directe.

Classes de terrain de fondation — SIA 261 Tableau 24 (§16.2.2) : paramètres
S, TB, TC, TD du spectre (classe F exclue — étude de site spectrale requise).

Spectre de réponse élastique — SIA 261 §16.2.3, éq. (26)-(29) : Se(T) =
agd·S·[...] (même forme que ci-dessus, avec agd zone-only, SANS γf).

Spectre de dimensionnement — SIA 261 §16.2.4, éq. (31)-(34) : Sd(T) =
agd·γf·S·[...] — γf (facteur d'importance, Tableau 25) appliqué séparément
ICI, contrairement à la France (voir point important ci-dessus).

    ⚠ Les éq. (26)-(35) et le Tableau 24 sont rendus par des images/tracés
    vectoriels dans le PDF source (OCR indisponible pour les fractions et
    exposants) ; la reconstruction suit la forme normalisée du spectre EC8
    (adoptée telle quelle par la SIA 261), avec pour le Tableau 24 :
    TC(classe A) et TC(classe E) reconstruits à 0,25 s après suppression
    d'un artefact d'OCR identique sur ces deux cellules (chiffre "1"
    parasite : "10,25" → "0,25", cohérent avec les valeurs physiquement
    attendues pour des sols raides). À confirmer contre le document source
    avant tout usage en production.
"""

__all__ = [
    'CH_ZONES', 'CH_SOIL_CLASSES', 'CH_IMPORTANCE_FACTORS',
    'FR_ZONES', 'FR_SOIL_CLASSES', 'FR_IMPORTANCE_FACTORS',
    'eta_damping', 'BETA_FLOOR',
    'ElasticResponseSpectrumCH', 'DesignResponseSpectrumCH', 'ground_displacement_CH',
    'ElasticResponseSpectrumFR', 'DesignResponseSpectrumFR',
]

import math
from typing import Dict, List, Tuple

from core.formula import FormulaResult, FormulaCollection

#: β — plancher du spectre de dimensionnement (valeur recommandée EC8,
#: confirmée retenue pour la France ; utilisée aussi pour la Suisse).
BETA_FLOOR = 0.2


def eta_damping(xi_percent: float = 5.0) -> float:
    """η — coefficient de correction d'amortissement.
    η = max(√(10/(5+ξ)) ; 0,55) ; η = 1 pour ξ = 5%."""
    return round(max(math.sqrt(10.0 / (5.0 + xi_percent)), 0.55), 5)


def _elastic_se(T: float, ag: float, S: float, TB: float, TC: float, TD: float, eta: float) -> float:
    """Se(T) [m/s²] — forme normalisée EC8 (4 branches)."""
    if T < 0:
        raise ValueError("T doit être ≥ 0.")
    if T < TB:
        return round(ag * S * (1 + (T / TB) * (2.5 * eta - 1)), 5)
    if T <= TC:
        return round(ag * S * 2.5 * eta, 5)
    if T <= TD:
        return round(ag * S * 2.5 * eta * (TC / T), 5)
    return round(ag * S * 2.5 * eta * (TC * TD / T ** 2), 5)


def _design_sd(T: float, ag: float, S: float, TB: float, TC: float, TD: float, q: float, beta: float = BETA_FLOOR) -> float:
    """Sd(T) [m/s²] — forme normalisée EC8 (4 branches, plancher β·ag)."""
    if T < 0:
        raise ValueError("T doit être ≥ 0.")
    floor = beta * ag
    if T < TB:
        raw = ag * S * (2 / 3 + (T / TB) * (2.5 / q - 2 / 3))
    elif T <= TC:
        raw = ag * S * 2.5 / q
    elif T <= TD:
        raw = ag * S * (2.5 / q) * (TC / T)
    else:
        raw = ag * S * (2.5 / q) * (TC * TD / T ** 2)
    return round(max(raw, floor), 5)


# ---------------------------------------------------------------------------
# Suisse — SIA 261:2020, chapitre 16
# ---------------------------------------------------------------------------

#: agd [m/s²] par zone sismique — SIA 261 §16.2.1.
CH_ZONES: Dict[str, float] = {
    "Z1a": 0.6, "Z1b": 0.8, "Z2": 1.0, "Z3a": 1.3, "Z3b": 1.6,
}

#: {classe: (S, TB, TC, TD)} — SIA 261 Tableau 24. Classe F exclue (étude de
#: site spectrale requise, §16.2.2.2).
CH_SOIL_CLASSES: Dict[str, Tuple[float, float, float, float]] = {
    "A": (1.00, 0.07, 0.25, 2.0),
    "B": (1.20, 0.08, 0.35, 2.0),
    "C": (1.45, 0.10, 0.40, 2.0),
    "D": (1.70, 0.10, 0.50, 2.0),
    "E": (1.70, 0.09, 0.25, 2.0),
}

#: γf par classe d'ouvrage (sécurité structurale) — SIA 261 Tableau 25.
CH_IMPORTANCE_FACTORS: Dict[str, float] = {
    "I": 1.5, "II": 1.2, "III": 1.0,
}


class ElasticResponseSpectrumCH:
    """
    Spectre de réponse élastique Se(T) — Suisse (SIA 261 §16.2.3).

    :param zone: Zone sismique ('Z1a'..'Z3b' — voir Annexe F, carte).
    :param soil_class: Classe de terrain de fondation ('A'..'E' — Tableau 24).
    :param xi_percent: Amortissement visqueux ξ [%] (5,0 par défaut).
    """

    def __init__(self, zone: str, soil_class: str, xi_percent: float = 5.0) -> None:
        zone = zone.strip()
        soil_class = soil_class.upper().strip()
        if zone not in CH_ZONES:
            raise ValueError(f"Zone '{zone}' inconnue. Valeurs : {list(CH_ZONES.keys())}")
        if soil_class not in CH_SOIL_CLASSES:
            raise ValueError(
                f"Classe de terrain '{soil_class}' invalide ou non couverte (classe F : "
                f"étude de site spectrale requise, hors périmètre). "
                f"Valeurs : {list(CH_SOIL_CLASSES.keys())}"
            )
        self.__zone = zone
        self.__soil_class = soil_class
        self.__xi = xi_percent
        self.__S, self.__TB, self.__TC, self.__TD = CH_SOIL_CLASSES[soil_class]

    @property
    def zone(self) -> str:
        return self.__zone

    @property
    def soil_class(self) -> str:
        return self.__soil_class

    @property
    def agd(self) -> float:
        return CH_ZONES[self.__zone]

    @property
    def S(self) -> float:
        return self.__S

    @property
    def TB(self) -> float:
        return self.__TB

    @property
    def TC(self) -> float:
        return self.__TC

    @property
    def TD(self) -> float:
        return self.__TD

    @property
    def eta(self) -> float:
        return eta_damping(self.__xi)

    def Se(self, T: float) -> float:
        """Se(T) [m/s²] — éq. (26)-(29)."""
        return _elastic_se(T, self.agd, self.__S, self.__TB, self.__TC, self.__TD, self.eta)

    def curve(self, n_points: int = 60, T_max: float = 4.0) -> List[Tuple[float, float]]:
        """Liste de points (T, Se(T)) pour tracer la courbe."""
        if n_points < 2:
            raise ValueError("n_points doit être ≥ 2.")
        step = T_max / (n_points - 1)
        return [(round(i * step, 4), self.Se(i * step)) for i in range(n_points)]

    def get_Se_max(self, with_values: bool = False) -> FormulaResult:
        se_max = self.Se(self.__TB)
        fv = f"Se,max = agd·S·2,5·η = {self.agd:.2f}×{self.__S:.2f}×2,5×{self.eta:.3f} = {se_max:.4f} m/s²" if with_values else ""
        return FormulaResult(
            name="Se,max (plateau)",
            formula="Se = agd·S·2,5·η (TB ≤ T ≤ TC)",
            formula_values=fv,
            result=se_max,
            unit="m/s²",
            ref="SIA 261:2020 — §16.2.3, éq. (27) [à confirmer]",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Spectre de réponse élastique — {self.__zone}, terrain {self.__soil_class}",
            ref="SIA 261:2020 — §16.2.3",
        )
        fc.add(self.get_Se_max(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"ElasticResponseSpectrumCH(zone='{self.__zone}', soil_class='{self.__soil_class}', "
            f"agd={self.agd:.2f}m/s², Se_max={self.Se(self.__TB):.3f}m/s²)"
        )


class DesignResponseSpectrumCH:
    """
    Spectre de dimensionnement Sd(T) — Suisse (SIA 261 §16.2.4).

    :param zone: Zone sismique ('Z1a'..'Z3b').
    :param soil_class: Classe de terrain de fondation ('A'..'E').
    :param q: Coefficient de comportement (SIA 262 à SIA 267 selon matériau).
    :param importance_class: Classe d'ouvrage ('I', 'II', 'III' — Tableau 25).
    """

    def __init__(
        self,
        zone: str,
        soil_class: str,
        q: float = 1.5,
        importance_class: str = "III",
    ) -> None:
        importance_class = importance_class.upper().strip()
        if importance_class not in CH_IMPORTANCE_FACTORS:
            raise ValueError(
                f"Classe d'ouvrage '{importance_class}' invalide. "
                f"Valeurs : {list(CH_IMPORTANCE_FACTORS.keys())}"
            )
        if q <= 0:
            raise ValueError("q (coefficient de comportement) doit être > 0.")
        self.__elastic = ElasticResponseSpectrumCH(zone=zone, soil_class=soil_class, xi_percent=5.0)
        self.__q = q
        self.__importance_class = importance_class

    @property
    def elastic(self) -> ElasticResponseSpectrumCH:
        return self.__elastic

    @property
    def q(self) -> float:
        return self.__q

    @property
    def importance_class(self) -> str:
        return self.__importance_class

    @property
    def gamma_f(self) -> float:
        return CH_IMPORTANCE_FACTORS[self.__importance_class]

    @property
    def agd(self) -> float:
        return self.__elastic.agd

    def Sd(self, T: float) -> float:
        """Sd(T) [m/s²] — éq. (31)-(34), avec plancher β·agd·γf (γf appliqué
        ici, contrairement à la France où γI est déjà incorporé dans ag)."""
        e = self.__elastic
        return _design_sd(T, e.agd * self.gamma_f, e.S, e.TB, e.TC, e.TD, self.__q)

    def curve(self, n_points: int = 60, T_max: float = 4.0) -> List[Tuple[float, float]]:
        """Liste de points (T, Sd(T)) pour tracer la courbe."""
        if n_points < 2:
            raise ValueError("n_points doit être ≥ 2.")
        step = T_max / (n_points - 1)
        return [(round(i * step, 4), self.Sd(i * step)) for i in range(n_points)]

    def get_Sd_max(self, with_values: bool = False) -> FormulaResult:
        e = self.__elastic
        sd_max = self.Sd(e.TB)
        fv = ""
        if with_values:
            fv = (
                f"Sd,max = agd·γf·S·2,5/q = {e.agd:.2f}×{self.gamma_f:.2f}×{e.S:.2f}×2,5/{self.__q:.2f} "
                f"= {sd_max:.4f} m/s²"
            )
        return FormulaResult(
            name="Sd,max (plateau)",
            formula="Sd = agd·γf·S·2,5/q (TB ≤ T ≤ TC)",
            formula_values=fv,
            result=sd_max,
            unit="m/s²",
            ref="SIA 261:2020 — §16.2.4, éq. (32) [à confirmer]",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        e = self.__elastic
        fc = FormulaCollection(
            title=f"Spectre de dimensionnement — {e.zone}, terrain {e.soil_class}, q={self.__q}",
            ref="SIA 261:2020 — §16.2.4",
        )
        fc.add(self.get_Sd_max(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        e = self.__elastic
        return (
            f"DesignResponseSpectrumCH(zone='{e.zone}', soil_class='{e.soil_class}', q={self.__q}, "
            f"importance_class='{self.__importance_class}', Sd_max={self.Sd(e.TB):.3f}m/s²)"
        )


def ground_displacement_CH(zone: str, soil_class: str, importance_class: str = "III") -> float:
    """Valeur de dimensionnement du déplacement du sol ugd [m] — éq. (35) :
    ugd = 0,05·γf·agd·S·TC·TD [à confirmer]."""
    e = ElasticResponseSpectrumCH(zone=zone, soil_class=soil_class)
    gf = CH_IMPORTANCE_FACTORS[importance_class.upper().strip()]
    return round(0.05 * gf * e.agd * e.S * e.TC * e.TD, 5)


# ---------------------------------------------------------------------------
# France — NF EN 1998-1:2005 + NF EN 1998-1/NA
# ---------------------------------------------------------------------------

#: agR [m/s²] par zone de sismicité (1 à 5) — arrêté du 22/10/2010 modifié.
#: ⚠ Non lu dans un document source de cette session — voir avertissement
#: en tête de module.
FR_ZONES: Dict[str, float] = {
    "1": 0.4, "2": 0.7, "3": 1.1, "4": 1.6, "5": 3.0,
}

#: {classe: (S, TB, TC, TD)} — NF EN 1998-1, Tableau 3.3 (spectre de type 2,
#: retenu pour la France — voir avertissement en tête de module). Classes
#: spéciales S1/S2 exclues (étude particulière requise, §3.1.2(4)P).
FR_SOIL_CLASSES: Dict[str, Tuple[float, float, float, float]] = {
    "A": (1.00, 0.05, 0.25, 1.2),
    "B": (1.35, 0.05, 0.25, 1.2),
    "C": (1.50, 0.10, 0.25, 1.2),
    "D": (1.80, 0.10, 0.30, 1.2),
    "E": (1.60, 0.05, 0.25, 1.2),
}

#: γI par catégorie d'importance (bâtiments à risque normal, I à IV).
#: ⚠ Non lu dans un document source de cette session — voir avertissement
#: en tête de module.
FR_IMPORTANCE_FACTORS: Dict[str, float] = {
    "I": 0.8, "II": 1.0, "III": 1.2, "IV": 1.4,
}


class ElasticResponseSpectrumFR:
    """
    Spectre de réponse élastique Se(T) — France (NF EN 1998-1 §3.2.2.2).

    :param zone: Zone de sismicité ('1' à '5' — zonage réglementaire).
    :param soil_class: Classe de sol ('A' à 'E' — Tableau 3.1).
    :param importance_class: Catégorie d'importance ('I' à 'IV') — γI est
        incorporé dans ag = γI·agR (contrairement à la Suisse).
    :param xi_percent: Amortissement visqueux ξ [%] (5,0 par défaut).
    """

    def __init__(
        self,
        zone: str,
        soil_class: str,
        importance_class: str = "II",
        xi_percent: float = 5.0,
    ) -> None:
        zone = zone.strip()
        soil_class = soil_class.upper().strip()
        importance_class = importance_class.upper().strip()
        if zone not in FR_ZONES:
            raise ValueError(f"Zone '{zone}' inconnue. Valeurs : {list(FR_ZONES.keys())}")
        if soil_class not in FR_SOIL_CLASSES:
            raise ValueError(
                f"Classe de sol '{soil_class}' invalide ou non couverte (classes S1/S2 : "
                f"étude particulière requise, hors périmètre). "
                f"Valeurs : {list(FR_SOIL_CLASSES.keys())}"
            )
        if importance_class not in FR_IMPORTANCE_FACTORS:
            raise ValueError(
                f"Catégorie d'importance '{importance_class}' invalide. "
                f"Valeurs : {list(FR_IMPORTANCE_FACTORS.keys())}"
            )
        self.__zone = zone
        self.__soil_class = soil_class
        self.__importance_class = importance_class
        self.__xi = xi_percent
        self.__S, self.__TB, self.__TC, self.__TD = FR_SOIL_CLASSES[soil_class]

    @property
    def zone(self) -> str:
        return self.__zone

    @property
    def soil_class(self) -> str:
        return self.__soil_class

    @property
    def importance_class(self) -> str:
        return self.__importance_class

    @property
    def agR(self) -> float:
        return FR_ZONES[self.__zone]

    @property
    def gamma_I(self) -> float:
        return FR_IMPORTANCE_FACTORS[self.__importance_class]

    @property
    def ag(self) -> float:
        """ag = γI·agR — accélération de calcul pour un sol de classe A."""
        return round(self.gamma_I * self.agR, 5)

    @property
    def S(self) -> float:
        return self.__S

    @property
    def TB(self) -> float:
        return self.__TB

    @property
    def TC(self) -> float:
        return self.__TC

    @property
    def TD(self) -> float:
        return self.__TD

    @property
    def eta(self) -> float:
        return eta_damping(self.__xi)

    def Se(self, T: float) -> float:
        """Se(T) [m/s²] — éq. (3.2)-(3.5)."""
        return _elastic_se(T, self.ag, self.__S, self.__TB, self.__TC, self.__TD, self.eta)

    def curve(self, n_points: int = 60, T_max: float = 4.0) -> List[Tuple[float, float]]:
        if n_points < 2:
            raise ValueError("n_points doit être ≥ 2.")
        step = T_max / (n_points - 1)
        return [(round(i * step, 4), self.Se(i * step)) for i in range(n_points)]

    def get_Se_max(self, with_values: bool = False) -> FormulaResult:
        se_max = self.Se(self.__TB)
        fv = ""
        if with_values:
            fv = (
                f"Se,max = ag·S·2,5·η = ({self.gamma_I:.2f}×{self.agR:.2f})×{self.__S:.2f}×2,5×{self.eta:.3f} "
                f"= {se_max:.4f} m/s²"
            )
        return FormulaResult(
            name="Se,max (plateau)",
            formula="Se = ag·S·2,5·η (TB ≤ T ≤ TC)",
            formula_values=fv,
            result=se_max,
            unit="m/s²",
            ref="NF EN 1998-1 — §3.2.2.2, éq. (3.3) [agR/γI à confirmer]",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Spectre de réponse élastique — zone {self.__zone}, sol {self.__soil_class}",
            ref="NF EN 1998-1 — §3.2.2.2",
        )
        fc.add(self.get_Se_max(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"ElasticResponseSpectrumFR(zone='{self.__zone}', soil_class='{self.__soil_class}', "
            f"ag={self.ag:.3f}m/s², Se_max={self.Se(self.__TB):.3f}m/s²)"
        )


class DesignResponseSpectrumFR:
    """
    Spectre de dimensionnement Sd(T) — France (NF EN 1998-1 §3.2.2.5).

    :param zone: Zone de sismicité ('1' à '5').
    :param soil_class: Classe de sol ('A' à 'E').
    :param q: Coefficient de comportement (parties 5 à 9 de l'EN 1998 selon
        matériau).
    :param importance_class: Catégorie d'importance ('I' à 'IV').
    """

    def __init__(
        self,
        zone: str,
        soil_class: str,
        q: float = 1.5,
        importance_class: str = "II",
    ) -> None:
        if q <= 0:
            raise ValueError("q (coefficient de comportement) doit être > 0.")
        self.__elastic = ElasticResponseSpectrumFR(
            zone=zone, soil_class=soil_class, importance_class=importance_class, xi_percent=5.0,
        )
        self.__q = q

    @property
    def elastic(self) -> ElasticResponseSpectrumFR:
        return self.__elastic

    @property
    def q(self) -> float:
        return self.__q

    @property
    def importance_class(self) -> str:
        return self.__elastic.importance_class

    def Sd(self, T: float) -> float:
        """Sd(T) [m/s²] — éq. (3.13)-(3.16), plancher β·ag (γI déjà dans ag)."""
        e = self.__elastic
        return _design_sd(T, e.ag, e.S, e.TB, e.TC, e.TD, self.__q)

    def curve(self, n_points: int = 60, T_max: float = 4.0) -> List[Tuple[float, float]]:
        if n_points < 2:
            raise ValueError("n_points doit être ≥ 2.")
        step = T_max / (n_points - 1)
        return [(round(i * step, 4), self.Sd(i * step)) for i in range(n_points)]

    def get_Sd_max(self, with_values: bool = False) -> FormulaResult:
        e = self.__elastic
        sd_max = self.Sd(e.TB)
        fv = ""
        if with_values:
            fv = f"Sd,max = ag·S·2,5/q = {e.ag:.3f}×{e.S:.2f}×2,5/{self.__q:.2f} = {sd_max:.4f} m/s²"
        return FormulaResult(
            name="Sd,max (plateau)",
            formula="Sd = ag·S·2,5/q (TB ≤ T ≤ TC)",
            formula_values=fv,
            result=sd_max,
            unit="m/s²",
            ref="NF EN 1998-1 — §3.2.2.5, éq. (3.14) [agR/γI à confirmer]",
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        e = self.__elastic
        fc = FormulaCollection(
            title=f"Spectre de dimensionnement — zone {e.zone}, sol {e.soil_class}, q={self.__q}",
            ref="NF EN 1998-1 — §3.2.2.5",
        )
        fc.add(self.get_Sd_max(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        e = self.__elastic
        return (
            f"DesignResponseSpectrumFR(zone='{e.zone}', soil_class='{e.soil_class}', q={self.__q}, "
            f"importance_class='{e.importance_class}', Sd_max={self.Sd(e.TB):.3f}m/s²)"
        )


# ===========================================================================
# Debug / exemple
# ===========================================================================
if __name__ == "__main__":
    print("=== Suisse ===")
    se = ElasticResponseSpectrumCH(zone="Z3a", soil_class="C")
    print(f"{se!r}")
    sd = DesignResponseSpectrumCH(zone="Z3a", soil_class="C", q=1.5, importance_class="II")
    print(f"{sd!r}")

    print("\n=== France ===")
    se_fr = ElasticResponseSpectrumFR(zone="4", soil_class="C", importance_class="II")
    print(f"{se_fr!r}")
    sd_fr = DesignResponseSpectrumFR(zone="4", soil_class="C", q=1.5, importance_class="II")
    print(f"{sd_fr!r}")

    print("\nCourbe Sd(T) France, zone 4, sol C (6 premiers points) :")
    for T, val in sd_fr.curve(n_points=6, T_max=2.0):
        print(f"  T={T:.2f}s -> Sd={val:.4f} m/s²")
