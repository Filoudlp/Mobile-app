"""
Wrapper service — poutre acier fléchie (Str-lib, norme.EC3.element.steel_beam).

Eurocode 3 (EN 1993-1-1 + EN 1993-1-5) et SIA 263:2013.

Vérifications (assemblages exclus) : résistance de section (N, M, V,
interactions), voilement par cisaillement de l'âme, déversement,
flambement, interaction N+M, et flèche.

Réutilise le catalogue de profilés, les nuances d'acier et les facteurs
partiels de ``strlib_service`` — une seule source pour les deux modules.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

STRLIB_DIR = Path(__file__).parent / "strlib_repo"
if str(STRLIB_DIR) not in sys.path:
    sys.path.insert(0, str(STRLIB_DIR))

from strlib_service import (  # noqa: E402
    load_profile,
    _fy_fu,
    _partial_factors,
    _status,
    _f,
)

from core.sec_mat.sec_mat_i_h_u import SecMatIHU  # noqa: E402
from norme.EC3.element.steel_beam import SteelBeam  # noqa: E402


#: Conditions d'appui proposées pour le calcul de flèche.
SUPPORTS = {
    "simply_supported": "Bi-articulée",
    "cantilever": "Console",
    "fixed_fixed": "Bi-encastrée",
    "fixed_pinned": "Encastrée-articulée",
}

#: Limites de flèche courantes (ratio L/n).
DEFLECTION_LIMITS = {
    "floor_general": 250.0,
    "floor_brittle_partitions": 300.0,
    "floor_supporting_columns": 400.0,
    "roof_general": 200.0,
    "cantilever": 150.0,
}


def list_supports() -> List[Dict]:
    return [{"value": k, "label": v} for k, v in SUPPORTS.items()]


def list_deflection_limits() -> List[Dict]:
    return [
        {"value": k, "label": f"L/{int(v)}", "ratio": v}
        for k, v in DEFLECTION_LIMITS.items()
    ]


# ---------------------------------------------------------------------------
# Main check — Poutre acier fléchie
# ---------------------------------------------------------------------------

def compute_poutre_flechie(
    *,
    norme: str = "EC3",
    profile: str,
    grade: str = "S235",
    # Efforts (kN, kN·m) — N > 0 = traction
    N_ed_kn: float = 0.0,
    My_ed_knm: float = 0.0,
    Mz_ed_knm: float = 0.0,
    Vz_ed_kn: float = 0.0,
    Vy_ed_kn: float = 0.0,
    # Géométrie (m)
    L_m: float = 6.0,
    Lcr_LT_m: Optional[float] = None,
    Lcry_m: Optional[float] = None,
    Lcrz_m: Optional[float] = None,
    # Paramètres
    section_class: int = 1,
    profile_type: str = "rolled",
    a_stiffener_m: Optional[float] = None,
    rigid_end_post: bool = True,
    psi: float = 1.0,
    C1: float = 1.0,
    # ELS
    q_els_kn_m: Optional[float] = None,
    deflection_mm: Optional[float] = None,
    support: str = "simply_supported",
    limit_type: str = "floor_general",
    limit_ratio: Optional[float] = None,
    # Avancé
    gamma_m0: Optional[float] = None,
    gamma_m1: Optional[float] = None,
) -> Dict:
    norme = norme.upper().strip()
    if norme not in ("EC3", "SIA263"):
        raise ValueError(f"norme doit être 'EC3' ou 'SIA263' (reçu : '{norme}')")

    # ---- Matériau & facteurs partiels -------------------------------------
    gM0_def, gM1_def, gM2 = _partial_factors(norme)
    gM0 = gM0_def if gamma_m0 is None else float(gamma_m0)
    gM1 = gM1_def if gamma_m1 is None else float(gamma_m1)
    fy, fu = _fy_fu(grade)

    # ---- Section ----------------------------------------------------------
    sec = load_profile(profile)
    geo = {
        "h": float(sec.get("h", 0.0)),
        "b": float(sec.get("b", 0.0)),
        "tw": float(sec.get("tw", 0.0)),
        "tf": float(sec.get("tf", 0.0)),
        "r": float(sec.get("r", 0.0)),
        "A": float(sec.get("A", 0.0)),
        "Avz": float(sec.get("Avz", 0.0)),
        "Iy": float(sec.get("Iy", 0.0)),
        "Iz": float(sec.get("Iz", 0.0)),
        "iy": float(sec.get("iy", 0.0)),
        "iz": float(sec.get("iz", 0.0)),
        "It": float(sec.get("It", 0.0)),
        "Iw": float(sec.get("Iw", 0.0)),
    }
    Wel_y = float(sec.get("Wel,y", 0.0))
    Wpl_y = float(sec.get("Wpl,y", 0.0))
    Wel_z = float(sec.get("Wel,z", 0.0))
    Wpl_z = float(sec.get("Wpl,z", 0.0))

    sec_mat = SecMatIHU.from_properties(
        profile,
        h=geo["h"], b=geo["b"], tw=geo["tw"], tf=geo["tf"], r=geo["r"],
        A=geo["A"], Avz=geo["Avz"], Iy=geo["Iy"], Iz=geo["Iz"],
        wel_y=Wel_y, wel_z=Wel_z, wpl_y=Wpl_y, wpl_z=Wpl_z,
        iy=geo["iy"], iz=geo["iz"], It=geo["It"], Iw=geo["Iw"],
        section_type="I",
        fy=fy, fu=fu, gamma_m0=gM0, gamma_m1=gM1, gamma_m2=gM2,
        section_class=section_class,
    )

    # ---- Conversions vers les unités Str-lib (N, N·mm, mm) ----------------
    L_mm = L_m * 1e3
    beam = SteelBeam(
        sec_mat=sec_mat,
        norme=norme,
        N=N_ed_kn * 1e3,
        My=My_ed_knm * 1e6,
        Mz=Mz_ed_knm * 1e6,
        Vz=Vz_ed_kn * 1e3,
        Vy=Vy_ed_kn * 1e3,
        L=L_mm,
        Lcr_LT=(Lcr_LT_m * 1e3) if Lcr_LT_m else L_mm,
        Lcr_y=(Lcry_m * 1e3) if Lcry_m else L_mm,
        Lcr_z=(Lcrz_m * 1e3) if Lcrz_m else L_mm,
        section_class=section_class,
        profile_type=profile_type,
        a_stiffener=(a_stiffener_m * 1e3) if a_stiffener_m else None,
        rigid_end_post=rigid_end_post,
        psi=psi,
        C1=C1,
        # ELS — q en kN/m → N/mm (facteur 1,0), flèche en mm
        q=(q_els_kn_m * 1.0) if q_els_kn_m else None,
        deflection=deflection_mm,
        support=support,
        limit_type=limit_type,
        limit_ratio=limit_ratio,
        gamma_m1_sia=gM1,
    )

    s = beam.summary()
    elu, stab, els = s["elu"], s["stability"], s["els"]

    ratios = [
        d["max_ratio"] for d in (elu, stab, els) if d["max_ratio"] is not None
    ]
    overall = max(ratios) if ratios else 0.0
    # `is_ok` vaut None quand la collection n'a produit aucune ligne
    # marquee is_check : rien n'a ete verifie. On l'annonce au lieu de
    # conclure "OK" par defaut, ce qui masquerait un depassement.
    verdict_ok = bool(s["is_ok"])
    verdict_text = "OK" if verdict_ok else "NON VÉRIFIÉ"
    verdict_status = "ok" if verdict_ok else "error"
    if s["is_ok"] is None:
        verdict_text, verdict_status = "NON CONCLUANT", "warning"

    def _cat(d: Dict, label: str, formula: str) -> Optional[Dict]:
        if d["max_ratio"] is None:
            return None
        return {
            "label": label,
            "value": _f(d["max_ratio"] * 100, 1) + " %",
            "status": _status(d["max_ratio"]),
            "formula": f"{formula} — {d['governing_check'] or '—'}",
        }

    # ---- Résumé -----------------------------------------------------------
    results: List[Dict] = []
    for row in (
        _cat(elu, "Taux résistance de section (ELU)", "max des vérifs §résistance"),
        _cat(stab, "Taux stabilité (déversement / flambement)", "max des vérifs §stabilité"),
        _cat(els, "Taux flèche (ELS)", "δ_net / δ_lim"),
    ):
        if row is not None:
            results.append(row)
    results.append({
        "label": "Taux global",
        "value": _f(overall * 100, 1) + " %",
        "status": _status(overall),
        "formula": "max(tous les taux)",
    })
    results.append({
        "label": f"Vérification {norme}",
        "value": verdict_text,
        "status": verdict_status,
        "formula": "tous les taux ≤ 1,0",
    })

    # ---- Détail : blocs issus des FormulaCollection Str-lib ---------------
    def _rows(fc) -> List[Dict]:
        out: List[Dict] = []
        for fr in fc:
            unit = fr.unit if fr.unit and fr.unit != "-" else None
            # Les résistances sont en N / N·mm → on affiche en kN / kN·m
            value, disp_unit = fr.result, unit
            if unit == "N":
                value, disp_unit = fr.result / 1e3, "kN"
            elif unit == "N·mm":
                value, disp_unit = fr.result / 1e6, "kN·m"
            decimals = 2 if disp_unit else 4
            out.append({
                "label": fr.name,
                "unit": disp_unit,
                "value": _f(value, decimals),
                "formula": fr.formula,
            })
        return out

    norme_label = (
        "EN 1993-1-1 / EN 1993-1-5" if norme == "EC3" else "SIA 263:2013"
    )
    donnees_rows = [
        {"label": "Norme", "value": norme_label, "unit": None, "formula": None},
        {"label": "Profilé", "value": profile, "unit": None, "formula": None},
        {"label": "Nuance", "value": grade, "unit": None,
         "formula": f"fy = {_f(fy, 0)} MPa ; fu = {_f(fu, 0)} MPa"},
        {"label": "Classe de section", "value": str(section_class), "unit": None, "formula": None},
        {"label": "Type de profilé", "value": profile_type, "unit": None,
         "formula": "laminé / soudé"},
        {"label": "Portée L", "unit": "m", "value": _f(L_m, 2), "formula": None},
        {"label": "Longueur de déversement", "unit": "m",
         "value": _f(Lcr_LT_m or L_m, 2), "formula": None},
        {"label": "γM0 / γM1 / γM2", "value": f"{gM0} / {gM1} / {gM2}",
         "unit": None, "formula": "facteurs partiels"},
    ]
    efforts_rows = [
        {"label": "N,Ed", "unit": "kN", "value": _f(N_ed_kn, 1),
         "formula": "+ traction / − compression"},
        {"label": "My,Ed", "unit": "kN·m", "value": _f(My_ed_knm, 2), "formula": None},
        {"label": "Mz,Ed", "unit": "kN·m", "value": _f(Mz_ed_knm, 2), "formula": None},
        {"label": "Vz,Ed", "unit": "kN", "value": _f(Vz_ed_kn, 1), "formula": None},
        {"label": "Vy,Ed", "unit": "kN", "value": _f(Vy_ed_kn, 1), "formula": None},
    ]

    blocks: List[Dict] = [
        {"title": "Données", "rows": donnees_rows},
        {"title": "Efforts de calcul", "rows": efforts_rows},
    ]

    elu_fc = beam.check_elu(with_values=True)
    if len(elu_fc):
        blocks.append({
            "title": "Résistance de section (ELU)", "rows": _rows(elu_fc),
        })
    stab_fc = beam.check_stability(with_values=True)
    if len(stab_fc):
        blocks.append({"title": "Stabilité", "rows": _rows(stab_fc)})
    els_fc = beam.check_els(with_values=True)
    if len(els_fc):
        blocks.append({"title": "Aptitude au service (ELS)", "rows": _rows(els_fc)})

    resume_rows = []
    for d, label in (
        (elu, "Taux résistance de section"),
        (stab, "Taux stabilité"),
        (els, "Taux flèche"),
    ):
        if d["max_ratio"] is not None:
            resume_rows.append({
                "label": label, "unit": "%",
                "value": _f(d["max_ratio"] * 100, 1),
                "formula": d["governing_check"],
            })
    resume_rows.append({
        "label": "Taux global", "unit": "%", "value": _f(overall * 100, 1),
        "formula": "max(taux)",
    })
    resume_rows.append({
        "label": f"Vérification {norme}",
        "value": verdict_text,
        "unit": None, "formula": "tous les taux ≤ 1,0",
    })
    blocks.append({"title": "Résumé", "rows": resume_rows})

    return {
        "module": "acier-poutre-flechie",
        "inputs": {
            "norme": norme,
            "profile": profile,
            "grade": grade,
            "N_ed_kn": N_ed_kn,
            "My_ed_knm": My_ed_knm,
            "Mz_ed_knm": Mz_ed_knm,
            "Vz_ed_kn": Vz_ed_kn,
            "Vy_ed_kn": Vy_ed_kn,
            "L_m": L_m,
            "Lcr_LT_m": Lcr_LT_m or L_m,
            "section_class": section_class,
            "profile_type": profile_type,
            "q_els_kn_m": q_els_kn_m,
        },
        "results": results,
        "detail": {"blocks": blocks},
    }
