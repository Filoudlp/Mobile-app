"""
Wrapper service that calls the user-supplied Str-lib (in ./strlib_repo).

Vérification poteau acier EC3 / SIA 263 — compression + flexion biaxiale +
cisaillement + flambement + déversement + interaction M-N (méthode 2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

STRLIB_DIR = Path(__file__).parent / "strlib_repo"
if str(STRLIB_DIR) not in sys.path:
    sys.path.insert(0, str(STRLIB_DIR))

from core.sec_mat.sec_mat_i_h_u import SecMatIHU  # noqa: E402
from norme.EC3.buckling.buckling_curves import (  # noqa: E402
    get_buckling_curve,
    get_imperfection_factor,
    get_lt_buckling_curve,
)
from norme.EC3.buckling.lateral_torsional import LateralTorsionalBuckling  # noqa: E402
from norme.EC3.elu.shear import Shear  # noqa: E402
from norme.EC3.element.steel_column import SteelColumn  # noqa: E402
from utility.lookupinjson import get_section  # noqa: E402


# ---------------------------------------------------------------------------
# Profile catalogue
# ---------------------------------------------------------------------------
_PROFILE_FAMILIES: Dict[str, str] = {
    "IPE": "IPE.json",
    "IPN": "IPN.json",
    "HE": "HE.json",
    "HEA": "HE.json",
    "HEB": "HE.json",
    "HEM": "HE.json",
    "HD": "HD.json",
    "HL": "HL.json",
    "HP": "HP.json",
}


def _resolve_profile_name(name: str) -> Tuple[str, str]:
    cleaned = name.strip().upper().replace("  ", " ")
    family = cleaned.split()[0]
    if family in {"HEA", "HEB", "HEM"}:
        suffix = family[-1]
        size = cleaned.split()[1]
        return _PROFILE_FAMILIES["HE"], f"HE {size} {suffix}"
    if family not in _PROFILE_FAMILIES:
        raise ValueError(f"Famille de profilé inconnue : {family}")
    return _PROFILE_FAMILIES[family], cleaned


_PROFILE_CACHE: Dict[str, dict] = {}


def load_profile(name: str) -> dict:
    if name in _PROFILE_CACHE:
        return _PROFILE_CACHE[name]
    json_file, lookup = _resolve_profile_name(name)
    with open(STRLIB_DIR / "ressource" / json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    row = get_section(data, lookup)
    _PROFILE_CACHE[name] = row
    return row


def list_profiles(family: str) -> List[str]:
    json_file = _PROFILE_FAMILIES.get(family.upper())
    if json_file is None:
        return []
    with open(STRLIB_DIR / "ressource" / json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [s["Name"] for s in data["sections"] if s.get("Name") not in (None, "unit")]


# ---------------------------------------------------------------------------
# Steel grades — (fy, fu) per EN 10025 for t ≤ 40 mm.
# ---------------------------------------------------------------------------
_STEEL_GRADES: Dict[str, Tuple[float, float]] = {
    "S235": (235.0, 360.0),
    "S275": (275.0, 430.0),
    "S355": (355.0, 490.0),
    "S460": (440.0, 550.0),
}


def _fy_fu(grade: str) -> Tuple[float, float]:
    return _STEEL_GRADES.get(grade.upper().replace(" ", ""), _STEEL_GRADES["S235"])


# ---------------------------------------------------------------------------
# Norm-specific partial factors
# ---------------------------------------------------------------------------
def _partial_factors(norme: str) -> Tuple[float, float, float]:
    """Return (γM0, γM1, γM2) per norm defaults."""
    if norme.upper() == "SIA263":
        return (1.05, 1.05, 1.25)
    # EC3 (default) — NF EN 1993-1-1/NA
    return (1.00, 1.00, 1.25)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status(ratio: float) -> str:
    if ratio < 0.85:
        return "ok"
    if ratio < 1.0:
        return "warning"
    return "error"


def _f(val: float, decimals: int = 2) -> str:
    if val == 0:
        return f"{0.0:.{decimals}f}"
    return f"{val:.{decimals}f}"


# ---------------------------------------------------------------------------
# Main check — Poteau acier
# ---------------------------------------------------------------------------

def compute_poteau_comprime(
    *,
    # main inputs
    norme: str = "EC3",
    profile: str,
    grade: str,
    N_ed_kn: float = 0.0,
    My_ed_knm: float = 0.0,
    Mz_ed_knm: float = 0.0,
    Vz_ed_kn: float = 0.0,
    Vy_ed_kn: float = 0.0,
    Lcry_m: float = 3.0,
    Lcrz_m: float = 3.0,
    LcrLT_m: float = 3.0,
    psi_y: float = 1.0,
    psi_z: float = 1.0,
    # advanced (rarely changed)
    gamma_m0: Optional[float] = None,
    gamma_m1: Optional[float] = None,
    C1: float = 1.0,
    Cmy: float = 0.9,
    Cmz: float = 0.9,
    section_class: int = 1,
    interaction_method: int = 2,
    curve_y_override: Optional[str] = None,
    curve_z_override: Optional[str] = None,
    curve_LT_override: Optional[str] = None,
    length_m: Optional[float] = None,
    Ky: Optional[float] = None,
    Kz: Optional[float] = None,
    # legacy compatibility with older frontend
    height_m: Optional[float] = None,
    axial_kn: Optional[float] = None,
    lx_m: Optional[float] = None,
    ly_m: Optional[float] = None,
) -> Dict:
    # legacy input shim
    if axial_kn is not None and N_ed_kn == 0.0:
        N_ed_kn = axial_kn
    if height_m is not None:
        Lcry_m = lx_m if lx_m is not None else height_m
        Lcrz_m = ly_m if ly_m is not None else height_m
        if LcrLT_m == 3.0:
            LcrLT_m = height_m

    # ---- Material & partial factors ---------------------------------------
    gM0_def, gM1_def, gM2 = _partial_factors(norme)
    gM0 = gM0_def if gamma_m0 is None else float(gamma_m0)
    gM1 = gM1_def if gamma_m1 is None else float(gamma_m1)

    fy, fu = _fy_fu(grade)
    E = 210_000.0
    G = 80_770.0

    # ---- Section ----------------------------------------------------------
    sec = load_profile(profile)
    A = float(sec.get("A", 0.0))
    Avz = float(sec.get("Avz", 0.0))
    Iy = float(sec.get("Iy", 0.0))
    Iz = float(sec.get("Iz", 0.0))
    iy = float(sec.get("iy", 0.0))
    iz = float(sec.get("iz", 0.0))
    It = float(sec.get("It", 0.0))
    Iw = float(sec.get("Iw", 0.0))
    Wel_y = float(sec.get("Wel,y", 0.0))
    Wpl_y = float(sec.get("Wpl,y", 0.0))
    Wel_z = float(sec.get("Wel,z", 0.0))
    Wpl_z = float(sec.get("Wpl,z", 0.0))
    h = float(sec.get("h", 0.0))
    b = float(sec.get("b", 0.0))
    tf = float(sec.get("tf", 0.0))
    tw = float(sec.get("tw", 0.0))
    r = float(sec.get("r", 0.0))

    # Section modulus depending on class (1/2 → plastic, 3 → elastic)
    Wy = Wpl_y if section_class in (1, 2) else Wel_y
    Wz = Wpl_z if section_class in (1, 2) else Wel_z

    # ---- Section resistances (§6.2) ---------------------------------------
    NRk = A * fy  # N
    My_Rk = Wy * fy  # N·mm
    Mz_Rk = Wz * fy  # N·mm

    # ---- Design forces (convert to N and N·mm) ----------------------------
    N_ed = N_ed_kn * 1e3
    My_ed = My_ed_knm * 1e6
    Mz_ed = Mz_ed_knm * 1e6
    Vz_ed = Vz_ed_kn * 1e3
    Vy_ed = Vy_ed_kn * 1e3

    Lcr_y = Lcry_m * 1e3
    Lcr_z = Lcrz_m * 1e3
    Lcr_LT = LcrLT_m * 1e3

    # ---- Sec_mat — construit une fois ici (le serveur a déjà chargé le
    # profilé JSON + résolu fy/fu/γM), puis réutilisé pour toutes les
    # vérifications. SteelColumn ne fait que le consommer.
    sec_mat = SecMatIHU.from_properties(
        profile,
        h=h, b=b, tw=tw, tf=tf, r=r,
        A=A, Avz=Avz, Iy=Iy, Iz=Iz,
        wel_y=Wel_y, wel_z=Wel_z, wpl_y=Wpl_y, wpl_z=Wpl_z,
        iy=iy, iz=iz, It=It, Iw=Iw,
        section_type="H",
        fy=fy, fu=fu, gamma_m0=gM0, gamma_m1=gM1, gamma_m2=gM2,
        section_class=section_class,
    )
    Avy = sec_mat.Av_y

    # ---- Str-lib SteelColumn — orchestrateur des vérifications unitaires --
    # (norme.EC3.element.steel_column) : compression, cisaillement (y, z),
    # flambement (y, z), déversement et interaction N+M sont tous calculés
    # par les classes de la librairie, pas réimplémentés ici.
    col = SteelColumn(
        N=N_ed, My=My_ed, Mz=Mz_ed, Vy=Vy_ed, Vz=Vz_ed,
        Lcr_y=Lcr_y, Lcr_z=Lcr_z, Lcr_LT=Lcr_LT,
        sec_mat=sec_mat, section_class=section_class,
        curve_y=curve_y_override, curve_z=curve_z_override,
        curve_LT=curve_LT_override,
        method_LT="rolled", interaction_method=interaction_method,
        Cmy=Cmy, Cmz=Cmz, CmLT=Cmy, C1=C1,
    )

    # ---- Compression §6.2.4 ------------------------------------------------
    # (None si N,Ed = 0 — cas limite ; Nc,Rd reste affiché comme capacité)
    comp_fc = col.check_compression(with_values=False)
    if comp_fc is not None:
        Nc_Rd = comp_fc.get("Nc,Rd").result
        ratio_Nc = comp_fc.get("Ned/Nc,Rd").result
    else:
        Nc_Rd = A * fy / gM0
        ratio_Nc = 0.0

    # ---- Flambement §6.3.1 (flexion axe y et z) ----------------------------
    fb = col._flexural_buckling()
    if fb is not None:
        Ncr_y, Ncr_z = fb.ncr_y, fb.ncr_z
        lambda_y, lambda_z = fb.lambda_bar_y, fb.lambda_bar_z
        chi_y, chi_z = fb.chi_y, fb.chi_z
        Nb_y_Rd, Nb_z_Rd = fb.nb_rd_y, fb.nb_rd_z
        Nb_Rd_min = fb.nb_rd
        critical_axis = "y" if Nb_y_Rd <= Nb_z_Rd else "z"
        ratio_Nb = fb.verif
    else:
        Ncr_y = Ncr_z = lambda_y = lambda_z = 0.0
        chi_y = chi_z = 1.0
        Nb_y_Rd = Nb_z_Rd = Nb_Rd_min = A * fy / gM1
        critical_axis = "y"
        ratio_Nb = 0.0

    curve_y = curve_y_override or get_buckling_curve("H", "rolled", "y", h, b, tf)
    curve_z = curve_z_override or get_buckling_curve("H", "rolled", "z", h, b, tf)
    alpha_y = get_imperfection_factor(curve_y)
    alpha_z = get_imperfection_factor(curve_z)
    phi_y = 0.5 * (1.0 + alpha_y * (lambda_y - 0.2) + lambda_y**2)
    phi_z = 0.5 * (1.0 + alpha_z * (lambda_z - 0.2) + lambda_z**2)

    # ---- Déversement §6.3.2 -------------------------------------------------
    # Toujours calculé (même à My,Ed = 0) pour afficher la capacité Mb,y,Rd.
    ltb = LateralTorsionalBuckling(
        Med_y=My_ed if My_ed > 0 else 1.0,
        mat=sec_mat, sec=sec_mat,
        L=Lcr_LT, Lcr_LT=Lcr_LT,
        method="rolled", curve_LT=curve_LT_override,
        section_class=section_class, C1=C1,
    )
    Mcr = ltb.mcr
    lambda_LT = ltb.lambda_bar_LT
    curve_LT = curve_LT_override or get_lt_buckling_curve("H", h, b, "rolled")
    alpha_LT = get_imperfection_factor(curve_LT)
    phi_LT = 0.5 * (1.0 + alpha_LT * (lambda_LT - 0.2) + lambda_LT**2) if lambda_LT > 0 else 0.0
    chi_LT = ltb.chi_LT
    Mb_y_Rd = ltb.mb_rd
    My_Rd = My_Rk / gM0
    Mz_Rd = Mz_Rk / gM0

    # ---- Cisaillement §6.2.6 -------------------------------------------------
    # Toujours calculé (même à V,Ed = 0) pour afficher la capacité Vpl,Rd.
    shear_z = Shear(Ved=Vz_ed, axis="z", sec_mat=sec_mat)
    shear_y = Shear(Ved=Vy_ed, axis="y", sec_mat=sec_mat)
    Vpl_z_Rd = shear_z.vpl_rd
    ratio_Vz = shear_z.verif
    Vpl_y_Rd = shear_y.vpl_rd
    ratio_Vy = shear_y.verif

    # ---- Interaction M-N — §6.3.3 -------------------------------------------
    inm_fc = col.check_interaction_NM(with_values=False)
    if inm_fc is not None:
        kyy = inm_fc.get(f"kyy (Annexe {'A' if interaction_method == 1 else 'B'})").result
        kyz = inm_fc.get(f"kyz (Annexe {'A' if interaction_method == 1 else 'B'})").result
        kzy = inm_fc.get(f"kzy (Annexe {'A' if interaction_method == 1 else 'B'})").result
        kzz = inm_fc.get(f"kzz (Annexe {'A' if interaction_method == 1 else 'B'})").result
        eq_631 = inm_fc.get("Éq.(6.61)").result
        eq_632 = inm_fc.get("Éq.(6.62)").result
    else:
        kyy = kyz = kzy = kzz = 0.0
        eq_631 = eq_632 = 0.0
    ratio_MN = max(eq_631, eq_632)

    # ---- Overall verdict ---------------------------------------------------
    overall = max(ratio_Nc, ratio_Nb, ratio_MN, ratio_Vz, ratio_Vy)
    verdict_ok = overall < 1.0

    # ---- Summary (Résumé) --------------------------------------------------
    results: List[Dict] = [
        {"label": "Compression Nc,Rd", "value": _f(Nc_Rd / 1e3, 1), "unit": "kN", "formula": "A·fy/γM0"},
        {"label": "Taux compression pure", "value": _f(ratio_Nc * 100, 1) + " %", "status": _status(ratio_Nc), "formula": "N,Ed / Nc,Rd"},
        {"label": f"Nb,Rd (axe {critical_axis})", "value": _f(Nb_Rd_min / 1e3, 1), "unit": "kN", "formula": "χ · A·fy/γM1"},
        {"label": "Taux flambement", "value": _f(ratio_Nb * 100, 1) + " %", "status": _status(ratio_Nb), "formula": "N,Ed / Nb,Rd"},
        {"label": "Mb,y,Rd (déversement)", "value": _f(Mb_y_Rd / 1e6, 2), "unit": "kN·m", "formula": "χLT · Wy·fy/γM1"},
        {"label": "Taux interaction M-N (éq. 6.61)", "value": _f(eq_631 * 100, 1) + " %", "status": _status(eq_631), "formula": "N/Nb,y + kyy·My/Mb,y + kyz·Mz/Mz,Rd"},
        {"label": "Taux interaction M-N (éq. 6.62)", "value": _f(eq_632 * 100, 1) + " %", "status": _status(eq_632), "formula": "N/Nb,z + kzy·My/Mb,y + kzz·Mz/Mz,Rd"},
        {"label": "Taux cisaillement Vz", "value": _f(ratio_Vz * 100, 1) + " %", "status": _status(ratio_Vz), "formula": "Vz,Ed / Vpl,z,Rd"},
        {"label": "Taux cisaillement Vy", "value": _f(ratio_Vy * 100, 1) + " %", "status": _status(ratio_Vy), "formula": "Vy,Ed / Vpl,y,Rd"},
        {"label": f"Vérification {norme}", "value": "OK" if verdict_ok else "NON VÉRIFIÉ", "status": "ok" if verdict_ok else "error", "formula": "max(taux) < 1.0"},
    ]

    # ---- Detail (blocs comme dans l'Excel) ---------------------------------
    detail: Dict = {
        "blocks": [
            {
                "title": "Données",
                "rows": [
                    {"label": "Norme", "value": norme, "formula": None},
                    {"label": "Nuance", "value": grade, "formula": None},
                    {"label": "fy", "unit": "MPa", "value": _f(fy, 0), "formula": "Limite d'élasticité"},
                    {"label": "fu", "unit": "MPa", "value": _f(fu, 0), "formula": "Résistance à la rupture"},
                    {"label": "E", "unit": "MPa", "value": _f(E, 0), "formula": "Module d'Young acier"},
                    {"label": "G", "unit": "MPa", "value": _f(G, 0), "formula": "Module de cisaillement"},
                    {"label": "γM0", "value": _f(gM0, 2), "formula": None},
                    {"label": "γM1", "value": _f(gM1, 2), "formula": None},
                    {"label": "γM2", "value": _f(gM2, 2), "formula": None},
                ],
            },
            {
                "title": "Section & classification",
                "rows": [
                    {"label": "Profilé", "value": profile, "formula": None},
                    {"label": "Classe", "value": str(section_class), "formula": "Tableau 5.2"},
                    {"label": "A", "unit": "mm²", "value": _f(A, 0), "formula": "Aire brute"},
                    {"label": "Av,z", "unit": "mm²", "value": _f(Avz, 0), "formula": "Aire cisaillement axe z"},
                    {"label": "Av,y", "unit": "mm²", "value": _f(Avy, 0), "formula": "A - Av,z (simplifié)"},
                    {"label": "Iy", "unit": "mm⁴", "value": _f(Iy, 0), "formula": "Inertie axe fort"},
                    {"label": "Iz", "unit": "mm⁴", "value": _f(Iz, 0), "formula": "Inertie axe faible"},
                    {"label": "iy", "unit": "mm", "value": _f(iy, 1), "formula": "Rayon giration y"},
                    {"label": "iz", "unit": "mm", "value": _f(iz, 1), "formula": "Rayon giration z"},
                    {"label": "It", "unit": "mm⁴", "value": _f(It, 0), "formula": "Torsion (Saint-Venant)"},
                    {"label": "Iw", "unit": "mm⁶", "value": _f(Iw, 0), "formula": "Gauchissement"},
                    {"label": "Wpl,y", "unit": "mm³", "value": _f(Wpl_y, 0), "formula": "Module plastique y"},
                    {"label": "Wpl,z", "unit": "mm³", "value": _f(Wpl_z, 0), "formula": "Module plastique z"},
                    {"label": "Wy retenu", "unit": "mm³", "value": _f(Wy, 0), "formula": "Wpl,y (cl.1/2) ou Wel,y (cl.3)"},
                ],
            },
            {
                "title": "Résistances de section",
                "rows": [
                    {"label": "NRk", "unit": "kN", "value": _f(NRk / 1e3, 1), "formula": "A · fy"},
                    {"label": "My,Rk", "unit": "kN·m", "value": _f(My_Rk / 1e6, 2), "formula": "Wy · fy"},
                    {"label": "Mz,Rk", "unit": "kN·m", "value": _f(Mz_Rk / 1e6, 2), "formula": "Wz · fy"},
                    {"label": "Nc,Rd", "unit": "kN", "value": _f(Nc_Rd / 1e3, 1), "formula": "A·fy/γM0"},
                    {"label": "My,Rd", "unit": "kN·m", "value": _f(My_Rd / 1e6, 2), "formula": "Wy·fy/γM0"},
                    {"label": "Mz,Rd", "unit": "kN·m", "value": _f(Mz_Rd / 1e6, 2), "formula": "Wz·fy/γM0"},
                    {"label": "Vpl,z,Rd", "unit": "kN", "value": _f(Vpl_z_Rd / 1e3, 1), "formula": "Av,z·(fy/√3)/γM0"},
                    {"label": "Vpl,y,Rd", "unit": "kN", "value": _f(Vpl_y_Rd / 1e3, 1), "formula": "Av,y·(fy/√3)/γM0"},
                ],
            },
            {
                "title": "Efforts",
                "rows": [
                    {"label": "N,Ed", "unit": "kN", "value": _f(N_ed / 1e3, 1), "formula": "Compression"},
                    {"label": "My,Ed", "unit": "kN·m", "value": _f(My_ed / 1e6, 2), "formula": "Flexion axe y"},
                    {"label": "Mz,Ed", "unit": "kN·m", "value": _f(Mz_ed / 1e6, 2), "formula": "Flexion axe z"},
                    {"label": "Vz,Ed", "unit": "kN", "value": _f(Vz_ed / 1e3, 1), "formula": "Cisaillement // z"},
                    {"label": "Vy,Ed", "unit": "kN", "value": _f(Vy_ed / 1e3, 1), "formula": "Cisaillement // y"},
                    {"label": "Longueur barre L", "unit": "m", "value": _f(length_m if length_m is not None else Lcry_m, 2), "formula": "Longueur physique"},
                    {"label": "Ky", "value": _f(Ky if Ky is not None else 1.0, 2), "formula": "Lcr,y = Ky · L"},
                    {"label": "Kz", "value": _f(Kz if Kz is not None else 1.0, 2), "formula": "Lcr,z = Kz · L"},
                    {"label": "ψy", "value": _f(psi_y, 2), "formula": "Diagramme moment y (Mmin/Mmax)"},
                    {"label": "ψz", "value": _f(psi_z, 2), "formula": "Diagramme moment z"},
                ],
            },
            {
                "title": "Compression — §6.2.4",
                "rows": [
                    {"label": "Nc,Rd", "unit": "kN", "value": _f(Nc_Rd / 1e3, 1), "formula": "A·fy/γM0"},
                    {"label": "N,Ed / Nc,Rd", "unit": "%", "value": _f(ratio_Nc * 100, 1), "formula": "Vérification"},
                ],
            },
            {
                "title": "Flambement — §6.3.1",
                "rows": [
                    {"label": "Lcr,y", "unit": "m", "value": _f(Lcry_m, 2), "formula": None},
                    {"label": "Lcr,z", "unit": "m", "value": _f(Lcrz_m, 2), "formula": None},
                ],
                "subBlocks": [
                    {
                        "title": "Axe y",
                        "rows": [
                            {"label": "Ncr,y", "unit": "kN", "value": _f(Ncr_y / 1e3, 1), "formula": "π²·E·Iy/Lcr,y²"},
                            {"label": "λ̄y", "value": _f(lambda_y, 3), "formula": "√(A·fy/Ncr,y)"},
                            {"label": "Courbe", "value": curve_y, "formula": "Tab. 6.2"},
                            {"label": "αy", "value": _f(alpha_y, 2), "formula": "Tab. 6.1"},
                            {"label": "Φy", "value": _f(phi_y, 3), "formula": "0.5[1+α(λ̄-0.2)+λ̄²]"},
                            {"label": "χy", "value": _f(chi_y, 3), "formula": "1/(Φ+√(Φ²-λ̄²)) ≤ 1"},
                            {"label": "Nb,y,Rd", "unit": "kN", "value": _f(Nb_y_Rd / 1e3, 1), "formula": "χy·A·fy/γM1"},
                        ],
                    },
                    {
                        "title": "Axe z",
                        "rows": [
                            {"label": "Ncr,z", "unit": "kN", "value": _f(Ncr_z / 1e3, 1), "formula": "π²·E·Iz/Lcr,z²"},
                            {"label": "λ̄z", "value": _f(lambda_z, 3), "formula": "√(A·fy/Ncr,z)"},
                            {"label": "Courbe", "value": curve_z, "formula": "Tab. 6.2"},
                            {"label": "αz", "value": _f(alpha_z, 2), "formula": "Tab. 6.1"},
                            {"label": "Φz", "value": _f(phi_z, 3), "formula": "0.5[1+α(λ̄-0.2)+λ̄²]"},
                            {"label": "χz", "value": _f(chi_z, 3), "formula": "1/(Φ+√(Φ²-λ̄²)) ≤ 1"},
                            {"label": "Nb,z,Rd", "unit": "kN", "value": _f(Nb_z_Rd / 1e3, 1), "formula": "χz·A·fy/γM1"},
                        ],
                    },
                ],
            },
            {
                "title": "Déversement — §6.3.2",
                "rows": [
                    {"label": "Lcr,LT", "unit": "m", "value": _f(LcrLT_m, 2), "formula": None},
                    {"label": "C1", "value": _f(C1, 2), "formula": "Coefficient diagramme moment"},
                    {"label": "Mcr", "unit": "kN·m", "value": _f(Mcr / 1e6, 2), "formula": "C1·(π²EIz/L²)·√(Iw/Iz+L²·GIt/(π²EIz))"},
                    {"label": "λ̄LT", "value": _f(lambda_LT, 3), "formula": "√(Wy·fy/Mcr)"},
                    {"label": "Courbe LT", "value": curve_LT, "formula": "Tab. 6.5 (méthode profilés laminés)"},
                    {"label": "αLT", "value": _f(alpha_LT, 2), "formula": "Tab. 6.3"},
                    {"label": "ΦLT", "value": _f(phi_LT, 3), "formula": "0.5[1+αLT(λ̄LT-0.2)+λ̄LT²]"},
                    {"label": "χLT", "value": _f(chi_LT, 3), "formula": "1/(ΦLT+√(ΦLT²-λ̄LT²)) ≤ 1"},
                    {"label": "Mb,y,Rd", "unit": "kN·m", "value": _f(Mb_y_Rd / 1e6, 2), "formula": "χLT·Wy·fy/γM1"},
                ],
            },
            {
                "title": "Cisaillement — §6.2.6",
                "rows": [
                    {"label": "Vpl,z,Rd", "unit": "kN", "value": _f(Vpl_z_Rd / 1e3, 1), "formula": "Av,z·(fy/√3)/γM0"},
                    {"label": "Vz,Ed / Vpl,z,Rd", "unit": "%", "value": _f(ratio_Vz * 100, 1), "formula": "Vérification"},
                    {"label": "Vpl,y,Rd", "unit": "kN", "value": _f(Vpl_y_Rd / 1e3, 1), "formula": "Av,y·(fy/√3)/γM0"},
                    {"label": "Vy,Ed / Vpl,y,Rd", "unit": "%", "value": _f(ratio_Vy * 100, 1), "formula": "Vérification"},
                ],
            },
            {
                "title": "Interaction M-N — §6.3.3 (Méthode 2, Annexe B)",
                "rows": [
                    {"label": "Cmy", "value": _f(Cmy, 3), "formula": "Coefficient moment équivalent y"},
                    {"label": "Cmz", "value": _f(Cmz, 3), "formula": "Coefficient moment équivalent z"},
                    {"label": "kyy", "value": _f(kyy, 3), "formula": "Cmy·(1+(λ̄y-0.2)·N/Nb,y,Rd)"},
                    {"label": "kyz", "value": _f(kyz, 3), "formula": "0.6·kzz"},
                    {"label": "kzy", "value": _f(kzy, 3), "formula": "0.6·kyy"},
                    {"label": "kzz", "value": _f(kzz, 3), "formula": "Cmz·(1+(2λ̄z-0.6)·N/Nb,z,Rd)"},
                    {"label": "Éq. 6.61", "unit": "%", "value": _f(eq_631 * 100, 1), "formula": "N/Nb,y + kyy·My/Mb,y + kyz·Mz/Mz,Rd"},
                    {"label": "Éq. 6.62", "unit": "%", "value": _f(eq_632 * 100, 1), "formula": "N/Nb,z + kzy·My/Mb,y + kzz·Mz/Mz,Rd"},
                ],
            },
            {
                "title": "Résumé",
                "rows": [
                    {"label": "Taux compression", "unit": "%", "value": _f(ratio_Nc * 100, 1), "formula": None},
                    {"label": "Taux flambement", "unit": "%", "value": _f(ratio_Nb * 100, 1), "formula": None},
                    {"label": "Taux interaction M-N", "unit": "%", "value": _f(ratio_MN * 100, 1), "formula": None},
                    {"label": "Taux cisaillement Vz", "unit": "%", "value": _f(ratio_Vz * 100, 1), "formula": None},
                    {"label": "Taux cisaillement Vy", "unit": "%", "value": _f(ratio_Vy * 100, 1), "formula": None},
                    {"label": "Taux global", "unit": "%", "value": _f(overall * 100, 1), "formula": "max(taux)"},
                    {"label": f"Vérification {norme}", "value": "OK" if verdict_ok else "NON VÉRIFIÉ", "formula": "max < 1.0"},
                ],
            },
        ],
    }

    return {
        "module": "acier-poteau-comprime",
        "inputs": {
            "norme": norme,
            "profile": profile,
            "grade": grade,
            "N_ed_kn": N_ed_kn,
            "My_ed_knm": My_ed_knm,
            "Mz_ed_knm": Mz_ed_knm,
            "Vz_ed_kn": Vz_ed_kn,
            "Vy_ed_kn": Vy_ed_kn,
            "Lcry_m": Lcry_m,
            "Lcrz_m": Lcrz_m,
            "LcrLT_m": LcrLT_m,
            "psi_y": psi_y,
            "psi_z": psi_z,
            "gamma_m0": gM0,
            "gamma_m1": gM1,
            "C1": C1,
            "Cmy": Cmy,
            "Cmz": Cmz,
            "section_class": section_class,
        },
        "results": results,
        "detail": detail,
    }
