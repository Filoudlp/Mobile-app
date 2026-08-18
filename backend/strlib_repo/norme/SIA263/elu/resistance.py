#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Résistance ultime des sections — SIA 263:2013, chiffre 5.1
(poutres et poteaux des classes de section 1 et 2).

Vérifications unitaires indépendantes (même principe que ``norme.EC3.elu.*``) :
chaque classe accepte soit un ``sec_mat``, soit des ``**kwargs``.

Facteurs de résistance — §4.1.3 :
    γM1 = 1,05  résistance et stabilité
    γM2 = 1,25  moyens d'assemblage et section nette
    (la SIA a renoncé à la distinction γM0/γM1 de l'EN 1993-1-1 —
    remarque explicite du §4.1.3.)

Formules couvertes :
    §5.1.2  Effort normal
        N_Rd = fy·A / γM1                                        (38)
        N_Rd = 0,9·fu·A_net / γM2   (traction, section nette)    (39)
    §5.1.3  Flexion
        M_Rd = fy·W_pl / γM1                                     (40)
    §5.1.4  Effort tranchant
        V_Rd = fy·A_v / (√3·γM1)                                 (41)
        A_v = A − 2·b·tf + (tw + 2r)·tf   (profilés I laminés)    (42a)
    §5.1.5  Flexion uniaxiale + effort tranchant
        Réduction de la participation de l'âme si V_Ed > 0,5·V_Rd (43)
    §5.1.6  Flexion + effort normal
        N_Ed/N_Rd + My_Ed/My_Rd + Mz_Ed/Mz_Rd ≤ 1,0              (44)
        My_N,Rd = My_Rd·ξ·(1−n)  ≤ My_Rd,  ξ = 1/(1−0,5a)        (45)
        Mz_N,Rd = Mz_Rd·[1 − ((n−a)/(1−a))²]   pour n > a        (46)
        Mz_N,Rd = Mz_Rd                        pour n ≤ a        (47)
        [My_Ed/My_N,Rd]^α + [Mz_Ed/Mz_N,Rd]^β ≤ 1,0  (n < 0,9)   (48)
            profilés I : α = 2 ; β = 5n  mais β ≥ 1,1
            profilés creux rect. laminés : α = β = 1,66/(1−1,33n²) ≤ 6
    §5.1.7  Flexion uniaxiale + N + V
        V_Ed ≤ 0,5·V_Rd → §5.1.6 déterminant ; sinon (44) avec M réduit.

⚠ Écarts notables vs EN 1993-1-1 (à ne pas confondre) :
    - γM1 = 1,05 partout (EC3 : γM0 = 1,00 pour la section).
    - Exposant β : plancher 1,1 en SIA (48) contre 1,0 en EC3 §6.2.9 (6).
    - La formule (44) est une interaction linéaire simple, absente de l'EC3.
"""

__all__ = [
    'GAMMA_M1', 'GAMMA_M2',
    'AxialResistanceSIA', 'BendingResistanceSIA', 'ShearResistanceSIA',
    'CombinedBendingShearSIA', 'CombinedBendingAxialSIA',
    'av_rolled_I',
]

import math
from typing import Optional, TypeVar

from core.formula import FormulaResult, FormulaCollection

SecMatSteel = TypeVar('SecMatSteel')

#: Facteur de résistance — résistance et stabilité (SIA 263 §4.1.3).
GAMMA_M1 = 1.05
#: Facteur de résistance — assemblages et section nette (SIA 263 §4.1.3).
GAMMA_M2 = 1.25


def av_rolled_I(A: float, b: float, tf: float, tw: float, r: float = 0.0) -> float:
    """
    Aire efficace de cisaillement A_v d'un profilé I laminé bisymétrique,
    effort tranchant dans le sens de l'âme — SIA 263 éq. (42a) :

        A_v = A − 2·b·tf + (tw + 2r)·tf
    """
    return A - 2.0 * b * tf + (tw + 2.0 * r) * tf


# ======================================================================
#  §5.1.2 — Effort normal
# ======================================================================

class AxialResistanceSIA:
    """
    Résistance à l'effort normal — SIA 263 §5.1.2.

    :param Ned: Effort normal de calcul [N] (valeur absolue).
    :param tension: ``True`` si traction (active la vérification de section
        nette, éq. 39).
    :param sec_mat: Objet section-matériau (fy, fu, A, gamma_m1, gamma_m2).
    :param kwargs: fy, fu, A, Anet, gamma_m1, gamma_m2.
    """

    def __init__(
        self,
        Ned: float = 0.0,
        tension: bool = False,
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__ned = abs(Ned)
        self.__tension = tension

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__fu = sec_mat.fu if sec_mat else kwargs.get("fu", 0.0)
        self.__A = sec_mat.A if sec_mat else kwargs.get("A", 0.0)
        self.__Anet = kwargs.get("Anet", self.__A)
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)
        self.__gamma_m2 = kwargs.get("gamma_m2", GAMMA_M2)

    @property
    def n_rd_gross(self) -> float:
        """N_Rd = fy·A / γM1  [N] — éq. (38)."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.__fy * self.__A / self.__gamma_m1

    @property
    def n_rd_net(self) -> Optional[float]:
        """N_Rd = 0,9·fu·A_net / γM2  [N] — éq. (39). None hors traction."""
        if not self.__tension or self.__gamma_m2 == 0:
            return None
        return 0.9 * self.__fu * self.__Anet / self.__gamma_m2

    @property
    def n_rd(self) -> float:
        """Valeur de calcul retenue — min(éq. 38 ; éq. 39)."""
        net = self.n_rd_net
        if net is None:
            return self.n_rd_gross
        return min(self.n_rd_gross, net)

    def get_n_rd_gross(self, with_values: bool = False) -> FormulaResult:
        r = self.n_rd_gross
        fv = (
            f"N_Rd = {self.__fy:.1f} × {self.__A:.1f} / {self.__gamma_m1} "
            f"= {r:.2f} N"
        ) if with_values else ""
        return FormulaResult(
            name="N_Rd (section brute)",
            formula="N_Rd = fy·A / γM1",
            formula_values=fv, result=r, unit="N",
            ref="SIA 263 — §5.1.2, éq. (38)",
        )

    def get_n_rd_net(self, with_values: bool = False) -> FormulaResult:
        r = self.n_rd_net or 0.0
        fv = (
            f"N_Rd = 0,9 × {self.__fu:.1f} × {self.__Anet:.1f} / "
            f"{self.__gamma_m2} = {r:.2f} N"
        ) if with_values else ""
        return FormulaResult(
            name="N_Rd (section nette)",
            formula="N_Rd = 0,9·fu·A_net / γM2",
            formula_values=fv, result=r, unit="N",
            ref="SIA 263 — §5.1.2, éq. (39)",
        )

    @property
    def verif(self) -> float:
        if self.n_rd == 0:
            return float('inf')
        return round(self.__ned / self.n_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"N_Ed / N_Rd = {self.__ned:.2f} / {self.n_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="N_Ed/N_Rd",
            formula="N_Ed / N_Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §5.1.2",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Résistance à l'effort normal",
            ref="SIA 263 — §5.1.2",
        )
        fc.add(self.get_n_rd_gross(with_values=with_values))
        if self.n_rd_net is not None:
            fc.add(self.get_n_rd_net(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"AxialResistanceSIA(N_Ed={self.__ned:.2f}, N_Rd={self.n_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  §5.1.3 — Flexion
# ======================================================================

class BendingResistanceSIA:
    """
    Résistance à la flexion — SIA 263 §5.1.3, éq. (40) : M_Rd = fy·W / γM1.

    W = W_pl pour les classes 1-2, W_el pour la classe 3 (§4.5.2.2).

    :param My_ed, Mz_ed: Moments de calcul [N·mm].
    :param section_class: Classe de section (1, 2 ou 3).
    """

    def __init__(
        self,
        My_ed: float = 0.0,
        Mz_ed: float = 0.0,
        section_class: int = 1,
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__my_ed = abs(My_ed)
        self.__mz_ed = abs(Mz_ed)
        self.__section_class = section_class

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__Wpl_y = sec_mat.Wpl_y if sec_mat else kwargs.get("Wpl_y", 0.0)
        self.__Wpl_z = sec_mat.Wpl_z if sec_mat else kwargs.get("Wpl_z", 0.0)
        self.__Wel_y = sec_mat.Wel_y if sec_mat else kwargs.get("Wel_y", 0.0)
        self.__Wel_z = sec_mat.Wel_z if sec_mat else kwargs.get("Wel_z", 0.0)
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)

    @property
    def W_y(self) -> float:
        """Module de section retenu selon la classe (axe y)."""
        return self.__Wpl_y if self.__section_class <= 2 else self.__Wel_y

    @property
    def W_z(self) -> float:
        """Module de section retenu selon la classe (axe z)."""
        return self.__Wpl_z if self.__section_class <= 2 else self.__Wel_z

    @property
    def my_rd(self) -> float:
        """My_Rd = fy·W_y / γM1  [N·mm]."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.__fy * self.W_y / self.__gamma_m1

    @property
    def mz_rd(self) -> float:
        """Mz_Rd = fy·W_z / γM1  [N·mm]."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.__fy * self.W_z / self.__gamma_m1

    @property
    def verif_my(self) -> float:
        if self.my_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.my_rd, 4)

    @property
    def verif_mz(self) -> float:
        if self.mz_rd == 0:
            return float('inf')
        return round(self.__mz_ed / self.mz_rd, 4)

    @property
    def verif(self) -> float:
        """Taux le plus défavorable des deux axes."""
        vals = []
        if self.__my_ed > 0:
            vals.append(self.verif_my)
        if self.__mz_ed > 0:
            vals.append(self.verif_mz)
        return max(vals) if vals else 0.0

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def _get_m_rd(self, axis: str, with_values: bool) -> FormulaResult:
        r = self.my_rd if axis == "y" else self.mz_rd
        W = self.W_y if axis == "y" else self.W_z
        kind = "pl" if self.__section_class <= 2 else "el"
        fv = (
            f"M{axis},Rd = {self.__fy:.1f} × {W:.1f} / {self.__gamma_m1} "
            f"= {r:.2f} N·mm"
        ) if with_values else ""
        return FormulaResult(
            name=f"M{axis},Rd",
            formula=f"M{axis},Rd = fy·W_{kind},{axis} / γM1",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 263 — §5.1.3, éq. (40)",
        )

    def _get_verif(self, axis: str, with_values: bool) -> FormulaResult:
        r = self.verif_my if axis == "y" else self.verif_mz
        med = self.__my_ed if axis == "y" else self.__mz_ed
        mrd = self.my_rd if axis == "y" else self.mz_rd
        fv = ""
        if with_values:
            status = "OK ✓" if r <= 1.0 else "NON VÉRIFIÉ ✗"
            fv = (
                f"M{axis},Ed / M{axis},Rd = {med:.2f} / {mrd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name=f"M{axis},Ed/M{axis},Rd",
            formula=f"M{axis},Ed / M{axis},Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §5.1.3",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Résistance à la flexion",
            ref="SIA 263 — §5.1.3",
        )
        if self.__my_ed > 0:
            fc.add(self._get_m_rd("y", with_values))
            fc.add(self._get_verif("y", with_values))
        if self.__mz_ed > 0:
            fc.add(self._get_m_rd("z", with_values))
            fc.add(self._get_verif("z", with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"BendingResistanceSIA(My_Rd={self.my_rd:.2f}, "
            f"Mz_Rd={self.mz_rd:.2f}, taux={self.verif:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  §5.1.4 — Effort tranchant
# ======================================================================

class ShearResistanceSIA:
    """
    Résistance à l'effort tranchant — SIA 263 §5.1.4, éq. (41) :
    V_Rd = fy·A_v / (√3·γM1).

    :param Ved: Effort tranchant de calcul [N].
    :param axis: "z" (âme) ou "y" (semelles).
    :param Av: Aire efficace de cisaillement [mm²]. Si absente et un
        ``sec_mat`` est fourni, prise dans ``Av_z`` / ``Av_y``.
    """

    def __init__(
        self,
        Ved: float = 0.0,
        axis: str = "z",
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__ved = abs(Ved)
        self.__axis = axis.lower()

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)

        av_kw = kwargs.get("Av")
        if av_kw is not None:
            self.__Av = av_kw
        elif sec_mat is not None:
            self.__Av = sec_mat.Av_y if self.__axis == "y" else sec_mat.Av_z
        else:
            self.__Av = kwargs.get(
                "Av_y" if self.__axis == "y" else "Av_z", 0.0
            )

    @property
    def av(self) -> float:
        """Aire efficace de cisaillement [mm²]."""
        return self.__Av

    @property
    def v_rd(self) -> float:
        """V_Rd = fy·A_v / (√3·γM1)  [N] — éq. (41)."""
        if self.__gamma_m1 == 0:
            return 0.0
        return self.__fy * self.__Av / (math.sqrt(3) * self.__gamma_m1)

    def get_v_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.v_rd
        fv = (
            f"V_Rd = {self.__fy:.1f} × {self.__Av:.1f} / (√3 × "
            f"{self.__gamma_m1}) = {r:.2f} N"
        ) if with_values else ""
        return FormulaResult(
            name="V_Rd",
            formula="V_Rd = fy·A_v / (√3·γM1)",
            formula_values=fv, result=r, unit="N",
            ref="SIA 263 — §5.1.4, éq. (41)",
        )

    @property
    def verif(self) -> float:
        if self.v_rd == 0:
            return float('inf')
        return round(self.__ved / self.v_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    @property
    def is_high_shear(self) -> bool:
        """True si V_Ed > 0,5·V_Rd — déclenche la réduction §5.1.5."""
        return self.__ved > 0.5 * self.v_rd

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"V_Ed / V_Rd = {self.__ved:.2f} / {self.v_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="V_Ed/V_Rd",
            formula="V_Ed / V_Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §5.1.4",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title=f"Résistance à l'effort tranchant (axe {self.__axis})",
            ref="SIA 263 — §5.1.4",
        )
        fc.add(self.get_v_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"ShearResistanceSIA(V_Ed={self.__ved:.2f}, V_Rd={self.v_rd:.2f}, "
            f"taux={self.verif:.4f}, ok={self.is_ok}, "
            f"high_shear={self.is_high_shear})"
        )


# ======================================================================
#  §5.1.5 — Flexion uniaxiale + effort tranchant
# ======================================================================

class CombinedBendingShearSIA:
    """
    Flexion uniaxiale + effort tranchant — SIA 263 §5.1.5.

    Si V_Ed > 0,5·V_Rd, la participation de l'âme à la résistance à la
    flexion est réduite. Pour les poutres en double té bisymétriques,
    éq. (43) :

        My_V,Rd = [ b·tf·(h − tf) + (hw²·tw/4)·(1 − (V_Ed/V_Rd)²) ] · fy/γM1

    Le terme b·tf·(h − tf) est la contribution des semelles (intacte) et
    hw²·tw/4 celle de l'âme (réduite par le cisaillement).

    :param My_ed: Moment de calcul My,Ed [N·mm].
    :param Ved: Effort tranchant de calcul [N].
    :param V_Rd: Résistance au cisaillement [N] (§5.1.4).
    """

    def __init__(
        self,
        My_ed: float = 0.0,
        Ved: float = 0.0,
        V_Rd: float = 0.0,
        My_Rd: float = 0.0,
        section_class: int = 1,
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__my_ed = abs(My_ed)
        self.__ved = abs(Ved)
        self.__v_rd = V_Rd
        self.__section_class = section_class

        self.__fy = sec_mat.fy if sec_mat else kwargs.get("fy", 0.0)
        self.__h = sec_mat.h if sec_mat else kwargs.get("h", 0.0)
        self.__b = sec_mat.b if sec_mat else kwargs.get("b", 0.0)
        self.__tf = sec_mat.tf if sec_mat else kwargs.get("tf", 0.0)
        self.__tw = sec_mat.tw if sec_mat else kwargs.get("tw", 0.0)
        self.__gamma_m1 = kwargs.get("gamma_m1", GAMMA_M1)

        if My_Rd:
            self.__my_rd_full = My_Rd
        else:
            W = (
                (sec_mat.Wpl_y if sec_mat else kwargs.get("Wpl_y", 0.0))
                if section_class <= 2
                else (sec_mat.Wel_y if sec_mat else kwargs.get("Wel_y", 0.0))
            )
            self.__my_rd_full = (
                self.__fy * W / self.__gamma_m1 if self.__gamma_m1 else 0.0
            )

    @property
    def hw(self) -> float:
        """Hauteur de l'âme hw = h − 2·tf [mm]."""
        return max(self.__h - 2.0 * self.__tf, 0.0)

    @property
    def is_reduction_required(self) -> bool:
        """True si V_Ed > 0,5·V_Rd — §5.1.5."""
        return self.__v_rd > 0 and self.__ved > 0.5 * self.__v_rd

    @property
    def my_v_rd(self) -> float:
        """My_V,Rd — moment résistant réduit par le cisaillement [N·mm]."""
        if not self.is_reduction_required:
            return self.__my_rd_full
        if self.__gamma_m1 == 0 or self.__section_class > 2:
            return self.__my_rd_full
        ratio = self.__ved / self.__v_rd
        flange = self.__b * self.__tf * (self.__h - self.__tf)
        web = self.hw ** 2 * self.__tw / 4.0 * (1.0 - ratio ** 2)
        val = (flange + web) * self.__fy / self.__gamma_m1
        return max(min(val, self.__my_rd_full), 0.0)

    def get_my_v_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.my_v_rd
        fv = ""
        if with_values:
            if not self.is_reduction_required:
                fv = (
                    f"V_Ed = {self.__ved:.2f} ≤ 0,5·V_Rd = "
                    f"{0.5 * self.__v_rd:.2f} → pas de réduction, "
                    f"My_V,Rd = My_Rd = {r:.2f} N·mm"
                )
            else:
                ratio = self.__ved / self.__v_rd
                flange = self.__b * self.__tf * (self.__h - self.__tf)
                web = self.hw ** 2 * self.__tw / 4.0 * (1.0 - ratio ** 2)
                fv = (
                    f"My_V,Rd = [{flange:.1f} + {web:.1f}] × {self.__fy:.1f} / "
                    f"{self.__gamma_m1} = {r:.2f} N·mm "
                    f"(V_Ed/V_Rd = {ratio:.4f})"
                )
        return FormulaResult(
            name="My_V,Rd",
            formula="My_V,Rd = [b·tf·(h−tf) + hw²·tw/4·(1−(V_Ed/V_Rd)²)]·fy/γM1",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 263 — §5.1.5, éq. (43)",
        )

    @property
    def verif(self) -> float:
        if self.my_v_rd == 0:
            return float('inf')
        return round(self.__my_ed / self.my_v_rd, 4)

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def get_verif(self, with_values: bool = False) -> FormulaResult:
        r = self.verif
        fv = ""
        if with_values:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            fv = (
                f"My_Ed / My_V,Rd = {self.__my_ed:.2f} / {self.my_v_rd:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="My_Ed/My_V,Rd",
            formula="My_Ed / My_V,Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §5.1.5",
            is_check=True, limit=1.0,
        )

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Flexion + effort tranchant",
            ref="SIA 263 — §5.1.5",
        )
        fc.add(self.get_my_v_rd(with_values=with_values))
        fc.add(self.get_verif(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"CombinedBendingShearSIA(réduction={self.is_reduction_required}, "
            f"My_V,Rd={self.my_v_rd:.2f}, taux={self.verif:.4f}, "
            f"ok={self.is_ok})"
        )


# ======================================================================
#  §5.1.6 — Flexion + effort normal
# ======================================================================

class CombinedBendingAxialSIA:
    """
    Flexion + effort normal — SIA 263 §5.1.6.

    Fournit à la fois l'interaction linéaire (44) — toujours applicable et
    conservative — et l'interaction plastique (45)-(48) pour les sections
    en double té bisymétriques de classe 1-2.

    :param Ned, My_ed, Mz_ed: Efforts de calcul [N] / [N·mm].
    :param N_Rd, My_Rd, Mz_Rd: Résistances de section (§5.1.2 / §5.1.3).
    :param section_type: "I"/"H" ou "RHS" (profilés creux rect. laminés).
    """

    def __init__(
        self,
        Ned: float = 0.0,
        My_ed: float = 0.0,
        Mz_ed: float = 0.0,
        N_Rd: float = 0.0,
        My_Rd: float = 0.0,
        Mz_Rd: float = 0.0,
        section_class: int = 1,
        section_type: str = "I",
        sec_mat: Optional[SecMatSteel] = None,
        **kwargs,
    ) -> None:
        self.__ned = abs(Ned)
        self.__my_ed = abs(My_ed)
        self.__mz_ed = abs(Mz_ed)
        self.__n_rd = N_Rd
        self.__my_rd = My_Rd
        self.__mz_rd = Mz_Rd
        self.__section_class = section_class
        self.__section_type = section_type.upper()

        self.__A = sec_mat.A if sec_mat else kwargs.get("A", 0.0)
        self.__b = sec_mat.b if sec_mat else kwargs.get("b", 0.0)
        self.__tf = sec_mat.tf if sec_mat else kwargs.get("tf", 0.0)

    # --- Paramètres n, a, ξ ------------------------------------------
    @property
    def n(self) -> float:
        """n = N_Ed / N_Rd."""
        if self.__n_rd == 0:
            return float('inf')
        return self.__ned / self.__n_rd

    @property
    def a(self) -> float:
        """a = (A − 2·b·tf)/A  ≤ 0,5 — part de l'âme."""
        if self.__A == 0:
            return 0.0
        return min(max((self.__A - 2.0 * self.__b * self.__tf) / self.__A, 0.0), 0.5)

    @property
    def xi(self) -> float:
        """ξ = 1/(1 − 0,5·a)."""
        denom = 1.0 - 0.5 * self.a
        return 1.0 / denom if denom else 0.0

    # --- Moments réduits (45)-(47) -----------------------------------
    @property
    def my_n_rd(self) -> float:
        """My_N,Rd = My_Rd·ξ·(1−n)  ≤ My_Rd — éq. (45)."""
        if self.__section_class > 2 or self.__section_type not in ("I", "H"):
            return self.__my_rd
        val = self.__my_rd * self.xi * (1.0 - self.n)
        return max(min(val, self.__my_rd), 0.0)

    @property
    def mz_n_rd(self) -> float:
        """Mz_N,Rd — éq. (46)/(47)."""
        if self.__section_class > 2 or self.__section_type not in ("I", "H"):
            return self.__mz_rd
        if self.n <= self.a:
            return self.__mz_rd
        denom = 1.0 - self.a
        if denom == 0:
            return 0.0
        return max(self.__mz_rd * (1.0 - ((self.n - self.a) / denom) ** 2), 0.0)

    # --- Exposants (48) ----------------------------------------------
    @property
    def alpha(self) -> float:
        """α — éq. (48). Profilés I : 2 ; creux rect. : 1,66/(1−1,33n²) ≤ 6."""
        if self.__section_type in ("I", "H"):
            return 2.0
        denom = 1.0 - 1.33 * self.n ** 2
        if denom <= 0:
            return 6.0
        return min(1.66 / denom, 6.0)

    @property
    def beta(self) -> float:
        """β — éq. (48). Profilés I : 5n mais ≥ 1,1 (SIA, ≠ EC3 qui a ≥ 1,0)."""
        if self.__section_type in ("I", "H"):
            return max(5.0 * self.n, 1.1)
        return self.alpha

    # --- Vérification linéaire (44) ----------------------------------
    @property
    def verif_linear(self) -> float:
        """N_Ed/N_Rd + My_Ed/My_Rd + Mz_Ed/Mz_Rd ≤ 1,0 — éq. (44)."""
        total = 0.0
        if self.__n_rd:
            total += self.__ned / self.__n_rd
        if self.__my_rd:
            total += self.__my_ed / self.__my_rd
        if self.__mz_rd:
            total += self.__mz_ed / self.__mz_rd
        return round(total, 4)

    def get_verif_linear(self, with_values: bool = False) -> FormulaResult:
        r = self.verif_linear
        fv = ""
        if with_values:
            status = "OK ✓" if r <= 1.0 else "NON VÉRIFIÉ ✗"
            t_n = self.__ned / self.__n_rd if self.__n_rd else 0.0
            t_y = self.__my_ed / self.__my_rd if self.__my_rd else 0.0
            t_z = self.__mz_ed / self.__mz_rd if self.__mz_rd else 0.0
            fv = (
                f"{t_n:.4f} + {t_y:.4f} + {t_z:.4f} = {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="Interaction linéaire",
            formula="N_Ed/N_Rd + My_Ed/My_Rd + Mz_Ed/Mz_Rd ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §5.1.6.1, éq. (44)",
            is_check=True, limit=1.0,
        )

    # --- Vérification plastique (48) ---------------------------------
    @property
    def is_plastic_applicable(self) -> bool:
        """L'éq. (48) n'est valable que pour n < 0,9 et classes 1-2."""
        return self.__section_class <= 2 and self.n < 0.9

    @property
    def verif_plastic(self) -> float:
        """[My_Ed/My_N,Rd]^α + [Mz_Ed/Mz_N,Rd]^β ≤ 1,0 — éq. (48)."""
        ry = (
            self.__my_ed / self.my_n_rd if self.my_n_rd
            else (float('inf') if self.__my_ed else 0.0)
        )
        rz = (
            self.__mz_ed / self.mz_n_rd if self.mz_n_rd
            else (float('inf') if self.__mz_ed else 0.0)
        )
        if math.isinf(ry) or math.isinf(rz):
            return float('inf')
        return round(ry ** self.alpha + rz ** self.beta, 4)

    def get_verif_plastic(self, with_values: bool = False) -> FormulaResult:
        r = self.verif_plastic
        fv = ""
        if with_values:
            status = "OK ✓" if r <= 1.0 else "NON VÉRIFIÉ ✗"
            ry = self.__my_ed / self.my_n_rd if self.my_n_rd else 0.0
            rz = self.__mz_ed / self.mz_n_rd if self.mz_n_rd else 0.0
            fv = (
                f"[{ry:.4f}]^{self.alpha:.2f} + [{rz:.4f}]^{self.beta:.2f} "
                f"= {r:.4f} ≤ 1,0 → {status}"
            )
        return FormulaResult(
            name="Interaction plastique M+N",
            formula="[My_Ed/My_N,Rd]^α + [Mz_Ed/Mz_N,Rd]^β ≤ 1,0",
            formula_values=fv, result=r, unit="-",
            ref="SIA 263 — §5.1.6.4, éq. (48)",
            is_check=True, limit=1.0,
        )

    def get_n(self, with_values: bool = False) -> FormulaResult:
        r = self.n
        fv = (
            f"n = {self.__ned:.2f} / {self.__n_rd:.2f} = {r:.4f}"
        ) if with_values else ""
        return FormulaResult(
            name="n", formula="n = N_Ed / N_Rd",
            formula_values=fv, result=round(r, 4), unit="-",
            ref="SIA 263 — §5.1.6.2",
        )

    def get_my_n_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.my_n_rd
        fv = (
            f"My_N,Rd = {self.__my_rd:.2f} × {self.xi:.4f} × "
            f"(1 − {self.n:.4f}) = {r:.2f} N·mm  (≤ My_Rd)"
        ) if with_values else ""
        return FormulaResult(
            name="My_N,Rd",
            formula="My_N,Rd = My_Rd·ξ·(1−n) ≤ My_Rd,  ξ = 1/(1−0,5a)",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 263 — §5.1.6.2, éq. (45)",
        )

    def get_mz_n_rd(self, with_values: bool = False) -> FormulaResult:
        r = self.mz_n_rd
        fv = ""
        if with_values:
            if self.n <= self.a:
                fv = (
                    f"n = {self.n:.4f} ≤ a = {self.a:.4f} → "
                    f"Mz_N,Rd = Mz_Rd = {r:.2f} N·mm"
                )
            else:
                fv = (
                    f"Mz_N,Rd = {self.__mz_rd:.2f} × [1 − (({self.n:.4f} − "
                    f"{self.a:.4f})/(1 − {self.a:.4f}))²] = {r:.2f} N·mm"
                )
        return FormulaResult(
            name="Mz_N,Rd",
            formula="Mz_N,Rd = Mz_Rd·[1 − ((n−a)/(1−a))²]  pour n > a",
            formula_values=fv, result=r, unit="N·mm",
            ref="SIA 263 — §5.1.6.2, éq. (46)-(47)",
        )

    @property
    def verif(self) -> float:
        """Taux retenu : plastique si applicable, sinon linéaire."""
        if self.is_plastic_applicable and (self.__my_ed or self.__mz_ed):
            return self.verif_plastic
        return self.verif_linear

    @property
    def is_ok(self) -> bool:
        return self.verif <= 1.0

    def report(self, with_values: bool = True) -> FormulaCollection:
        fc = FormulaCollection(
            title="Flexion + effort normal",
            ref="SIA 263 — §5.1.6",
        )
        fc.add(self.get_n(with_values=with_values))
        fc.add(self.get_verif_linear(with_values=with_values))
        if self.is_plastic_applicable and (self.__my_ed or self.__mz_ed):
            if self.__my_ed:
                fc.add(self.get_my_n_rd(with_values=with_values))
            if self.__mz_ed:
                fc.add(self.get_mz_n_rd(with_values=with_values))
            fc.add(self.get_verif_plastic(with_values=with_values))
        return fc

    def __repr__(self) -> str:
        return (
            f"CombinedBendingAxialSIA(n={self.n:.4f}, "
            f"linéaire={self.verif_linear:.4f}, "
            f"plastique={self.verif_plastic:.4f}, ok={self.is_ok})"
        )


# ======================================================================
#  Debug / exemple
# ======================================================================
if __name__ == "__main__":
    sep = "-" * 60
    # IPE 300 / S235
    ipe = dict(
        fy=235.0, fu=360.0, A=5381.0, h=300.0, b=150.0, tf=10.7, tw=7.1,
        Wpl_y=628.4e3, Wpl_z=125.2e3, Wel_y=557.1e3, Wel_z=80.5e3,
    )
    Av = av_rolled_I(A=ipe["A"], b=ipe["b"], tf=ipe["tf"], tw=ipe["tw"], r=15.0)

    print(f"\n{sep}\n  A_v (éq. 42a) = {Av:.1f} mm²\n{sep}")

    print(f"\n{sep}\n  §5.1.2 — Effort normal (traction 500 kN)\n{sep}")
    n = AxialResistanceSIA(Ned=500e3, tension=True, Anet=4800.0, **ipe)
    print(f"  {n!r}")

    print(f"\n{sep}\n  §5.1.3 — Flexion My = 100 kN·m\n{sep}")
    m = BendingResistanceSIA(My_ed=100e6, section_class=1, **ipe)
    print(f"  {m!r}")

    print(f"\n{sep}\n  §5.1.4 — Cisaillement V = 200 kN\n{sep}")
    v = ShearResistanceSIA(Ved=200e3, Av=Av, **ipe)
    print(f"  {v!r}")

    print(f"\n{sep}\n  §5.1.5 — Flexion + cisaillement élevé (V = 250 kN)\n{sep}")
    v2 = ShearResistanceSIA(Ved=250e3, Av=Av, **ipe)
    bs = CombinedBendingShearSIA(
        My_ed=100e6, Ved=250e3, V_Rd=v2.v_rd, section_class=1, **ipe,
    )
    print(f"  {bs!r}")
    print(bs.report(with_values=True))

    print(f"\n{sep}\n  §5.1.6 — Flexion + effort normal\n{sep}")
    ba = CombinedBendingAxialSIA(
        Ned=300e3, My_ed=80e6, Mz_ed=5e6,
        N_Rd=n.n_rd_gross, My_Rd=m.my_rd, Mz_Rd=m.mz_rd,
        section_class=1, section_type="I", **ipe,
    )
    print(f"  {ba!r}")
    print(ba.report(with_values=True))

    print(f"\n{'=' * 60}\n  FIN DES TESTS\n{'=' * 60}")
