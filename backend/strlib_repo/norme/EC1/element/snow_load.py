#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe orchestratrice pour la détermination de la charge de neige sur
toiture — France (NF EN 1991-1-3/NA) et Suisse (SIA 261:2020).

SnowLoad ne contient aucune logique de calcul : elle délègue tout aux
classes indépendantes de ``norme.EC1.neige.*`` (approche composition —
même principe que ``norme.EC3.element.steel_column.SteelColumn``).

Contrairement au poteau acier, il n'y a pas de "Sec_mat" ici : la charge de
neige est une action (pas une vérification de résistance), et les entrées
(zone/altitude, ou h/h0) sont directement les paramètres du site — il n'y a
pas d'objet catalogue à réutiliser entre plusieurs vérifications comme un
profilé acier.
"""

__all__ = ['SnowLoad']

from typing import Optional
from core.formula import FormulaCollection

from norme.EC1.neige.ground_snow_load import GroundSnowLoadFR, GroundSnowLoadCH
from norme.EC1.neige.shape_coefficient import RoofShapeCoefficient
from norme.EC1.neige.roof_snow_load import RoofSnowLoad, CE_TABLE_FR, CE_TABLE_CH


class SnowLoad:
    """
    Orchestrateur de détermination de la charge de neige sur toiture.

    Parameters
    ----------
    country : str
        ``"FR"`` ou ``"CH"``.
    angle : float
        Angle de la toiture par rapport à l'horizontale [°] (toiture à un
        ou deux versants — voir ``RoofShapeCoefficient``).
    exposure : str
        Clé de la table Ce du pays concerné :
        France — ``"normal"`` ou ``"abrite"`` ;
        Suisse — ``"expose"``, ``"normal"`` ou ``"abrite"``.
    Ct : float
        Coefficient thermique (1,0 par défaut).
    zone : str, optional
        Zone de neige française (``"A1"``…``"E"``) — requis si ``country="FR"``.
    altitude : float, optional
        Altitude du site [m] — requis dans les deux pays
        (France : altitude au sens NA ; Suisse : h, altitude du site).
    h0 : float, optional
        Altitude de référence [m] (Suisse — SIA 261, Annexe D) — requis si
        ``country="CH"``.
    """

    def __init__(
        self,
        country: str,
        angle: float,
        exposure: str = "normal",
        Ct: float = 1.0,
        zone: Optional[str] = None,
        altitude: Optional[float] = None,
        h0: Optional[float] = None,
    ) -> None:
        country = country.upper().strip()
        if country not in ("FR", "CH"):
            raise ValueError(f"country doit être 'FR' ou 'CH' (reçu : '{country}')")

        self.__country = country
        self.__angle = angle
        self.__exposure = exposure
        self.__Ct = Ct
        self.__zone = zone
        self.__altitude = altitude
        self.__h0 = h0

        if country == "FR":
            if zone is None or altitude is None:
                raise ValueError("France : 'zone' et 'altitude' sont requis.")
            self.__ground = GroundSnowLoadFR(zone=zone, altitude=altitude)
            if exposure not in CE_TABLE_FR:
                raise ValueError(
                    f"exposure '{exposure}' invalide pour la France. "
                    f"Valeurs : {list(CE_TABLE_FR.keys())}"
                )
            self.__Ce = CE_TABLE_FR[exposure]
        else:
            if altitude is None or h0 is None:
                raise ValueError("Suisse : 'altitude' (h) et 'h0' sont requis.")
            self.__ground = GroundSnowLoadCH(h=altitude, h0=h0)
            if exposure not in CE_TABLE_CH:
                raise ValueError(
                    f"exposure '{exposure}' invalide pour la Suisse. "
                    f"Valeurs : {list(CE_TABLE_CH.keys())}"
                )
            self.__Ce = CE_TABLE_CH[exposure]

        self.__shape = RoofShapeCoefficient(angle=angle)

    # ------------------------------------------------------------------
    #  Propriétés
    # ------------------------------------------------------------------
    @property
    def country(self) -> str:
        return self.__country

    @property
    def ground(self):
        """Instance GroundSnowLoadFR / GroundSnowLoadCH sous-jacente."""
        return self.__ground

    @property
    def shape(self) -> RoofShapeCoefficient:
        """Instance RoofShapeCoefficient sous-jacente."""
        return self.__shape

    @property
    def Ce(self) -> float:
        """Coefficient d'exposition retenu (table du pays concerné)."""
        return self.__Ce

    @property
    def Ct(self) -> float:
        """Coefficient thermique."""
        return self.__Ct

    @property
    def sk(self) -> float:
        return self.__ground.sk

    # ------------------------------------------------------------------
    #  Cas de charge
    # ------------------------------------------------------------------
    def _combine(self, mu: Optional[float], sk: float) -> Optional[RoofSnowLoad]:
        if mu is None:
            return None
        return RoofSnowLoad(mu=mu, sk=sk, Ce=self.__Ce, Ct=self.__Ct)

    def check_sans_accumulation(self, with_values: bool = False) -> FormulaCollection:
        """s = μ1 · Ce · Ct · sk — EN 1991-1-3 éq. (5.1), cas durable/transitoire."""
        combo = self._combine(self.__shape.mu1, self.sk)
        return combo.report(with_values=with_values)

    def check_avec_accumulation(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """s = μ2 · Ce · Ct · sk — EN 1991-1-3 éq. (5.1). None si α ≥ 60°
        (μ2 non applicable)."""
        combo = self._combine(self.__shape.mu2, self.sk)
        if combo is None:
            return None
        return combo.report(with_values=with_values)

    def check_exceptionnelle(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        s = μ1 · Ce · Ct · sAd — EN 1991-1-3 éq. (5.2), situation accidentelle.
        France uniquement (le NA suisse ne définit pas de charge exceptionnelle
        de ce type). None si la zone française ne définit pas de sAd.
        """
        if self.__country != "FR":
            return None
        sAd = self.__ground.sAd
        if sAd is None:
            return None
        combo = self._combine(self.__shape.mu1, sAd)
        return combo.report(with_values=with_values)

    # ------------------------------------------------------------------
    #  Rapport complet
    # ------------------------------------------------------------------
    def full_check(self, with_values: bool = False) -> FormulaCollection:
        """Rapport complet : charge au sol + coefficients de forme + tous
        les cas de charge sur toiture applicables."""
        fc = FormulaCollection(
            title=f"Charge de neige sur toiture — {self.__country}",
            ref="EN 1991-1-3 / SIA 261",
        )
        for r in self.__ground.report(with_values=with_values):
            fc.add(r)
        for r in self.__shape.report(with_values=with_values):
            fc.add(r)

        sans = self.check_sans_accumulation(with_values=with_values)
        for r in sans:
            fc.add(r)

        avec = self.check_avec_accumulation(with_values=with_values)
        if avec is not None:
            for r in avec:
                fc.add(r)

        excep = self.check_exceptionnelle(with_values=with_values)
        if excep is not None:
            for r in excep:
                fc.add(r)

        return fc

    def summary(self) -> dict:
        """
        Retourne la charge de neige de calcul retenue (max des cas de
        charge applicables) — c'est la valeur à utiliser pour le
        dimensionnement de la toiture.
        """
        candidates = [self.check_sans_accumulation(with_values=False).get("s").result]
        avec = self.check_avec_accumulation(with_values=False)
        if avec is not None:
            candidates.append(avec.get("s").result)
        excep = self.check_exceptionnelle(with_values=False)
        if excep is not None:
            candidates.append(excep.get("s").result)
        return {
            "sk": self.sk,
            "mu1": self.__shape.mu1,
            "mu2": self.__shape.mu2,
            "s_design": max(candidates),
        }

    def __repr__(self) -> str:
        loc = (
            f"zone={self.__zone}, altitude={self.__altitude:.0f}m"
            if self.__country == "FR"
            else f"h={self.__altitude:.0f}m, h0={self.__h0:.0f}m"
        )
        return f"SnowLoad(country='{self.__country}', {loc}, angle={self.__angle:.1f}°)"


# ======================================================================
#  Debug / exemple d'utilisation
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 60

    print(f"\n{sep}")
    print("  CAS 1 : France, zone C2, 800 m, toiture 25°")
    print(sep)
    snow_fr = SnowLoad(country="FR", zone="C2", altitude=800, angle=25, exposure="normal")
    print(f"  {repr(snow_fr)}")
    s = snow_fr.summary()
    print(f"  sk = {s['sk']:.2f} kN/m² | μ1 = {s['mu1']:.3f} | μ2 = {s['mu2']} "
          f"| s de calcul = {s['s_design']:.3f} kN/m²")

    print(f"\n{sep}")
    print("  CAS 2 : Suisse, h=1200m, h0=900m, toiture 10°, site exposé")
    print(sep)
    snow_ch = SnowLoad(country="CH", altitude=1200, h0=900, angle=10, exposure="expose")
    print(f"  {repr(snow_ch)}")
    s = snow_ch.summary()
    print(f"  sk = {s['sk']:.2f} kN/m² | μ1 = {s['mu1']:.3f} | μ2 = {s['mu2']} "
          f"| s de calcul = {s['s_design']:.3f} kN/m²")

    print(f"\n{sep}")
    print("  CAS 3 : Full check (rapport détaillé, France)")
    print(sep)
    print(snow_fr.full_check(with_values=True))

    print(f"\n{'=' * 60}")
    print("  FIN DES TESTS")
    print(f"{'=' * 60}")
