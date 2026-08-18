"""
Wrapper service — poteau béton armé (Str-lib, norme.EC2.element.concrete_column).

Eurocode 2 (EN 1992-1-1 §5.8) et SIA 262:2013 (§4.3.7).

Trois méthodes de second ordre : courbure nominale (défaut), rigidité
nominale, forfaitaire (Recommandations professionnelles FFB).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

STRLIB_DIR = Path(__file__).parent / "strlib_repo"
if str(STRLIB_DIR) not in sys.path:
    sys.path.insert(0, str(STRLIB_DIR))

from strlib_service import _status, _f  # noqa: E402

from norme.EC2.element.concrete_column import ConcreteColumn, METHODES  # noqa: E402


#: Classes de béton courantes → fck [MPa].
CONCRETE_CLASSES: Dict[str, float] = {
    "C20/25": 20.0, "C25/30": 25.0, "C30/37": 30.0, "C35/45": 35.0,
    "C40/50": 40.0, "C45/55": 45.0, "C50/60": 50.0,
}

#: Nuances d'armature → fyk [MPa].
REBAR_GRADES: Dict[str, float] = {
    "B500A": 500.0, "B500B": 500.0, "B500C": 500.0, "B700B": 700.0,
}


def list_methodes() -> List[Dict]:
    return [{"value": k, "label": v} for k, v in METHODES.items()]


def list_concrete_classes() -> List[str]:
    return list(CONCRETE_CLASSES.keys())


def list_rebar_grades() -> List[str]:
    return list(REBAR_GRADES.keys())


def _partial_factors_beton(norme: str) -> tuple:
    """(γc, γs) selon la norme. SIA 262 §2.3 : mêmes valeurs que l'EC2."""
    return (1.5, 1.15)


def compute_poteau_beton(
    *,
    norme: str = "EC2",
    methode: str = "courbure",
    shape: str = "rect",
    b_mm: float = 300.0,
    h_mm: float = 400.0,
    D_mm: float = 400.0,
    l0_m: float = 3.5,
    l_real_m: Optional[float] = None,
    N_ed_kn: float = 0.0,
    M0_top_knm: float = 0.0,
    M0_bot_knm: float = 0.0,
    As_cm2: float = 0.0,
    d_prime_mm: float = 50.0,
    concrete_class: str = "C25/30",
    rebar_grade: str = "B500B",
    phi_ef: float = 2.0,
    c_curvature: float = 10.0,
    c0_stiffness: float = 8.0,
    show_diagram: bool = False,
    gamma_c: Optional[float] = None,
    gamma_s: Optional[float] = None,
) -> Dict:
    norme = norme.upper().strip()
    if norme not in ("EC2", "SIA262"):
        raise ValueError(f"norme doit être 'EC2' ou 'SIA262' (reçu : '{norme}')")

    fck = CONCRETE_CLASSES.get(concrete_class.upper())
    if fck is None:
        raise ValueError(
            f"Classe de béton '{concrete_class}' inconnue. "
            f"Valeurs : {list(CONCRETE_CLASSES.keys())}"
        )
    fyk = REBAR_GRADES.get(rebar_grade.upper())
    if fyk is None:
        raise ValueError(
            f"Nuance d'armature '{rebar_grade}' inconnue. "
            f"Valeurs : {list(REBAR_GRADES.keys())}"
        )

    gc_def, gs_def = _partial_factors_beton(norme)
    gc = gc_def if gamma_c is None else float(gamma_c)
    gs = gs_def if gamma_s is None else float(gamma_s)

    col = ConcreteColumn(
        norme=norme,
        methode=methode,
        shape=shape,
        b=b_mm, h=h_mm, D=D_mm,
        l0=l0_m * 1e3,
        l_real=(l_real_m * 1e3) if l_real_m else None,
        Ned=N_ed_kn * 1e3,
        M0Ed_top=M0_top_knm * 1e6,
        M0Ed_bot=M0_bot_knm * 1e6,
        As=As_cm2 * 100.0,
        d_prime=d_prime_mm,
        fck=fck, fyk=fyk,
        gamma_c=gc, gamma_s=gs,
        phi_ef=phi_ef,
        c_curvature=c_curvature,
        c0_stiffness=c0_stiffness,
    )

    s = col.summary()
    ratio = s["max_ratio"] or 0.0
    # `is_ok` vaut None quand la collection n'a produit aucune ligne
    # marquee is_check : rien n'a ete verifie. On l'annonce au lieu de
    # conclure "OK" par defaut, ce qui masquerait un depassement.
    verdict_ok = bool(s["is_ok"])
    verdict_text = "OK" if verdict_ok else "NON VÉRIFIÉ"
    verdict_status = "ok" if verdict_ok else "error"
    if s["is_ok"] is None:
        verdict_text, verdict_status = "NON CONCLUANT", "warning"
    is_forf = (norme == "EC2" and methode == "forfaitaire")

    # ---- Résumé -----------------------------------------------------------
    results: List[Dict] = [
        {
            "label": "Élancement λ",
            "value": _f(s["lambda"], 1),
            "formula": f"λlim = {s['lambda_lim']:.1f}",
            "status": "warning" if s["second_order_required"] else "ok",
        },
        {
            "label": "Effets du 2e ordre",
            "value": "À prendre en compte" if s["second_order_required"] else "Négligeables",
            "formula": "λ > λlim ?" if s["second_order_required"] else "λ ≤ λlim",
        },
        {
            "label": "Moment du 1er ordre M0Ed",
            "value": _f(s["M0Ed"] / 1e6, 2), "unit": "kN·m",
            "formula": "M0e + NEd·ei  (≥ NEd·e0,min)",
        },
    ]
    if not is_forf:
        results.append({
            "label": "Moment de calcul MEd (2e ordre inclus)",
            "value": _f(s["MEd"] / 1e6, 2), "unit": "kN·m",
            "formula": s["methode_label"],
        })
        m_rd = col.diagram.M_rd_at_N(N_ed_kn * 1e3)
        results.append({
            "label": "Moment résistant MRd(NEd)",
            "value": _f(m_rd / 1e6, 2), "unit": "kN·m",
            "formula": "Diagramme d'interaction N-M",
        })
    else:
        forf = col._forfaitaire()  # noqa: SLF001 — accès interne assumé
        results.append({
            "label": "Effort normal résistant NRd",
            "value": _f(forf.n_rd / 1e3, 1), "unit": "kN",
            "formula": "kh·ks·α·(Ac·fcd + As·fyd)",
        })

    results.append({
        "label": "Taux de travail",
        "value": _f(ratio * 100, 1) + " %",
        "status": _status(ratio),
        "formula": s["governing_check"] or "—",
    })
    results.append({
        "label": f"Vérification {norme}",
        "value": verdict_text,
        "status": verdict_status,
        "formula": "taux ≤ 1,0",
    })

    # ---- Détail -----------------------------------------------------------
    def _rows(fc) -> List[Dict]:
        out: List[Dict] = []
        for fr in fc:
            unit, value = fr.unit, fr.result
            if unit == "N":
                unit, value = "kN", fr.result / 1e3
            elif unit == "N·mm":
                unit, value = "kN·m", fr.result / 1e6
            elif unit == "N·mm²":
                unit, value = "kN·m²", fr.result / 1e9
            disp_unit = unit if unit and unit != "-" else None
            out.append({
                "label": fr.name,
                "unit": disp_unit,
                "value": _f(value, 2 if disp_unit else 4),
                "formula": fr.formula,
            })
        return out

    norme_label = "EN 1992-1-1" if norme == "EC2" else "SIA 262:2013"
    geo_label = (
        f"{b_mm:.0f} × {h_mm:.0f} mm" if shape == "rect" else f"Ø {D_mm:.0f} mm"
    )
    donnees_rows = [
        {"label": "Norme", "value": norme_label, "unit": None, "formula": None},
        {"label": "Méthode", "value": s["methode_label"], "unit": None, "formula": None},
        {"label": "Section", "value": geo_label, "unit": None, "formula": None},
        {"label": "Béton", "value": concrete_class, "unit": None,
         "formula": f"fck = {fck:.0f} MPa ; fcd = {col.fcd:.2f} MPa"},
        {"label": "Armatures", "value": rebar_grade, "unit": None,
         "formula": f"fyk = {fyk:.0f} MPa ; fyd = {col.fyd:.1f} MPa"},
        {"label": "As total", "unit": "cm²", "value": _f(As_cm2, 2),
         "formula": f"ρ = {col.rho * 100:.2f} %"},
        {"label": "Enrobage mécanique d'", "unit": "mm", "value": _f(d_prime_mm, 0), "formula": None},
        {"label": "Longueur efficace l0", "unit": "m", "value": _f(l0_m, 2), "formula": None},
        {"label": "Coefficient de fluage φef", "value": _f(phi_ef, 2), "unit": None, "formula": None},
        {"label": "γc / γs", "value": f"{gc} / {gs}", "unit": None, "formula": None},
    ]
    efforts_rows = [
        {"label": "NEd", "unit": "kN", "value": _f(N_ed_kn, 1), "formula": "compression"},
        {"label": "M0,top", "unit": "kN·m", "value": _f(M0_top_knm, 2), "formula": None},
        {"label": "M0,bot", "unit": "kN·m", "value": _f(M0_bot_knm, 2), "formula": None},
        {"label": "M0e (équivalent)", "unit": "kN·m", "value": _f(col.M0e / 1e6, 2),
         "formula": "0,6·M02 + 0,4·M01 ≥ 0,4·M02"},
    ]

    blocks: List[Dict] = [
        {"title": "Données", "rows": donnees_rows},
        {"title": "Efforts de calcul", "rows": efforts_rows},
        {"title": "Imperfections", "rows": _rows(col.imperfections.report(with_values=True))},
        {"title": "Critère d'élancement", "rows": _rows(col.check_slenderness(with_values=True))},
        {"title": s["methode_label"], "rows": _rows(col.check_second_order(with_values=True))},
    ]
    sect = col.check_section(with_values=True)
    if sect is not None:
        blocks.append({"title": "Résistance de section (flexion composée)", "rows": _rows(sect)})

    blocks.append({
        "title": "Résumé",
        "rows": [
            {"label": "Taux de travail", "unit": "%", "value": _f(ratio * 100, 1),
             "formula": s["governing_check"]},
            {"label": f"Vérification {norme}",
             "value": verdict_text,
             "unit": None, "formula": "taux ≤ 1,0"},
        ],
    })

    out: Dict = {
        "module": "beton-poteau",
        "inputs": {
            "norme": norme, "methode": methode, "shape": shape,
            "b_mm": b_mm, "h_mm": h_mm, "D_mm": D_mm, "l0_m": l0_m,
            "N_ed_kn": N_ed_kn, "M0_top_knm": M0_top_knm,
            "M0_bot_knm": M0_bot_knm, "As_cm2": As_cm2,
            "concrete_class": concrete_class, "rebar_grade": rebar_grade,
            "phi_ef": phi_ef, "show_diagram": show_diagram,
        },
        "results": results,
        "detail": {"blocks": blocks},
    }

    # ---- Diagramme de capacité (optionnel) --------------------------------
    if show_diagram:
        out["diagram"] = {
            "curve": col.diagram_curve(n_points=60),
            "point": {
                "N": round(N_ed_kn, 2),
                "M": round(s["MEd"] / 1e6, 3),
            },
            "labels": {"x": "M [kN·m]", "y": "N [kN]"},
        }

    return out
