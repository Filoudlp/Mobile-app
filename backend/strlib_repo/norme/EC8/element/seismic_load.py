#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe orchestratrice pour la détermination du spectre de réponse sismique
— France (NF EN 1998-1 + NF EN 1998-1/NA) et Suisse (SIA 261:2020,
chapitre 16).

SeismicLoad ne contient aucune logique de calcul propre : elle délègue tout
aux classes indépendantes de ``norme.EC8.seisme.*`` (composition — même
principe que ``norme.EC1.element.snow_load.SnowLoad`` /
``norme.EC1.element.wind_load.WindLoad``).

⚠ Zones sismiques françaises (agR) et catégories d'importance (γI) :
reconstruites depuis la connaissance générale de l'arrêté du 22/10/2010,
non lues dans un document source de cette session — voir l'avertissement
en tête de ``norme.EC8.seisme.response_spectrum``.
"""

__all__ = ['SeismicLoad']

from typing import Dict, List, Optional, Tuple
from core.formula import FormulaCollection

from norme.EC8.seisme.response_spectrum import (
    ElasticResponseSpectrumCH,
    DesignResponseSpectrumCH,
    ground_displacement_CH,
    ElasticResponseSpectrumFR,
    DesignResponseSpectrumFR,
)


class SeismicLoad:
    """
    Orchestrateur de détermination du spectre de réponse sismique.

    Parameters
    ----------
    country : str
        ``"FR"`` ou ``"CH"``.
    zone : str
        Zone sismique. France — ``"1"``..``"5"`` (zonage réglementaire) ;
        Suisse — ``"Z1a"``..``"Z3b"`` (Annexe F, carte).
    soil_class : str
        Classe de sol/terrain. France — ``"A"``..``"E"`` (Tableau 3.1) ;
        Suisse — ``"A"``..``"E"`` (Tableau 24 ; classe F hors périmètre).
    q : float
        Coefficient de comportement (1,5 par défaut — comportement peu
        ductile ; à fixer selon les parties matériau de l'EN 1998 / SIA 262
        à SIA 267).
    importance_class : str
        Catégorie d'importance / classe d'ouvrage. France — ``"I"``..``"IV"``
        (γI = 0,8/1,0/1,2/1,4) ; Suisse — ``"I"``..``"III"`` (γf =
        1,5/1,2/1,0). 'II' par défaut en France (bâtiments courants), 'III'
        par défaut en Suisse (numérotation inversée entre les deux pays —
        voir les tables de chaque module).
    xi_percent : float
        Amortissement visqueux ξ [%] (5,0 par défaut).
    """

    def __init__(
        self,
        country: str,
        zone: str,
        soil_class: str,
        q: float = 1.5,
        importance_class: Optional[str] = None,
        xi_percent: float = 5.0,
    ) -> None:
        country = country.upper().strip()
        if country not in ("FR", "CH"):
            raise ValueError(f"country doit être 'FR' ou 'CH' (reçu : '{country}')")

        self.__country = country
        if country == "FR":
            ic = importance_class or "II"
            self.__elastic = ElasticResponseSpectrumFR(
                zone=zone, soil_class=soil_class, importance_class=ic, xi_percent=xi_percent,
            )
            self.__design = DesignResponseSpectrumFR(
                zone=zone, soil_class=soil_class, q=q, importance_class=ic,
            )
        else:
            ic = importance_class or "III"
            self.__elastic = ElasticResponseSpectrumCH(zone=zone, soil_class=soil_class, xi_percent=xi_percent)
            self.__design = DesignResponseSpectrumCH(
                zone=zone, soil_class=soil_class, q=q, importance_class=ic,
            )

    @property
    def country(self) -> str:
        return self.__country

    @property
    def elastic(self):
        """Instance ElasticResponseSpectrumFR / ElasticResponseSpectrumCH."""
        return self.__elastic

    @property
    def design(self):
        """Instance DesignResponseSpectrumFR / DesignResponseSpectrumCH."""
        return self.__design

    @property
    def ugd(self) -> Optional[float]:
        """Déplacement de dimensionnement du sol [m] — Suisse uniquement
        (éq. 35 ; pas d'équivalent vérifié pour la France dans cette
        implémentation)."""
        if self.__country != "CH":
            return None
        return ground_displacement_CH(
            zone=self.__elastic.zone,
            soil_class=self.__elastic.soil_class,
            importance_class=self.__design.importance_class,
        )

    def spectrum_points(self, kind: str = "design", n: int = 60, T_max: float = 4.0) -> List[Tuple[float, float]]:
        """Points (T, S) de la courbe demandée ('design' ou 'elastic')."""
        if kind == "design":
            return self.__design.curve(n_points=n, T_max=T_max)
        if kind == "elastic":
            return self.__elastic.curve(n_points=n, T_max=T_max)
        raise ValueError("kind doit être 'design' ou 'elastic'.")

    def point_at(self, T: float) -> Dict[str, float]:
        """Valeurs Se(T) et Sd(T) pour une période T donnée — permet de lire
        la position exacte sur la courbe pour un point (ex. période propre
        de la structure)."""
        return {"T": T, "Se": self.__elastic.Se(T), "Sd": self.__design.Sd(T)}

    def full_check(self, with_values: bool = False) -> FormulaCollection:
        norme = "NF EN 1998-1" if self.__country == "FR" else "SIA 261:2020"
        fc = FormulaCollection(
            title=f"Spectre de réponse sismique — {self.__country}",
            ref=norme,
        )
        for r in self.__elastic.report(with_values=with_values):
            fc.add(r)
        for r in self.__design.report(with_values=with_values):
            fc.add(r)
        return fc

    def summary(self) -> dict:
        e, d = self.__elastic, self.__design
        base = {
            "S": e.S,
            "TB": e.TB,
            "TC": e.TC,
            "TD": e.TD,
            "eta": e.eta,
            "q": d.q,
            "Se_max": e.Se(e.TB),
            "Sd_max": d.Sd(e.TB),
        }
        if self.__country == "FR":
            base.update({
                "agR": e.agR,
                "gamma_I": e.gamma_I,
                "ag": e.ag,
                "importance_class": e.importance_class,
            })
        else:
            base.update({
                "agd": e.agd,
                "gamma_f": d.gamma_f,
                "importance_class": d.importance_class,
                "ugd": self.ugd,
            })
        return base

    def __repr__(self) -> str:
        e = self.__elastic
        return f"SeismicLoad(country='{self.__country}', zone='{e.zone}', soil_class='{e.soil_class}')"


# ======================================================================
#  Debug / exemple d'utilisation
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 60

    print(f"\n{sep}")
    print("  CAS 1 : Suisse, Z3a, terrain C, q=1.5, classe d'ouvrage II")
    print(sep)
    seisme_ch = SeismicLoad(country="CH", zone="Z3a", soil_class="C", q=1.5, importance_class="II")
    print(f"  {repr(seisme_ch)}")
    s = seisme_ch.summary()
    print(f"  agd={s['agd']:.2f} S={s['S']:.2f} TB={s['TB']:.2f} TC={s['TC']:.2f} TD={s['TD']:.2f}")
    print(f"  Se,max={s['Se_max']:.3f} m/s² | Sd,max={s['Sd_max']:.3f} m/s² | ugd={s['ugd']:.4f} m")

    print(f"\n{sep}")
    print("  CAS 2 : France, zone 4, sol C, q=1.5, catégorie II")
    print(sep)
    seisme_fr = SeismicLoad(country="FR", zone="4", soil_class="C", q=1.5, importance_class="II")
    print(f"  {repr(seisme_fr)}")
    s = seisme_fr.summary()
    print(f"  agR={s['agR']:.2f} gamma_I={s['gamma_I']:.2f} ag={s['ag']:.3f} S={s['S']:.2f}")
    print(f"  Se,max={s['Se_max']:.3f} m/s² | Sd,max={s['Sd_max']:.3f} m/s²")

    print(f"\n{sep}")
    print("  CAS 3 : point_at(T=0.6s), France")
    print(sep)
    print(f"  {seisme_fr.point_at(0.6)}")

    print(f"\n{sep}")
    print("  CAS 4 : Full check (rapport détaillé, France)")
    print(sep)
    print(seisme_fr.full_check(with_values=True))

    print(f"\n{'=' * 60}")
    print("  FIN DES TESTS")
    print(f"{'=' * 60}")
