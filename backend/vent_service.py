"""
Wrapper service — pression du vent sur murs verticaux (Str-lib, norme.EC1.vent).

France (NF EN 1991-1-4/NA) et Suisse (SIA 261:2020).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

STRLIB_DIR = Path(__file__).parent / "strlib_repo"
if str(STRLIB_DIR) not in sys.path:
    sys.path.insert(0, str(STRLIB_DIR))

from norme.EC1.element.wind_load import WindLoad  # noqa: E402
from norme.EC1.vent.base_velocity import FR_VB0, load_fr_region_table  # noqa: E402
from norme.EC1.vent.wind_profile import FR_TERRAIN_CATEGORIES, CH_TERRAIN_CATEGORIES  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers pour le frontend (listes déroulantes)
# ---------------------------------------------------------------------------

def list_fr_departments() -> List[Dict]:
    """Liste des départements français avec leur(s) région(s) — pour un
    sélecteur département -> région côté frontend."""
    data = load_fr_region_table()
    out = []
    for code, dept in data["departements"].items():
        out.append({
            "code": code,
            "nom": dept["nom"],
            "regions": dept["regions"],
            "default": dept["default"],
        })
    return sorted(out, key=lambda d: d["code"])


def list_fr_regions() -> List[str]:
    return sorted(FR_VB0.keys())


def list_terrain_categories(country: str) -> List[str]:
    return list(FR_TERRAIN_CATEGORIES.keys()) if country.upper() == "FR" else list(CH_TERRAIN_CATEGORIES.keys())


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def _f(val, decimals: int = 2) -> str:
    if val is None:
        return "—"
    return f"{val:.{decimals}f}"


# ---------------------------------------------------------------------------
# Main check — Pression du vent sur murs verticaux
# ---------------------------------------------------------------------------

def compute_vent(
    *,
    country: str,
    h_m: float,
    b_m: float,
    d_m: float,
    terrain_category: str,
    cscd: float = 1.0,
    # France
    region: Optional[str] = None,
    departement: Optional[str] = None,
    cdir: float = 1.0,
    cseason: float = 1.0,
    # Suisse
    qp0_kn_m2: Optional[float] = None,
) -> Dict:
    country = country.upper().strip()

    # Si un département est fourni sans région explicite, on prend sa région
    # par défaut (le frontend peut proposer les régions alternatives du
    # département via /api/vent/departements).
    if country == "FR" and region is None and departement is not None:
        data = load_fr_region_table()
        dept = data["departements"].get(departement.upper())
        if dept is None:
            raise ValueError(f"Département '{departement}' inconnu.")
        region = str(dept["default"])

    wind = WindLoad(
        country=country,
        h=h_m,
        b=b_m,
        d=d_m,
        terrain_category=terrain_category,
        cscd=cscd,
        region=region,
        cdir=cdir,
        cseason=cseason,
        qp0=qp0_kn_m2,
    )

    s = wind.summary()
    qp = s["qp"]
    ze = s["ze"]
    h_d = s["h_d"]
    pressures = s["pressures"]

    zone_labels = {
        "A": "Zone A (mur latéral, bord au vent)",
        "B": "Zone B (mur latéral, intermédiaire)",
        "C": "Zone C (mur latéral, reste)",
        "D": "Zone D (face au vent)",
        "E": "Zone E (face sous le vent)",
    }

    # ---- Résumé --------------------------------------------------------
    results: List[Dict] = [
        {"label": "Pression dynamique de pointe qp(ze)", "value": _f(qp, 4), "unit": "kN/m²", "formula": "ze = h"},
        {"label": "Rapport h/d", "value": _f(h_d, 2), "formula": None},
    ]
    for zone in ("D", "E", "A", "B", "C"):
        if zone in pressures:
            results.append({
                "label": f"we — {zone_labels[zone]}",
                "value": f"{pressures[zone]:+.3f}",
                "unit": "kN/m²",
                "formula": "cscd·qp(ze)·cpe,10",
            })
    we_max = s["we_max"]
    results.append({
        "label": "Pression de calcul retenue (enveloppe)",
        "value": f"{we_max:+.3f}",
        "unit": "kN/m²",
        "status": "ok",
        "formula": "max(|we,zone|)",
    })

    # ---- Detail ----------------------------------------------------------
    donnees_rows = [
        {"label": "Norme", "value": "NF EN 1991-1-4/NA" if country == "FR" else "SIA 261:2020", "formula": None},
        {"label": "Hauteur h", "unit": "m", "value": _f(h_m, 2), "formula": None},
        {"label": "Largeur au vent b", "unit": "m", "value": _f(b_m, 2), "formula": None},
        {"label": "Profondeur d", "unit": "m", "value": _f(d_m, 2), "formula": None},
        {"label": "Catégorie de terrain", "value": terrain_category, "formula": "Tableau 4.1(NA)" if country == "FR" else "Tableau 4"},
    ]
    if country == "FR":
        donnees_rows.insert(1, {"label": "Région climatique", "value": str(region), "formula": "Annexe nationale"})
    else:
        donnees_rows.insert(1, {"label": "qp0 (Annexe E)", "unit": "kN/m²", "value": _f(qp0_kn_m2, 2), "formula": "SIA 261, Annexe E (carte)"})

    vitesse_rows = []
    if country == "FR":
        vb = wind.velocity.vb
        qb = wind.velocity.qb
        vitesse_rows = [
            {"label": "vb,0", "unit": "m/s", "value": _f(wind.velocity.vb0, 1), "formula": "Tableau 4.2(NA)"},
            {"label": "vb", "unit": "m/s", "value": _f(vb, 2), "formula": "cdir·cseason·vb,0"},
            {"label": "qb", "unit": "kN/m²", "value": _f(qb, 4), "formula": "0,5·ρ·vb²"},
        ]
    else:
        vitesse_rows = [
            {"label": "qp0", "unit": "kN/m²", "value": _f(wind.velocity.qp0, 2), "formula": "Annexe E (carte)"},
        ]
    vitesse_rows.append({"label": "qp(ze)", "unit": "kN/m²", "value": _f(qp, 4), "formula": "ze = h (simplifié)"})

    pressure_rows = []
    for zone in ("A", "B", "C", "D", "E"):
        if zone in pressures:
            cpe10, cpe1 = wind.walls.cpe(zone)
            pressure_rows.append({
                "label": f"we — {zone_labels[zone]}",
                "unit": "kN/m²",
                "value": f"{pressures[zone]:+.3f}",
                "formula": f"cpe,10 = {cpe10:+.2f}",
            })

    detail: Dict = {
        "blocks": [
            {"title": "Données", "rows": donnees_rows},
            {"title": "Vitesse / pression dynamique", "rows": vitesse_rows},
            {
                "title": "Géométrie — Tableau 7.1",
                "rows": [
                    {"label": "h/d", "value": _f(h_d, 3), "formula": None},
                    {"label": "e = min(b, 2h)", "unit": "m", "value": _f(wind.walls.e, 2), "formula": None},
                    {"label": "Zone C existe", "value": "Oui" if wind.walls.has_zone_c else "Non (e ≥ d)", "formula": None},
                ],
            },
            {"title": "Pressions extérieures we par zone", "rows": pressure_rows},
            {
                "title": "Résumé",
                "rows": [
                    {"label": "Pression de calcul retenue (enveloppe)", "unit": "kN/m²", "value": f"{we_max:+.3f}", "formula": "max(|we,zone|)"},
                ],
            },
        ],
    }

    return {
        "module": "vent-facade",
        "inputs": {
            "country": country,
            "h_m": h_m,
            "b_m": b_m,
            "d_m": d_m,
            "terrain_category": terrain_category,
            "region": region,
            "qp0_kn_m2": qp0_kn_m2,
            "cscd": cscd,
        },
        "results": results,
        "detail": detail,
    }
