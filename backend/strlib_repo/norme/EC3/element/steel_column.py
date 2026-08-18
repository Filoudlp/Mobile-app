#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe orchestratrice pour la vérification complète d'un poteau acier
selon l'Eurocode 3 (EN 1993-1-1).

SteelColumn ne contient aucune logique de calcul EC3 : elle délègue tout
aux classes pures situées dans les modules ``elu.*`` et ``buckling.*``
(approche composition — même principe que ``SteelBeam``).

Vérifications couvertes (§6.2 et §6.3) :
    - Compression                       §6.2.4
    - Cisaillement (axes y et z)        §6.2.6
    - Flexion biaxiale                  §6.2.5 / §6.2.9.1
    - Flambement par flexion (y et z)   §6.3.1
    - Déversement                       §6.3.2
    - Interaction N + M                 §6.3.3 (Annexe A ou B)

Unités attendues :
    - Forces      : N
    - Moments     : N·mm
    - Contraintes : MPa
    - Longueurs   : mm
"""

__all__ = ['SteelColumn']

from typing import TypeVar, Optional
from core.formula import FormulaResult, FormulaCollection

# --- ELU checks ---
from norme.EC3.elu.compression import Compression
from norme.EC3.elu.shear import Shear
from norme.EC3.elu.bending import Bending

# --- Buckling / stabilité ---
from norme.EC3.buckling.flexural_buckling import FlexuralBuckling
from norme.EC3.buckling.lateral_torsional import LateralTorsionalBuckling
from norme.EC3.buckling.interaction_NM import InteractionNM

SecMatSteel = TypeVar('SecMatSteel')


class SteelColumn:
    """
    Orchestrateur de vérification d'un poteau acier EC3-1-1.

    Parameters
    ----------
    N : float
        Effort normal de compression de calcul [N] (valeur absolue).
    My, Mz : float
        Moments fléchissants de calcul autour de y et z [N·mm].
    Vy, Vz : float
        Efforts tranchants de calcul selon y et z [N].
    Lcr_y, Lcr_z : float
        Longueurs de flambement par flexion selon y et z [mm].
    Lcr_LT : float, optional
        Longueur de déversement [mm]. Par défaut = Lcr_y.
    sec_mat : SecMatSteel, optional
        Objet portant les propriétés section + matériau (ex. ``SecMatIHU``),
        construit par l'appelant — typiquement via
        ``SecMatIHU.from_properties(...)`` une fois pour le profilé chargé.
        ``SteelColumn`` ne construit rien : elle se contente de le passer
        aux vérifications. Si absent, chaque vérification retombe sur son
        propre mode ``**kwargs`` (fy, A, Iy, Wel_y, …) — les vérifications
        unitaires restent indépendantes et utilisables sans aucun sec_mat.
    section_class : int
        Classe de section (1, 2 ou 3).
    curve_y, curve_z, curve_LT : str, optional
        Courbes de flambement / déversement. Si absentes → déterminées
        automatiquement à partir de la géométrie de section.
    method_LT : str
        Méthode de déversement : ``"general"`` (§6.3.2.2) ou
        ``"rolled"`` (§6.3.2.3, profilés laminés).
    interaction_method : int
        Méthode d'interaction N+M : 1 (Annexe A) ou 2 (Annexe B).
    Cmy, Cmz, CmLT : float
        Coefficients de moment équivalent (Tableau B.3).
    C1 : float
        Coefficient de moment critique de déversement (NCCI SN003).
    moment_diagram : str, optional
        Type de diagramme de moment pour le calcul auto de C1 (déversement)
        et Cm (interaction). Voir ``buckling.lateral_torsional.get_C_coefficients``.
    psi : float
        Rapport des moments d'extrémité M_min/M_max (si ``moment_diagram``
        renseigné).
    """

    # ------------------------------------------------------------------
    #  Construction
    # ------------------------------------------------------------------
    def __init__(
        self,
        N: float = 0.0,
        My: float = 0.0,
        Mz: float = 0.0,
        Vy: float = 0.0,
        Vz: float = 0.0,
        Lcr_y: float = 0.0,
        Lcr_z: float = 0.0,
        Lcr_LT: Optional[float] = None,
        sec_mat: Optional[SecMatSteel] = None,
        section_class: int = 1,
        curve_y: Optional[str] = None,
        curve_z: Optional[str] = None,
        curve_LT: Optional[str] = None,
        method_LT: str = "rolled",
        interaction_method: int = 2,
        Cmy: float = 0.9,
        Cmz: float = 0.9,
        CmLT: float = 0.9,
        C1: float = 1.0,
        moment_diagram: Optional[str] = None,
        psi: float = 0.0,
        **kwargs,
    ) -> None:

        self.__kwargs = kwargs
        self.__sec_mat = sec_mat

        # --- Efforts (valeurs absolues — poteau toujours en compression) ---
        self.__N = abs(N)
        self.__My = abs(My)
        self.__Mz = abs(Mz)
        self.__Vy = abs(Vy)
        self.__Vz = abs(Vz)

        # --- Longueurs de flambement / déversement ---
        self.__Lcr_y = Lcr_y
        self.__Lcr_z = Lcr_z
        self.__Lcr_LT = Lcr_LT if Lcr_LT is not None else Lcr_y

        # --- Paramètres de vérification ---
        self.__section_class = section_class
        self.__curve_y = curve_y
        self.__curve_z = curve_z
        self.__curve_LT = curve_LT
        self.__method_LT = method_LT
        self.__interaction_method = interaction_method
        self.__Cmy = Cmy
        self.__Cmz = Cmz
        self.__CmLT = CmLT
        self.__C1 = C1
        self.__moment_diagram = moment_diagram
        self.__psi = psi

    # ------------------------------------------------------------------
    #  Propriétés — Efforts
    # ------------------------------------------------------------------
    @property
    def N(self) -> float:
        """Effort normal de compression (valeur absolue) [N]"""
        return self.__N

    @property
    def My(self) -> float:
        """Moment fléchissant autour de y (valeur absolue) [N·mm]"""
        return self.__My

    @property
    def Mz(self) -> float:
        """Moment fléchissant autour de z (valeur absolue) [N·mm]"""
        return self.__Mz

    @property
    def Vy(self) -> float:
        """Effort tranchant selon y (valeur absolue) [N]"""
        return self.__Vy

    @property
    def Vz(self) -> float:
        """Effort tranchant selon z (valeur absolue) [N]"""
        return self.__Vz

    @property
    def sec_mat(self) -> Optional[SecMatSteel]:
        """Objet section-matériau associé (peut être None)."""
        return self.__sec_mat

    # ------------------------------------------------------------------
    #  Vérifications ELU individuelles
    # ------------------------------------------------------------------
    def check_compression(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Vérification à la compression — EC3-1-1 §6.2.4. None si N = 0."""
        if self.__N == 0.0:
            return None
        c = Compression(self.__N, sec_mat=self.__sec_mat, **self.__kwargs)
        return c.report(with_values=with_values)

    def check_shear_y(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Vérification au cisaillement axe y — EC3-1-1 §6.2.6. None si Vy = 0."""
        if self.__Vy == 0.0:
            return None
        s = Shear(Ved=self.__Vy, axis="y", sec_mat=self.__sec_mat, **self.__kwargs)
        return s.report(with_values=with_values)

    def check_shear_z(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Vérification au cisaillement axe z — EC3-1-1 §6.2.6. None si Vz = 0."""
        if self.__Vz == 0.0:
            return None
        s = Shear(Ved=self.__Vz, axis="z", sec_mat=self.__sec_mat, **self.__kwargs)
        return s.report(with_values=with_values)

    def check_bending(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Vérification en flexion biaxiale — EC3-1-1 §6.2.5 / §6.2.9.1.
        None si My = Mz = 0."""
        if self.__My == 0.0 and self.__Mz == 0.0:
            return None
        b = Bending(My_ed=self.__My, Mz_ed=self.__Mz, sec_mat=self.__sec_mat, **self.__kwargs)
        return b.report(with_values=with_values)

    def check_elu(self, with_values: bool = False) -> FormulaCollection:
        """
        Vérification ELU globale : agrège compression, cisaillement (y, z)
        et flexion biaxiale.
        """
        fc = FormulaCollection(
            title="Vérifications ELU — Résistance de section",
            ref="EC3-1-1 — §6.2",
        )
        for check_fn in [
            self.check_compression,
            self.check_shear_y,
            self.check_shear_z,
            self.check_bending,
        ]:
            result = check_fn(with_values=with_values)
            if result is not None:
                for r in result:
                    fc.add(r)
        return fc

    # ------------------------------------------------------------------
    #  Vérifications stabilité individuelles
    # ------------------------------------------------------------------
    def _flexural_buckling(self) -> Optional[FlexuralBuckling]:
        """Instancie FlexuralBuckling (None si N = 0)."""
        if self.__N == 0.0:
            return None
        return FlexuralBuckling(
            Ned=self.__N,
            mat=self.__sec_mat, sec=self.__sec_mat,
            Lcr_y=self.__Lcr_y, Lcr_z=self.__Lcr_z,
            curve_y=self.__curve_y, curve_z=self.__curve_z,
            section_class=self.__section_class,
            **self.__kwargs,
        )

    def check_flexural_buckling(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Vérification au flambement par flexion — EC3-1-1 §6.3.1. None si N = 0."""
        fb = self._flexural_buckling()
        if fb is None:
            return None
        return fb.report(with_values=with_values)

    def _lateral_torsional(self) -> Optional[LateralTorsionalBuckling]:
        """Instancie LateralTorsionalBuckling (None si My = 0)."""
        if self.__My == 0.0:
            return None
        return LateralTorsionalBuckling(
            Med_y=self.__My,
            mat=self.__sec_mat, sec=self.__sec_mat,
            L=self.__Lcr_LT, Lcr_LT=self.__Lcr_LT,
            method=self.__method_LT, curve_LT=self.__curve_LT,
            section_class=self.__section_class,
            C1=self.__C1, moment_diagram=self.__moment_diagram, psi=self.__psi,
            **self.__kwargs,
        )

    def check_lateral_torsional(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Vérification au déversement — EC3-1-1 §6.3.2. None si My = 0."""
        ltb = self._lateral_torsional()
        if ltb is None:
            return None
        return ltb.report(with_values=with_values)

    def check_interaction_NM(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        Interaction N + M (flambement + déversement) — EC3-1-1 §6.3.3.
        None si N = 0 et My = Mz = 0.
        """
        if self.__N == 0.0 and self.__My == 0.0 and self.__Mz == 0.0:
            return None

        fb = self._flexural_buckling()
        ltb = self._lateral_torsional()

        chi_y = fb.chi_y if fb is not None else 1.0
        chi_z = fb.chi_z if fb is not None else 1.0
        lambda_bar_y = fb.lambda_bar_y if fb is not None else 0.0
        lambda_bar_z = fb.lambda_bar_z if fb is not None else 0.0
        chi_LT = ltb.chi_LT if ltb is not None else 1.0
        lambda_bar_LT = ltb.lambda_bar_LT if ltb is not None else 0.0

        inm = InteractionNM(
            Ned=self.__N, Med_y=self.__My, Med_z=self.__Mz,
            chi_y=chi_y, chi_z=chi_z, chi_LT=chi_LT,
            mat=self.__sec_mat, sec=self.__sec_mat,
            section_class=self.__section_class,
            Cmy=self.__Cmy, Cmz=self.__Cmz, CmLT=self.__CmLT,
            lambda_bar_y=lambda_bar_y, lambda_bar_z=lambda_bar_z,
            lambda_bar_LT=lambda_bar_LT,
            interaction_method=self.__interaction_method,
            **self.__kwargs,
        )
        return inm.report(with_values=with_values)

    def check_stability(self, with_values: bool = False) -> FormulaCollection:
        """Vérification stabilité globale : flambement + déversement + interaction N+M."""
        fc = FormulaCollection(
            title="Vérifications Stabilité",
            ref="EC3-1-1 — §6.3",
        )
        for check_fn in [
            self.check_flexural_buckling,
            self.check_lateral_torsional,
            self.check_interaction_NM,
        ]:
            result = check_fn(with_values=with_values)
            if result is not None:
                for r in result:
                    fc.add(r)
        return fc

    # ------------------------------------------------------------------
    #  Vérification complète
    # ------------------------------------------------------------------
    def full_check(self, with_values: bool = False) -> FormulaCollection:
        """Vérification complète : ELU + Stabilité."""
        fc = FormulaCollection(
            title="Vérification complète — Poteau acier",
            ref="EC3-1-1",
        )
        for r in self.check_elu(with_values=with_values):
            fc.add(r)
        for r in self.check_stability(with_values=with_values):
            fc.add(r)
        return fc

    # ------------------------------------------------------------------
    #  Résumé
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_max_ratio(fc: Optional[FormulaCollection]) -> Optional[float]:
        """Extrait le taux de travail max parmi les checks d'un FC."""
        if fc is None or len(fc) == 0:
            return None
        checks = fc.checks
        if not checks:
            return None
        return max(c.result for c in checks)

    @staticmethod
    def _extract_governing_check(fc: Optional[FormulaCollection]) -> Optional[str]:
        """Extrait le nom du check déterminant (result max) d'un FC."""
        if fc is None or len(fc) == 0:
            return None
        max_ratio = -1.0
        governing = None
        for fr in fc.checks:
            if fr.result is not None and fr.result >= max_ratio:
                max_ratio = fr.result
                governing = fr.name
        return governing

    def summary(self) -> dict:
        """
        Retourne un dictionnaire résumé de toutes les vérifications.

        Returns
        -------
        dict
            {
                "elu":       {"governing_check": str, "max_ratio": float, "is_ok": bool},
                "stability": {"governing_check": str, "max_ratio": float, "is_ok": bool},
                "is_ok":     bool or None,
            }
        """
        result = {}

        for category, fc_method in [
            ("elu", self.check_elu),
            ("stability", self.check_stability),
        ]:
            fc = fc_method(with_values=False)
            ratio = self._extract_max_ratio(fc)
            check = self._extract_governing_check(fc)

            if ratio is not None:
                is_ok = ratio <= 1.0
            else:
                is_ok = None

            result[category] = {
                "governing_check": check,
                "max_ratio": ratio,
                "is_ok": is_ok,
            }

        all_checks = [result[k]["is_ok"] for k in ("elu", "stability")]
        evaluated = [v for v in all_checks if v is not None]
        result["is_ok"] = all(evaluated) if evaluated else None

        return result

    # ------------------------------------------------------------------
    #  Représentation
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        N_kN = self.__N / 1e3
        My_kNm = self.__My / 1e6
        Mz_kNm = self.__Mz / 1e6
        return (
            f"SteelColumn(N={N_kN:.1f}kN, My={My_kNm:.1f}kN·m, "
            f"Mz={Mz_kNm:.1f}kN·m, Vy={self.__Vy/1e3:.1f}kN, "
            f"Vz={self.__Vz/1e3:.1f}kN)"
        )


# ======================================================================
#  Debug / exemple d'utilisation
# ======================================================================
if __name__ == "__main__":
    from core.sec_mat.sec_mat_i_h_u import SecMatIHU

    sep = "-" * 60

    # --- HEA 200 / S275 — le sec_mat est construit UNE fois par
    #     l'appelant (ici le script de test, dans l'app ce serait le
    #     backend juste après avoir chargé le profilé JSON), puis
    #     réutilisé pour toutes les vérifications de la barre. ---
    sec_mat = SecMatIHU.from_properties(
        "HEA 200",
        h=190.0, b=200.0, tw=6.5, tf=10.0, r=18.0,
        A=5383.0, Avz=1980.0, Iy=3692e4, Iz=1336e4,
        wel_y=388.6e3, wel_z=133.0e3, wpl_y=429.5e3, wpl_z=203.8e3,
        iy=82.8, iz=49.8, It=21.0e4, Iw=108.0e9,
        section_type="H",
        fy=275.0, fu=430.0, gamma_m0=1.0, gamma_m1=1.0, gamma_m2=1.25,
        section_class=1,
    )

    print(f"\n{sep}")
    print("  CAS 1 : Compression + flexion biaxiale + cisaillement")
    print(sep)
    col1 = SteelColumn(
        N=650e3, My=25e6, Mz=10e6, Vy=12e3, Vz=30e3,
        Lcr_y=4000.0, Lcr_z=4000.0, Lcr_LT=4000.0,
        sec_mat=sec_mat, section_class=1,
        method_LT="rolled", interaction_method=2,
    )
    print(f"  {repr(col1)}")
    try:
        s = col1.summary()
        for cat in ("elu", "stability"):
            d = s[cat]
            print(f"  {cat.upper():10s} | check: {str(d['governing_check']):20s} "
                  f"| ratio: {d['max_ratio']:.4f} | ok: {d['is_ok']}")
        print(f"  {'GLOBAL':10s} | is_ok: {s['is_ok']}")
    except Exception as e:
        print(f"  ⚠ {type(e).__name__}: {e}")

    print(f"\n{sep}")
    print("  CAS 2 : Compression pure (pas de moment) — même sec_mat réutilisé")
    print(sep)
    col2 = SteelColumn(N=500e3, Lcr_y=4000.0, Lcr_z=4000.0, sec_mat=sec_mat, section_class=1)
    print(f"  {repr(col2)}")
    try:
        s = col2.summary()
        print(f"  ELU is_ok        = {s['elu']['is_ok']}")
        print(f"  Stability is_ok  = {s['stability']['is_ok']}")
        print(f"  GLOBAL is_ok     = {s['is_ok']}")
    except Exception as e:
        print(f"  ⚠ {type(e).__name__}: {e}")

    print(f"\n{sep}")
    print("  CAS 3 : Full check (rapport détaillé)")
    print(sep)
    try:
        fc = col1.full_check(with_values=True)
        print(fc)
    except Exception as e:
        print(f"  ⚠ {type(e).__name__}: {e}")

    print(f"\n{sep}")
    print("  CAS 4 : Sans sec_mat — vérifications en mode kwargs indépendant")
    print(sep)
    col4 = SteelColumn(
        N=500e3, Lcr_y=4000.0, Lcr_z=4000.0, section_class=1,
        fy=275.0, A=5383.0, gamma_m0=1.0,
    )
    print(f"  {repr(col4)}")
    try:
        fc = col4.check_compression(with_values=True)
        print(f"  Compression (kwargs seuls, sans sec_mat) : {fc}")
    except Exception as e:
        print(f"  ⚠ {type(e).__name__}: {e}")

    print(f"\n{'=' * 60}")
    print("  FIN DES TESTS")
    print(f"{'=' * 60}")
