#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classe orchestratrice pour la vérification complète d'une poutre acier,
selon l'Eurocode 3 (EN 1993-1-1 + EN 1993-1-5) **ou** la SIA 263:2013.

SteelBeam ne contient aucune logique de calcul : elle délègue tout aux
classes de vérification unitaires indépendantes (approche composition —
même principe que ``SteelColumn``) :

    norme="EC3"      norme.EC3.elu.*        norme.EC3.buckling.*
                     norme.EC3.els.*        (EN 1993-1-1)
                     norme.EC3.elu.shear_buckling  (EN 1993-1-5 §5)
    norme="SIA263"   norme.SIA263.elu.*     norme.SIA263.stability.*

Vérifications couvertes (assemblages exclus) :

    RÉSISTANCE DE SECTION
        Traction / compression          EC3 §6.2.3-6.2.4   SIA §5.1.2
        Flexion (y et z)                EC3 §6.2.5         SIA §5.1.3
        Effort tranchant (y et z)       EC3 §6.2.6         SIA §5.1.4
        Voilement par cisaillement      EN 1993-1-5 §5     SIA §4.5.4
        Flexion + tranchant             EC3 §6.2.8         SIA §5.1.5
        Flexion + effort normal         EC3 §6.2.9         SIA §5.1.6
        Flexion + tranchant + normal    EC3 §6.2.10        SIA §5.1.7-5.1.8

    STABILITÉ
        Déversement                     EC3 §6.3.2         SIA §4.5.2
        Flambement par flexion (y, z)   EC3 §6.3.1         SIA §4.5.1
        Interaction N + M               EC3 §6.3.3         SIA §5.1.9

    APTITUDE AU SERVICE
        Flèche verticale                EC3 §7.2           SIA §4.10 (→ SIA 260)

Hors périmètre : assemblages, fatigue, incendie, séisme, classe de
section 4 (sections efficaces), contribution des semelles au voilement
par cisaillement (Vbf,Rd — négligée, sécuritaire).

Unités attendues :
    - Forces      : N
    - Moments     : N·mm
    - Contraintes : MPa
    - Longueurs   : mm
"""

__all__ = ['SteelBeam']

from typing import Optional, TypeVar

from core.formula import FormulaResult, FormulaCollection

# --- EC3 : résistance de section ---
from norme.EC3.elu.traction import Tension
from norme.EC3.elu.compression import Compression
from norme.EC3.elu.shear import Shear
from norme.EC3.elu.bending import Bending
from norme.EC3.elu.combined import (
    CombinedBendingShear, CombinedBendingAxial, CombinedAll,
)
from norme.EC3.elu.shear_buckling import ShearBuckling

# --- EC3 : stabilité ---
from norme.EC3.buckling.flexural_buckling import FlexuralBuckling
from norme.EC3.buckling.lateral_torsional import LateralTorsionalBuckling
from norme.EC3.buckling.interaction_NM import InteractionNM

# --- EC3 : aptitude au service ---
from norme.EC3.els.deflection import Deflection

# --- SIA 263 ---
from norme.SIA263.elu.resistance import (
    AxialResistanceSIA, BendingResistanceSIA, ShearResistanceSIA,
    CombinedBendingShearSIA, CombinedBendingAxialSIA,
)
from norme.SIA263.stability.buckling import (
    FlexuralBucklingSIA, LateralTorsionalBucklingSIA, ShearBucklingSIA,
)

SecMatSteel = TypeVar('SecMatSteel')

_NORMES = ("EC3", "SIA263")


class SteelBeam:
    """
    Orchestrateur de vérification d'une poutre acier — EC3 ou SIA 263.

    Parameters
    ----------
    sec_mat : SecMatSteel
        Objet section + matériau, construit par l'appelant (typiquement
        ``SecMatIHU.from_properties(...)``). ``SteelBeam`` ne construit
        rien : elle le passe aux vérifications unitaires.
    norme : str
        ``"EC3"`` (EN 1993-1-1 / 1-5) ou ``"SIA263"``.
    N : float
        Effort normal de calcul [N]. Positif = traction (convention
        ``tension_positive``).
    Vy, Vz : float
        Efforts tranchants de calcul [N].
    My, Mz : float
        Moments fléchissants de calcul [N·mm].
    L : float
        Portée de la poutre [mm] — utilisée pour la flèche.
    Lcr_LT : float, optional
        Longueur de déversement [mm]. Par défaut = ``L``.
    Lcr_y, Lcr_z : float, optional
        Longueurs de flambement [mm] (si compression). Par défaut = ``L``.
    section_class : int
        Classe de section (1, 2 ou 3).
    a_stiffener : float, optional
        Espacement des raidisseurs transversaux d'âme [mm]. ``None`` =
        âme non raidie.
    rigid_end_post : bool
        Montant d'extrémité rigide (EN 1993-1-5 §9.3.1).
    profile_type : str
        ``"rolled"`` (laminé) ou ``"welded"`` (soudé). Vocabulaire unique
        pour les deux normes, traduit en interne :
            SIA §4.5.2.3 → α_D = 0,21 (rolled) / 0,49 (welded)
            EC3          → méthode §6.3.2.3 "rolled" (laminé) ou
                           §6.3.2.2 "general" (soudé)
    psi : float
        Rapport des moments d'extrémité M_min/M_max (signes compris).
    C1 : float
        Coefficient de moment critique de déversement (EC3).
    deflection, deflection_limit : float, optional
        Flèche calculée / admissible [mm]. Si ``deflection`` est absente
        mais ``q`` fourni, elle est calculée analytiquement.
    q : float, optional
        Charge répartie de service [N/mm] pour le calcul de flèche.
    support : str
        Conditions d'appui pour la flèche — ``"simply_supported"``,
        ``"cantilever"``, ``"fixed_fixed"``, ``"fixed_pinned"``.
    limit_type : str
        Clé de limite de flèche (voir ``norme.EC3.els.limits``).
    limit_ratio : float, optional
        Ratio de flèche personnalisé (ex. 300 → L/300).
    tension_positive : bool
        Convention de signe. ``True`` ⇒ N > 0 = traction.
    """

    def __init__(
        self,
        sec_mat: Optional[SecMatSteel] = None,
        norme: str = "EC3",
        N: float = 0.0,
        Vy: float = 0.0,
        Vz: float = 0.0,
        My: float = 0.0,
        Mz: float = 0.0,
        L: float = 0.0,
        Lcr_LT: Optional[float] = None,
        Lcr_y: Optional[float] = None,
        Lcr_z: Optional[float] = None,
        section_class: int = 1,
        a_stiffener: Optional[float] = None,
        rigid_end_post: bool = True,
        profile_type: str = "rolled",
        psi: float = 1.0,
        C1: float = 1.0,
        Cmy: float = 0.9,
        Cmz: float = 0.9,
        interaction_method: int = 2,
        curve_y: Optional[str] = None,
        curve_z: Optional[str] = None,
        curve_LT: Optional[str] = None,
        deflection: Optional[float] = None,
        deflection_limit: Optional[float] = None,
        q: Optional[float] = None,
        support: str = "simply_supported",
        limit_type: str = "floor_general",
        limit_ratio: Optional[float] = None,
        tension_positive: bool = True,
        **kwargs,
    ) -> None:
        norme = norme.upper().strip()
        if norme not in _NORMES:
            raise ValueError(f"norme doit être 'EC3' ou 'SIA263' (reçu : '{norme}')")

        self.__norme = norme
        self.__sec_mat = sec_mat
        self.__kwargs = kwargs
        self.__tension_positive = tension_positive

        # --- Efforts (convention interne : N > 0 = traction) ---
        self.__N_raw = N
        self.__N = N if tension_positive else -N
        self.__Vy = abs(Vy)
        self.__Vz = abs(Vz)
        self.__My = abs(My)
        self.__Mz = abs(Mz)

        # --- Géométrie ---
        self.__L = L
        self.__Lcr_LT = Lcr_LT if Lcr_LT is not None else L
        self.__Lcr_y = Lcr_y if Lcr_y is not None else L
        self.__Lcr_z = Lcr_z if Lcr_z is not None else L

        # --- Paramètres de vérification ---
        self.__section_class = section_class
        self.__a_stiffener = a_stiffener
        self.__rigid_end_post = rigid_end_post
        self.__profile_type = profile_type.lower()
        if self.__profile_type not in ("rolled", "welded"):
            raise ValueError(
                f"profile_type doit être 'rolled' ou 'welded' "
                f"(reçu : '{profile_type}')"
            )
        self.__psi = psi
        self.__C1 = C1
        self.__Cmy = Cmy
        self.__Cmz = Cmz
        self.__interaction_method = interaction_method
        self.__curve_y = curve_y
        self.__curve_z = curve_z
        self.__curve_LT = curve_LT

        # --- ELS ---
        self.__deflection = deflection
        self.__deflection_limit = deflection_limit
        self.__q = q
        self.__support = support
        self.__limit_type = limit_type
        self.__limit_ratio = limit_ratio

        # --- γM pour la SIA (γM1 = 1,05) ---
        self.__sia_kw = {"gamma_m1": kwargs.get("gamma_m1_sia", 1.05)}

    # ==================================================================
    #  Propriétés
    # ==================================================================
    @property
    def norme(self) -> str:
        """Norme de vérification retenue."""
        return self.__norme

    @property
    def sec_mat(self) -> Optional[SecMatSteel]:
        return self.__sec_mat

    @property
    def N(self) -> float:
        """Effort normal signé (+ = traction) [N]."""
        return self.__N

    @property
    def Vy(self) -> float:
        return self.__Vy

    @property
    def Vz(self) -> float:
        return self.__Vz

    @property
    def My(self) -> float:
        return self.__My

    @property
    def Mz(self) -> float:
        return self.__Mz

    @property
    def is_tension(self) -> bool:
        return self.__N > 0.0

    @property
    def is_compression(self) -> bool:
        return self.__N < 0.0

    @property
    def is_ec3(self) -> bool:
        return self.__norme == "EC3"

    def _sec(self, name: str, default: float = 0.0) -> float:
        """Lecture tolérante d'une propriété du sec_mat (ou kwargs)."""
        if self.__sec_mat is not None and hasattr(self.__sec_mat, name):
            return getattr(self.__sec_mat, name)
        return self.__kwargs.get(name, default)

    # ==================================================================
    #  Résistance de section — traction / compression
    # ==================================================================
    def check_axial(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Traction ou compression de section. None si N = 0."""
        if self.__N == 0.0:
            return None
        if self.is_ec3:
            if self.is_tension:
                return Tension(self.__N, sec_mat=self.__sec_mat,
                               **self.__kwargs).report(with_values=with_values)
            return Compression(abs(self.__N), sec_mat=self.__sec_mat,
                               **self.__kwargs).report(with_values=with_values)
        return AxialResistanceSIA(
            Ned=abs(self.__N), tension=self.is_tension,
            sec_mat=self.__sec_mat, **self.__sia_kw, **self.__kwargs,
        ).report(with_values=with_values)

    # ==================================================================
    #  Résistance de section — flexion
    # ==================================================================
    def check_bending(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Flexion (uni- ou biaxiale). None si My = Mz = 0."""
        if self.__My == 0.0 and self.__Mz == 0.0:
            return None
        if self.is_ec3:
            return Bending(
                My_ed=self.__My, Mz_ed=self.__Mz, sec_mat=self.__sec_mat,
                section_class=self.__section_class, **self.__kwargs,
            ).report(with_values=with_values)
        return BendingResistanceSIA(
            My_ed=self.__My, Mz_ed=self.__Mz,
            section_class=self.__section_class, sec_mat=self.__sec_mat,
            **self.__sia_kw, **self.__kwargs,
        ).report(with_values=with_values)

    # ==================================================================
    #  Résistance de section — effort tranchant
    # ==================================================================
    def _shear(self, axis: str):
        """Instance de vérification au cisaillement pour l'axe donné."""
        ved = self.__Vz if axis == "z" else self.__Vy
        if self.is_ec3:
            return Shear(Ved=ved, axis=axis, sec_mat=self.__sec_mat,
                         **self.__kwargs)
        return ShearResistanceSIA(
            Ved=ved, axis=axis, sec_mat=self.__sec_mat,
            **self.__sia_kw, **self.__kwargs,
        )

    def check_shear_y(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Cisaillement selon y. None si Vy = 0."""
        if self.__Vy == 0.0:
            return None
        return self._shear("y").report(with_values=with_values)

    def check_shear_z(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Cisaillement selon z (âme). None si Vz = 0."""
        if self.__Vz == 0.0:
            return None
        return self._shear("z").report(with_values=with_values)

    # ==================================================================
    #  Voilement par cisaillement de l'âme
    # ==================================================================
    def _shear_buckling(self):
        """Instance de vérification au voilement par cisaillement."""
        if self.is_ec3:
            return ShearBuckling(
                Ved=self.__Vz, sec_mat=self.__sec_mat,
                a=self.__a_stiffener, rigid_end_post=self.__rigid_end_post,
                **self.__kwargs,
            )
        return ShearBucklingSIA(
            Ved=self.__Vz, sec_mat=self.__sec_mat, a=self.__a_stiffener,
            **self.__sia_kw, **self.__kwargs,
        )

    def check_shear_buckling(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Voilement par cisaillement de l'âme. None si Vz = 0."""
        if self.__Vz == 0.0:
            return None
        return self._shear_buckling().report(with_values=with_values)

    # ==================================================================
    #  Interaction M + V
    # ==================================================================
    def check_bending_shear(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        Flexion + effort tranchant. None si l'un des deux est nul ou si le
        cisaillement est faible (V ≤ 0,5·V_Rd → pas de réduction).
        """
        if self.__My == 0.0 or self.__Vz == 0.0:
            return None
        sh = self._shear("z")
        if not sh.is_high_shear:
            return None
        if self.is_ec3:
            return CombinedBendingShear(
                My_ed=self.__My, Ved=self.__Vz,
                section_class=self.__section_class,
                mat=self.__sec_mat, sec=self.__sec_mat, shear=sh,
                **self.__kwargs,
            ).report(with_values=with_values)
        return CombinedBendingShearSIA(
            My_ed=self.__My, Ved=self.__Vz, V_Rd=sh.v_rd,
            section_class=self.__section_class, sec_mat=self.__sec_mat,
            **self.__sia_kw, **self.__kwargs,
        ).report(with_values=with_values)

    # ==================================================================
    #  Interaction M + N  et  M + V + N
    # ==================================================================
    def check_bending_axial(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        Flexion + effort normal (et cisaillement si élevé — §6.2.10 /
        §5.1.7). None si N = 0 ou si aucun moment.
        """
        if self.__N == 0.0 or (self.__My == 0.0 and self.__Mz == 0.0):
            return None

        sh = self._shear("z") if self.__Vz else None
        high_shear = bool(sh and sh.is_high_shear)

        if self.is_ec3:
            if high_shear:
                return CombinedAll(
                    Ned=abs(self.__N), My_ed=self.__My, Mz_ed=self.__Mz,
                    Ved=self.__Vz, section_class=self.__section_class,
                    section_type=self._sec("section_type", "I") or "I",
                    mat=self.__sec_mat, sec=self.__sec_mat, shear=sh,
                    **self.__kwargs,
                ).report(with_values=with_values)
            return CombinedBendingAxial(
                Ned=abs(self.__N), My_ed=self.__My, Mz_ed=self.__Mz,
                section_class=self.__section_class,
                section_type=self._sec("section_type", "I") or "I",
                mat=self.__sec_mat, sec=self.__sec_mat, **self.__kwargs,
            ).report(with_values=with_values)

        # --- SIA 263 : on construit les résistances de section requises ---
        n_res = AxialResistanceSIA(
            Ned=abs(self.__N), tension=self.is_tension,
            sec_mat=self.__sec_mat, **self.__sia_kw, **self.__kwargs,
        )
        m_res = BendingResistanceSIA(
            My_ed=self.__My, Mz_ed=self.__Mz,
            section_class=self.__section_class, sec_mat=self.__sec_mat,
            **self.__sia_kw, **self.__kwargs,
        )
        # §5.1.7 : si V > 0,5·V_Rd, la résistance en flexion est réduite.
        my_rd = m_res.my_rd
        if high_shear:
            my_rd = CombinedBendingShearSIA(
                My_ed=self.__My, Ved=self.__Vz, V_Rd=sh.v_rd,
                section_class=self.__section_class, sec_mat=self.__sec_mat,
                **self.__sia_kw, **self.__kwargs,
            ).my_v_rd
        return CombinedBendingAxialSIA(
            Ned=abs(self.__N), My_ed=self.__My, Mz_ed=self.__Mz,
            N_Rd=n_res.n_rd, My_Rd=my_rd, Mz_Rd=m_res.mz_rd,
            section_class=self.__section_class,
            section_type=self._sec("section_type", "I") or "I",
            sec_mat=self.__sec_mat, **self.__kwargs,
        ).report(with_values=with_values)

    # ==================================================================
    #  ELU global
    # ==================================================================
    def check_elu(self, with_values: bool = False) -> FormulaCollection:
        """Résistance de section : N, M, V, voilement et interactions."""
        ref = "EC3-1-1 — §6.2 / EN 1993-1-5 §5" if self.is_ec3 else "SIA 263 — §5.1"
        fc = FormulaCollection(
            title="Vérifications ELU — Résistance de section", ref=ref,
        )
        for fn in (
            self.check_axial,
            self.check_bending,
            self.check_shear_y,
            self.check_shear_z,
            self.check_shear_buckling,
            self.check_bending_shear,
            self.check_bending_axial,
        ):
            result = fn(with_values=with_values)
            if result is not None:
                for r in result:
                    fc.add(r)
        return fc

    # ==================================================================
    #  Stabilité — déversement
    # ==================================================================
    def _lateral_torsional(self):
        """Instance de vérification au déversement (None si My = 0)."""
        if self.__My == 0.0:
            return None
        if self.is_ec3:
            # EC3 : §6.3.2.3 réservé aux profilés laminés ; les profilés
            # soudés relèvent de la méthode générale §6.3.2.2.
            method_ec3 = "rolled" if self.__profile_type == "rolled" else "general"
            return LateralTorsionalBuckling(
                Med_y=self.__My, mat=self.__sec_mat, sec=self.__sec_mat,
                L=self.__Lcr_LT, Lcr_LT=self.__Lcr_LT,
                method=method_ec3, curve_LT=self.__curve_LT,
                section_class=self.__section_class,
                C1=self.__C1, psi=self.__psi, **self.__kwargs,
            )
        return LateralTorsionalBucklingSIA(
            My_ed=self.__My, L=self.__Lcr_LT, profile=self.__profile_type,
            section_class=self.__section_class, psi=self.__psi,
            sec_mat=self.__sec_mat, **self.__sia_kw, **self.__kwargs,
        )

    def check_lateral_torsional(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Déversement — EC3 §6.3.2 / SIA §4.5.2. None si My = 0."""
        ltb = self._lateral_torsional()
        if ltb is None:
            return None
        return ltb.report(with_values=with_values)

    # ==================================================================
    #  Stabilité — flambement (si compression)
    # ==================================================================
    def _flexural_buckling(self, axis: str = "y"):
        """Instance de flambement pour l'axe donné (None si pas de compression)."""
        if not self.is_compression:
            return None
        n = abs(self.__N)
        if self.is_ec3:
            return FlexuralBuckling(
                Ned=n, mat=self.__sec_mat, sec=self.__sec_mat,
                Lcr_y=self.__Lcr_y, Lcr_z=self.__Lcr_z,
                curve_y=self.__curve_y, curve_z=self.__curve_z,
                section_class=self.__section_class, **self.__kwargs,
            )
        return FlexuralBucklingSIA(
            Ned=n, Lk=self.__Lcr_z if axis == "z" else self.__Lcr_y,
            axis=axis, curve=(self.__curve_z or "b") if axis == "z"
            else (self.__curve_y or "a"),
            sec_mat=self.__sec_mat, **self.__sia_kw, **self.__kwargs,
        )

    def check_flexural_buckling(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """Flambement par flexion — EC3 §6.3.1 / SIA §4.5.1. None si pas de compression."""
        if not self.is_compression:
            return None
        if self.is_ec3:
            fb = self._flexural_buckling()
            return fb.report(with_values=with_values) if fb else None
        fc = FormulaCollection(
            title="Flambement par flexion", ref="SIA 263 — §4.5.1",
        )
        for axis in ("y", "z"):
            fb = self._flexural_buckling(axis)
            if fb is None:
                continue
            for r in fb.report(with_values=with_values):
                fc.add(r)
        return fc

    # ==================================================================
    #  Stabilité — interaction N + M
    # ==================================================================
    def check_interaction_NM(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        Interaction flambement + déversement — EC3 §6.3.3 / SIA §5.1.9.
        None hors compression, ou si aucun moment.
        """
        if not self.is_compression or (self.__My == 0.0 and self.__Mz == 0.0):
            return None

        ltb = self._lateral_torsional()

        if self.is_ec3:
            fb = self._flexural_buckling()
            return InteractionNM(
                Ned=abs(self.__N), Med_y=self.__My, Med_z=self.__Mz,
                chi_y=fb.chi_y if fb else 1.0,
                chi_z=fb.chi_z if fb else 1.0,
                chi_LT=ltb.chi_LT if ltb else 1.0,
                mat=self.__sec_mat, sec=self.__sec_mat,
                section_class=self.__section_class,
                Cmy=self.__Cmy, Cmz=self.__Cmz, CmLT=self.__Cmy,
                lambda_bar_y=fb.lambda_bar_y if fb else 0.0,
                lambda_bar_z=fb.lambda_bar_z if fb else 0.0,
                lambda_bar_LT=ltb.lambda_bar_LT if ltb else 0.0,
                interaction_method=self.__interaction_method,
                **self.__kwargs,
            ).report(with_values=with_values)

        # --- SIA 263 §5.1.9.1, éq. (49) ---
        return self._interaction_sia(with_values=with_values)

    def _interaction_sia(self, with_values: bool = False) -> FormulaCollection:
        """
        Stabilité des barres comprimées et fléchies — SIA 263 §5.1.9.1 :

            N_Ed/N_K,Rd + [1/(1 − N_Ed/N_cr)]·M_Ed/M_Rd ≤ 1,0     (49)
        """
        import math

        fc = FormulaCollection(
            title="Stabilité — barre comprimée et fléchie",
            ref="SIA 263 — §5.1.9.1, éq. (49)",
        )
        n_ed = abs(self.__N)
        fb = self._flexural_buckling("y")
        ltb = self._lateral_torsional()

        nk_rd = fb.nk_rd if fb else 0.0
        # M_Rd : résistance au déversement si applicable, sinon section
        if ltb is not None:
            m_rd = ltb.md_rd
            m_src = "M_D,Rd (déversement)"
        else:
            m_res = BendingResistanceSIA(
                My_ed=self.__My, section_class=self.__section_class,
                sec_mat=self.__sec_mat, **self.__sia_kw, **self.__kwargs,
            )
            m_rd = m_res.my_rd
            m_src = "My,Rd (section)"

        # N_cr = π²·E·I / L² dans le plan de flexion (axe y)
        E = self._sec("E", 210000.0) or 210000.0
        Iy = self._sec("Iy", 0.0)
        n_cr = (
            math.pi ** 2 * E * Iy / self.__Lcr_y ** 2
            if self.__Lcr_y > 0 and Iy > 0 else 0.0
        )

        amp_denom = 1.0 - (n_ed / n_cr if n_cr > 0 else 0.0)
        amplification = 1.0 / amp_denom if amp_denom > 0 else float('inf')

        t_n = n_ed / nk_rd if nk_rd else float('inf')
        t_m = (self.__My / m_rd) if m_rd else 0.0
        total = t_n + amplification * t_m if not math.isinf(amplification) else float('inf')
        total = round(total, 4) if not math.isinf(total) else float('inf')

        fc.add(FormulaResult(
            name="N_cr",
            formula="N_cr = π²·E·Iy / L_K,y²",
            formula_values=(
                f"N_cr = π² × {E:.0f} × {Iy:.1f} / {self.__Lcr_y:.1f}² "
                f"= {n_cr:.2f} N" if with_values else ""
            ),
            result=n_cr, unit="N", ref="SIA 263 — §4.5.1.4",
        ))
        fc.add(FormulaResult(
            name="1/(1 − N_Ed/N_cr)",
            formula="Facteur d'amplification du moment",
            formula_values=(
                f"1/(1 − {n_ed:.2f}/{n_cr:.2f}) = {amplification:.4f}"
                if with_values else ""
            ),
            result=round(amplification, 4) if not math.isinf(amplification) else float('inf'),
            unit="-", ref="SIA 263 — §5.1.9.1",
        ))
        fv = ""
        if with_values:
            status = "OK ✓" if total <= 1.0 else "NON VÉRIFIÉ ✗"
            fv = (
                f"{t_n:.4f} + {amplification:.4f} × {t_m:.4f} = {total:.4f} "
                f"≤ 1,0 → {status}   [M_Rd = {m_src}]"
            )
        fc.add(FormulaResult(
            name="Interaction N+M (stabilité)",
            formula="N_Ed/N_K,Rd + [1/(1 − N_Ed/N_cr)]·M_Ed/M_Rd ≤ 1,0",
            formula_values=fv, result=total, unit="-",
            ref="SIA 263 — §5.1.9.1, éq. (49)",
            is_check=True, limit=1.0,
        ))
        return fc

    def check_stability(self, with_values: bool = False) -> FormulaCollection:
        """Stabilité globale : déversement + flambement + interaction."""
        ref = "EC3-1-1 — §6.3" if self.is_ec3 else "SIA 263 — §4.5 / §5.1.9"
        fc = FormulaCollection(title="Vérifications Stabilité", ref=ref)
        for fn in (
            self.check_lateral_torsional,
            self.check_flexural_buckling,
            self.check_interaction_NM,
        ):
            result = fn(with_values=with_values)
            if result is not None:
                for r in result:
                    fc.add(r)
        return fc

    # ==================================================================
    #  Aptitude au service — flèche
    # ==================================================================
    def check_deflection(self, with_values: bool = False) -> Optional[FormulaCollection]:
        """
        Flèche verticale — EC3 §7.2 (la SIA 263 §4.10 renvoie aux limites
        de la SIA 260 ; les mêmes ratios L/n sont utilisés ici, la limite
        restant paramétrable). None si ni flèche ni charge fournie.
        """
        if self.__deflection is None and self.__q is None:
            return None
        if self.__deflection is not None:
            d = Deflection(
                mode="calculated", support=self.__support, L=self.__L,
                delta=self.__deflection, delta_limit=self.__deflection_limit,
                limit_type=self.__limit_type, limit_ratio=self.__limit_ratio,
                E=self._sec("E", 210000.0), I=self._sec("Iy", 0.0),
            )
        else:
            d = Deflection(
                mode="distributed", support=self.__support, L=self.__L,
                q=self.__q, delta_limit=self.__deflection_limit,
                limit_type=self.__limit_type, limit_ratio=self.__limit_ratio,
                E=self._sec("E", 210000.0), I=self._sec("Iy", 0.0),
            )
        return d.report(with_values=with_values)

    def check_els(self, with_values: bool = False) -> FormulaCollection:
        """Aptitude au service."""
        ref = "EC3-1-1 — §7.2" if self.is_ec3 else "SIA 263 — §4.10 / SIA 260"
        fc = FormulaCollection(title="Vérifications ELS", ref=ref)
        result = self.check_deflection(with_values=with_values)
        if result is not None:
            for r in result:
                fc.add(r)
        return fc

    # ==================================================================
    #  Vérification complète
    # ==================================================================
    def full_check(self, with_values: bool = False) -> FormulaCollection:
        """ELU + Stabilité + ELS."""
        norme_label = (
            "EN 1993-1-1 / 1-5" if self.is_ec3 else "SIA 263:2013"
        )
        fc = FormulaCollection(
            title=f"Vérification complète — Poutre acier ({norme_label})",
            ref=norme_label,
        )
        for block in (
            self.check_elu(with_values=with_values),
            self.check_stability(with_values=with_values),
            self.check_els(with_values=with_values),
        ):
            for r in block:
                fc.add(r)
        return fc

    # ==================================================================
    #  Résumé
    # ==================================================================
    @staticmethod
    def _max_ratio(fc: Optional[FormulaCollection]) -> Optional[float]:
        if fc is None or len(fc) == 0:
            return None
        checks = fc.checks
        if not checks:
            return None
        return max(c.result for c in checks)

    @staticmethod
    def _governing(fc: Optional[FormulaCollection]) -> Optional[str]:
        if fc is None or len(fc) == 0:
            return None
        best, name = -1.0, None
        for fr in fc.checks:
            if fr.result is not None and fr.result >= best:
                best, name = fr.result, fr.name
        return name

    def summary(self) -> dict:
        """
        Résumé par catégorie.

        Returns
        -------
        dict
            ``{"elu": {...}, "stability": {...}, "els": {...},
               "norme": str, "is_ok": bool | None}``
        """
        result = {"norme": self.__norme}
        for category, fn in (
            ("elu", self.check_elu),
            ("stability", self.check_stability),
            ("els", self.check_els),
        ):
            fc = fn(with_values=False)
            ratio = self._max_ratio(fc)
            result[category] = {
                "governing_check": self._governing(fc),
                "max_ratio": ratio,
                "is_ok": (ratio <= 1.0) if ratio is not None else None,
            }
        evaluated = [
            result[k]["is_ok"] for k in ("elu", "stability", "els")
            if result[k]["is_ok"] is not None
        ]
        result["is_ok"] = all(evaluated) if evaluated else None
        return result

    def __repr__(self) -> str:
        return (
            f"SteelBeam(norme={self.__norme}, N={self.__N_raw / 1e3:+.1f}kN, "
            f"Vy={self.__Vy / 1e3:.1f}kN, Vz={self.__Vz / 1e3:.1f}kN, "
            f"My={self.__My / 1e6:.1f}kN·m, Mz={self.__Mz / 1e6:.1f}kN·m, "
            f"L={self.__L / 1e3:.2f}m)"
        )


# ======================================================================
#  Debug / exemple d'utilisation
# ======================================================================
if __name__ == "__main__":
    from core.sec_mat.sec_mat_i_h_u import SecMatIHU

    sep = "-" * 68

    # --- IPE 300 / S235, construit une fois par l'appelant ---
    def make_sec_mat(gamma_m0: float = 1.0, gamma_m1: float = 1.0):
        return SecMatIHU.from_properties(
            "IPE 300",
            h=300.0, b=150.0, tw=7.1, tf=10.7, r=15.0,
            A=5381.0, Avz=2567.0, Iy=8356e4, Iz=603.8e4,
            wel_y=557.1e3, wel_z=80.5e3, wpl_y=628.4e3, wpl_z=125.2e3,
            iy=124.6, iz=33.5, It=20.12e4, Iw=125.9e9,
            section_type="I",
            fy=235.0, fu=360.0,
            gamma_m0=gamma_m0, gamma_m1=gamma_m1, gamma_m2=1.25,
            section_class=1,
        )

    sm_ec3 = make_sec_mat(gamma_m0=1.0, gamma_m1=1.0)
    sm_sia = make_sec_mat(gamma_m0=1.05, gamma_m1=1.05)

    def show(beam: "SteelBeam") -> None:
        print(f"  {beam!r}")
        s = beam.summary()
        for cat in ("elu", "stability", "els"):
            d = s[cat]
            ratio = d["max_ratio"]
            ratio_txt = f"{ratio:.4f}" if ratio is not None else "   —  "
            print(
                f"    {cat.upper():10s} | {str(d['governing_check'] or '—'):28s}"
                f" | taux {ratio_txt} | ok={d['is_ok']}"
            )
        print(f"    {'GLOBAL':10s} | is_ok = {s['is_ok']}")

    # --- CAS 1 : poutre fléchie simple, EC3 vs SIA ---
    print(f"\n{sep}")
    print("  CAS 1 : Flexion + cisaillement (My=120 kN·m, Vz=180 kN, L=6 m)")
    print(sep)
    for norme, sm in (("EC3", sm_ec3), ("SIA263", sm_sia)):
        print(f"  --- {norme} ---")
        show(SteelBeam(
            sec_mat=sm, norme=norme, My=120e6, Vz=180e3, L=6000.0,
            q=12.0, section_class=1, profile_type="rolled",
        ))

    # --- CAS 2 : cisaillement élevé → interaction M+V ---
    print(f"\n{sep}")
    print("  CAS 2 : Cisaillement élevé (Vz=300 kN > 0,5·Vpl,Rd)")
    print(sep)
    for norme, sm in (("EC3", sm_ec3), ("SIA263", sm_sia)):
        print(f"  --- {norme} ---")
        show(SteelBeam(
            sec_mat=sm, norme=norme, My=100e6, Vz=300e3, L=6000.0,
            section_class=1,
        ))

    # --- CAS 3 : compression + flexion (stabilité complète) ---
    print(f"\n{sep}")
    print("  CAS 3 : Compression 250 kN + flexion 80 kN·m")
    print(sep)
    for norme, sm in (("EC3", sm_ec3), ("SIA263", sm_sia)):
        print(f"  --- {norme} ---")
        show(SteelBeam(
            sec_mat=sm, norme=norme, N=-250e3, My=80e6, Vz=60e3,
            L=6000.0, Lcr_y=6000.0, Lcr_z=3000.0, Lcr_LT=3000.0,
            section_class=1,
        ))

    # --- CAS 4 : traction + flexion ---
    print(f"\n{sep}")
    print("  CAS 4 : Traction 400 kN + flexion 60 kN·m")
    print(sep)
    for norme, sm in (("EC3", sm_ec3), ("SIA263", sm_sia)):
        print(f"  --- {norme} ---")
        show(SteelBeam(
            sec_mat=sm, norme=norme, N=400e3, My=60e6, L=6000.0,
            section_class=1,
        ))

    # --- CAS 5 : PRS à âme élancée → voilement par cisaillement ---
    print(f"\n{sep}")
    print("  CAS 5 : PRS âme élancée (hw/tw = 200) — voilement déterminant")
    print(sep)
    sm_prs = SecMatIHU.from_properties(
        "PRS 1240x300", h=1240.0, b=300.0, tw=6.0, tf=20.0, r=0.0,
        A=19200.0, Avz=7440.0, Iy=48000e4, Iz=9000e4,
        wel_y=7742e3, wel_z=600e3, wpl_y=8600e3, wpl_z=940e3,
        iy=500.0, iz=68.5, It=180e4, Iw=3.3e12,
        section_type="I", fy=355.0, fu=490.0,
        gamma_m0=1.0, gamma_m1=1.0, gamma_m2=1.25, section_class=3,
    )
    for norme in ("EC3", "SIA263"):
        print(f"  --- {norme} ---")
        show(SteelBeam(
            sec_mat=sm_prs, norme=norme, My=900e6, Vz=700e3, L=12000.0,
            section_class=3, profile_type="welded",
        ))

    # --- CAS 6 : rapport détaillé ---
    print(f"\n{sep}")
    print("  CAS 6 : Rapport détaillé complet — SIA 263")
    print(sep)
    beam = SteelBeam(
        sec_mat=sm_sia, norme="SIA263", My=120e6, Vz=180e3, L=6000.0,
        q=12.0, section_class=1, profile_type="rolled",
    )
    print(beam.full_check(with_values=True))

    print(f"\n{'=' * 68}")
    print("  FIN DES TESTS")
    print(f"{'=' * 68}")
