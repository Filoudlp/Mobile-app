"""
Wrapper service — spectre de réponse sismique (Str-lib, norme.EC8.seisme).

France (NF EN 1998-1 + NA) et Suisse (SIA 261:2020, chapitre 16).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

STRLIB_DIR = Path(__file__).parent / "strlib_repo"
if str(STRLIB_DIR) not in sys.path:
    sys.path.insert(0, str(STRLIB_DIR))

from norme.EC8.element.seismic_load import SeismicLoad  # noqa: E402
from norme.EC8.seisme.response_spectrum import (  # noqa: E402
    CH_ZONES,
    CH_SOIL_CLASSES,
    CH_IMPORTANCE_FACTORS,
    FR_ZONES,
    FR_SOIL_CLASSES,
    FR_IMPORTANCE_FACTORS,
)


# ---------------------------------------------------------------------------
# Helpers pour le frontend (listes déroulantes)
# ---------------------------------------------------------------------------

def list_zones(country: str) -> List[str]:
    return list(FR_ZONES.keys()) if country.upper() == "FR" else list(CH_ZONES.keys())


def list_soil_classes(country: str) -> List[str]:
    return list(FR_SOIL_CLASSES.keys()) if country.upper() == "FR" else list(CH_SOIL_CLASSES.keys())


def list_importance_classes(country: str) -> List[str]:
    return list(FR_IMPORTANCE_FACTORS.keys()) if country.upper() == "FR" else list(CH_IMPORTANCE_FACTORS.keys())


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def _f(val, decimals: int = 3) -> str:
    if val is None:
        return "—"
    return f"{val:.{decimals}f}"


# ---------------------------------------------------------------------------
# Main check — Spectre de réponse sismique
# ---------------------------------------------------------------------------

def compute_seisme(
    *,
    country: str,
    zone: str,
    soil_class: str,
    q: float = 1.5,
    importance_class: Optional[str] = None,
    xi_percent: float = 5.0,
    t_point: Optional[float] = None,
) -> Dict:
    country = country.upper().strip()
    is_fr = country == "FR"

    seisme = SeismicLoad(
        country=country,
        zone=zone,
        soil_class=soil_class,
        q=q,
        importance_class=importance_class,
        xi_percent=xi_percent,
    )

    s = seisme.summary()

    elastic_pts = seisme.spectrum_points(kind="elastic", n=60, T_max=4.0)
    design_pts = seisme.spectrum_points(kind="design", n=60, T_max=4.0)

    accel_label = "ag (= γI·agR)" if is_fr else "agd"
    accel_value = s["ag"] if is_fr else s["agd"]
    accel_formula = "Zonage réglementaire (agR) × γI" if is_fr else "Zone sismique (Annexe F)"

    # ---- Résumé --------------------------------------------------------
    results: List[Dict] = [
        {"label": f"Accélération de calcul {accel_label}", "value": _f(accel_value, 3 if is_fr else 2), "unit": "m/s²", "formula": accel_formula},
        {"label": "Paramètre de sol S", "value": _f(s["S"], 2), "formula": "Tableau 3.3" if is_fr else "Tableau 24"},
        {"label": "Se,max (plateau élastique)", "value": _f(s["Se_max"], 3), "unit": "m/s²", "formula": "ag·S·2,5·η" if is_fr else "agd·S·2,5·η"},
        {
            "label": "Sd,max (plateau de dimensionnement)",
            "value": _f(s["Sd_max"], 3),
            "unit": "m/s²",
            "status": "ok",
            "formula": "ag·S·2,5/q" if is_fr else "agd·γf·S·2,5/q",
        },
    ]
    if not is_fr:
        results.append({
            "label": "Déplacement de calcul du sol ugd",
            "value": _f(s["ugd"], 4),
            "unit": "m",
            "formula": "0,05·γf·agd·S·TC·TD",
        })

    point = None
    if t_point is not None:
        point = seisme.point_at(t_point)
        results.append({
            "label": f"Point lu sur la courbe — T = {t_point:.2f} s",
            "value": f"Se={point['Se']:.3f} / Sd={point['Sd']:.3f}",
            "unit": "m/s²",
            "formula": "Se(T) / Sd(T)",
        })

    # ---- Detail ----------------------------------------------------------
    donnees_rows = [
        {"label": "Norme", "value": "NF EN 1998-1" if is_fr else "SIA 261:2020 (chap. 16)", "formula": None},
        {"label": "Zone sismique", "value": zone, "formula": "Zonage réglementaire" if is_fr else "Annexe F (carte)"},
        {"label": "Classe de sol" if is_fr else "Classe de terrain de fondation", "value": soil_class, "formula": "Tableau 3.1" if is_fr else "Tableau 24"},
        {"label": "Catégorie d'importance" if is_fr else "Classe d'ouvrage", "value": s["importance_class"], "formula": None},
        {"label": "Coefficient de comportement q", "value": _f(q, 2), "formula": None},
        {"label": "Amortissement visqueux ξ", "unit": "%", "value": _f(xi_percent, 1), "formula": None},
    ]

    spectre_rows = [
        {"label": accel_label, "unit": "m/s²", "value": _f(accel_value, 3 if is_fr else 2), "formula": accel_formula},
        {"label": "S", "value": _f(s["S"], 2), "formula": "Tableau 3.3" if is_fr else "Tableau 24"},
        {"label": "TB", "unit": "s", "value": _f(s["TB"], 2), "formula": "Tableau 3.3" if is_fr else "Tableau 24"},
        {"label": "TC", "unit": "s", "value": _f(s["TC"], 2), "formula": "Tableau 3.3" if is_fr else "Tableau 24"},
        {"label": "TD", "unit": "s", "value": _f(s["TD"], 2), "formula": "Tableau 3.3" if is_fr else "Tableau 24"},
        {"label": "η (correction d'amortissement)", "value": _f(s["eta"], 3), "formula": "√(10/(5+ξ)) ≥ 0,55"},
    ]
    if is_fr:
        spectre_rows.append({"label": "γI (facteur d'importance)", "value": _f(s["gamma_I"], 2), "formula": None})
    else:
        spectre_rows.append({"label": "γf (facteur d'importance)", "value": _f(s["gamma_f"], 2), "formula": "Tableau 25"})

    calc_rows = [
        {"label": "Se,max", "unit": "m/s²", "value": _f(s["Se_max"], 3), "formula": "ag·S·2,5·η" if is_fr else "agd·S·2,5·η"},
        {"label": "Sd,max", "unit": "m/s²", "value": _f(s["Sd_max"], 3), "formula": "ag·S·2,5/q" if is_fr else "agd·γf·S·2,5/q"},
    ]
    if not is_fr:
        calc_rows.append({"label": "ugd", "unit": "m", "value": _f(s["ugd"], 4), "formula": "0,05·γf·agd·S·TC·TD"})
    if point is not None:
        calc_rows.append({"label": f"Se(T={t_point:.2f}s)", "unit": "m/s²", "value": _f(point["Se"], 4), "formula": None})
        calc_rows.append({"label": f"Sd(T={t_point:.2f}s)", "unit": "m/s²", "value": _f(point["Sd"], 4), "formula": None})

    detail: Dict = {
        "blocks": [
            {"title": "Données", "rows": donnees_rows},
            {"title": "Paramètres du spectre", "rows": spectre_rows},
            {"title": "Valeurs de calcul", "rows": calc_rows},
        ],
    }

    return {
        "module": "seisme-spectre",
        "inputs": {
            "country": country,
            "zone": zone,
            "soil_class": soil_class,
            "q": q,
            "importance_class": s["importance_class"],
            "xi_percent": xi_percent,
            "t_point": t_point,
        },
        "results": results,
        "detail": detail,
        "spectrum": {
            "T": [round(t, 4) for t, _ in elastic_pts],
            "Se": [round(v, 5) for _, v in elastic_pts],
            "Sd": [round(v, 5) for _, v in design_pts],
            "point": point,
        },
    }
