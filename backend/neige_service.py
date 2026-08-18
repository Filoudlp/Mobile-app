"""
Wrapper service — charges de neige sur toiture (Str-lib, norme.EC1.neige).

France (NF EN 1991-1-3/NA) et Suisse (SIA 261:2020).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

STRLIB_DIR = Path(__file__).parent / "strlib_repo"
if str(STRLIB_DIR) not in sys.path:
    sys.path.insert(0, str(STRLIB_DIR))

from norme.EC1.element.snow_load import SnowLoad  # noqa: E402
from norme.EC1.neige.ground_snow_load import (  # noqa: E402
    FR_ZONES,
    load_fr_zone_table,
    zones_for_department,
)
from norme.EC1.neige.roof_snow_load import CE_TABLE_FR, CE_TABLE_CH  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers pour le frontend (listes déroulantes)
# ---------------------------------------------------------------------------

def list_fr_departments() -> List[Dict]:
    """Liste des départements français avec leur(s) zone(s) — pour un
    sélecteur département -> zone côté frontend."""
    data = load_fr_zone_table()
    out = []
    for code, dept in data["departements"].items():
        out.append({
            "code": code,
            "nom": dept["nom"],
            "zones": dept["zones"],
            "default": dept["default"],
        })
    return sorted(out, key=lambda d: d["code"])


def list_fr_zones() -> List[str]:
    return sorted(FR_ZONES.keys())


def list_exposure_options(country: str) -> List[str]:
    return list(CE_TABLE_FR.keys()) if country.upper() == "FR" else list(CE_TABLE_CH.keys())


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def _f(val: float, decimals: int = 2) -> str:
    if val is None:
        return "—"
    return f"{val:.{decimals}f}"


# ---------------------------------------------------------------------------
# Main check — Charge de neige sur toiture
# ---------------------------------------------------------------------------

def compute_neige(
    *,
    country: str,
    angle_deg: float,
    exposure: str = "normal",
    Ct: float = 1.0,
    # France
    zone: Optional[str] = None,
    departement: Optional[str] = None,
    altitude_m: Optional[float] = None,
    # Suisse
    h0_m: Optional[float] = None,
) -> Dict:
    country = country.upper().strip()

    # Si un département est fourni sans zone explicite, on prend sa zone
    # par défaut (le frontend peut proposer les zones alternatives du
    # département via /api/neige/departements).
    if country == "FR" and zone is None and departement is not None:
        data = load_fr_zone_table()
        dept = data["departements"].get(departement.upper())
        if dept is None:
            raise ValueError(f"Département '{departement}' inconnu.")
        zone = dept["default"]

    snow = SnowLoad(
        country=country,
        angle=angle_deg,
        exposure=exposure,
        Ct=Ct,
        zone=zone,
        altitude=altitude_m,
        h0=h0_m,
    )

    s = snow.summary()
    sk = s["sk"]
    mu1 = s["mu1"]
    mu2 = s["mu2"]
    s_design = s["s_design"]

    sans_fc = snow.check_sans_accumulation(with_values=False)
    s_sans = sans_fc.get("s").result

    avec_fc = snow.check_avec_accumulation(with_values=False)
    s_avec = avec_fc.get("s").result if avec_fc is not None else None

    excep_fc = snow.check_exceptionnelle(with_values=False)
    s_excep = excep_fc.get("s").result if excep_fc is not None else None
    sAd = snow.ground.sAd if country == "FR" else None

    # ---- Résumé --------------------------------------------------------
    results: List[Dict] = [
        {"label": "Charge de neige au sol sk", "value": _f(sk, 3), "unit": "kN/m²", "formula": "Zone/altitude" if country == "FR" else "h, h0"},
        {"label": "μ1 (sans accumulation)", "value": _f(mu1, 3), "formula": "Tableau 5.2"},
        {"label": "μ2 (avec accumulation)", "value": _f(mu2, 3) if mu2 is not None else "n/a (α ≥ 60°)", "formula": "Tableau 5.2"},
        {"label": "s — sans accumulation", "value": _f(s_sans, 3), "unit": "kN/m²", "formula": "μ1·Ce·Ct·sk"},
    ]
    if s_avec is not None:
        results.append({"label": "s — avec accumulation", "value": _f(s_avec, 3), "unit": "kN/m²", "formula": "μ2·Ce·Ct·sk"})
    if s_excep is not None:
        results.append({"label": "s — charge exceptionnelle", "value": _f(s_excep, 3), "unit": "kN/m²", "formula": "μ1·Ce·Ct·sAd"})
    results.append({
        "label": "Charge de neige de calcul retenue",
        "value": _f(s_design, 3),
        "unit": "kN/m²",
        "status": "ok",
        "formula": "max(cas de charge applicables)",
    })

    # ---- Detail ----------------------------------------------------------
    donnees_rows = [
        {"label": "Norme", "value": "NF EN 1991-1-3/NA" if country == "FR" else "SIA 261:2020", "formula": None},
        {"label": "Angle de toiture α", "unit": "°", "value": _f(angle_deg, 1), "formula": None},
        {"label": "Exposition", "value": exposure, "formula": "Table Ce"},
        {"label": "Coefficient thermique Ct", "value": _f(Ct, 2), "formula": None},
    ]
    if country == "FR":
        donnees_rows.insert(1, {"label": "Zone de neige", "value": zone, "formula": "Annexe nationale"})
        donnees_rows.insert(2, {"label": "Altitude", "unit": "m", "value": _f(altitude_m, 0), "formula": None})
    else:
        donnees_rows.insert(1, {"label": "Altitude du site h", "unit": "m", "value": _f(altitude_m, 0), "formula": None})
        donnees_rows.insert(2, {"label": "Altitude de référence h0", "unit": "m", "value": _f(h0_m, 0), "formula": "SIA 261, Annexe D (carte)"})

    sol_rows = [
        {"label": "sk", "unit": "kN/m²", "value": _f(sk, 3), "formula": "sk0(zone) + Δs(altitude)" if country == "FR" else "[1+(h/h0)²]-0,4 ≥ 0,9"},
    ]
    if country == "FR":
        sol_rows.append({"label": "sAd (charge exceptionnelle)", "unit": "kN/m²", "value": _f(sAd, 3) if sAd is not None else "n/a", "formula": "Valeur directe par zone"})

    detail: Dict = {
        "blocks": [
            {"title": "Données", "rows": donnees_rows},
            {"title": "Charge de neige au sol", "rows": sol_rows},
            {
                "title": "Coefficients de forme — Tableau 5.2",
                "rows": [
                    {"label": "μ1 (sans accumulation)", "value": _f(mu1, 3), "formula": "0,8 si α≤30° ; 0,8(60-α)/30 si 30°<α<60° ; 0 si α≥60°"},
                    {"label": "μ2 (avec accumulation)", "value": _f(mu2, 3) if mu2 is not None else "n/a", "formula": "0,8+0,8α/30 si α≤30° ; 1,6 si 30°<α<60°"},
                ],
            },
            {
                "title": "Charges de toiture — s = μ·Ce·Ct·sk",
                "rows": [
                    {"label": "Ce (exposition)", "value": _f(snow.Ce, 2), "formula": "Table Ce"},
                    {"label": "s — sans accumulation", "unit": "kN/m²", "value": _f(s_sans, 3), "formula": "μ1·Ce·Ct·sk"},
                ] + (
                    [{"label": "s — avec accumulation", "unit": "kN/m²", "value": _f(s_avec, 3), "formula": "μ2·Ce·Ct·sk"}]
                    if s_avec is not None else []
                ) + (
                    [{"label": "s — charge exceptionnelle", "unit": "kN/m²", "value": _f(s_excep, 3), "formula": "μ1·Ce·Ct·sAd"}]
                    if s_excep is not None else []
                ),
            },
            {
                "title": "Résumé",
                "rows": [
                    {"label": "Charge de neige de calcul retenue", "unit": "kN/m²", "value": _f(s_design, 3), "formula": "max(cas de charge applicables)"},
                ],
            },
        ],
    }

    return {
        "module": "neige-toiture",
        "inputs": {
            "country": country,
            "zone": zone,
            "altitude_m": altitude_m,
            "h0_m": h0_m,
            "angle_deg": angle_deg,
            "exposure": exposure,
            "Ct": Ct,
        },
        "results": results,
        "detail": detail,
    }
