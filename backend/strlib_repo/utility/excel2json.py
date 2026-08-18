#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Convert Excel sections database to JSON
"""

import json
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
#  CONFIG — à modifier selon ton fichier
# ─────────────────────────────────────────────
EXCEL_FILE  = "section-arcelor-mital.xlsx"   # chemin vers ton Excel
OUTPUT_FILE = "chs.json"   # fichier JSON de sortie
SHEET_NAME  = "Tube creux rond"               # 0 = 1ère feuille, ou "IPE", "HEA"...
DESCRIPTION  = "CHS sections from ArcelorMittal"
# ─────────────────────────────────────────────


def excel_to_json(excel_file: str,
                  output_file: str,
                  sheet_name: int | str = 0, description: str = "") -> None:
    """
    Lit un fichier Excel et génère un fichier JSON.

    :param excel_file:  Chemin vers le fichier Excel
    :param output_file: Chemin vers le fichier JSON de sortie
    :param sheet_name:  Nom ou index de la feuille Excel
    """
    excel_path = Path(excel_file)

    if not excel_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {excel_path.resolve()}")

    print(f"Lecture de '{excel_path.name}' — feuille : '{sheet_name}' ...")

    # --- Lecture ---
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    # --- Nettoyage ---
    df.columns = df.columns.str.strip()          # retire les espaces dans les noms de colonnes
    df = df.dropna(how="all")                    # retire les lignes entièrement vides
    df = df.where(pd.notna(df), other=None)      # NaN → None (→ null en JSON)

    # --- Conversion ---
    sections = df.to_dict(orient="records")

    payload = {
        "source" : excel_path.name,
        "website": "https://sections.arcelormittal.com/products_and_solutions/Product_catalogues/FR",
        "description" : description,
        "sheet"  : sheet_name,
        "count"  : len(sections),
        "sections": sections,
    }

    # --- Écriture ---
    output_path = Path(output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    print(f"✅ {len(sections)} sections exportées → '{output_path.resolve()}'")


def excel_multi_sheets_to_json(excel_file: str,
                                output_file: str) -> None:
    """
    Lit TOUTES les feuilles d'un Excel et génère un JSON groupé par feuille.
    Utile si tu as une feuille IPE, une feuille HEA, etc.

    :param excel_file:  Chemin vers le fichier Excel
    :param output_file: Chemin vers le fichier JSON de sortie
    """
    excel_path = Path(excel_file)

    if not excel_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {excel_path.resolve()}")

    print(f"Lecture de '{excel_path.name}' — toutes les feuilles ...")

    xls = pd.ExcelFile(excel_path)
    payload = {
        "source": excel_path.name,
        "sheets": {}
    }

    total = 0
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df.columns = df.columns.str.strip()
        df = df.dropna(how="all")
        df = df.where(pd.notna(df), other=None)
        sections = df.to_dict(orient="records")

        payload["sheets"][sheet] = {
            "count"   : len(sections),
            "sections": sections,
        }
        total += len(sections)
        print(f"  → Feuille '{sheet}' : {len(sections)} sections")

    payload["total"] = total

    output_path = Path(output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    print(f"✅ {total} sections au total → '{output_path.resolve()}'")


if __name__ == "__main__":

    # ── Option A : une seule feuille ──────────────────────────────────────
    excel_to_json(
        excel_file  = EXCEL_FILE,
        output_file = OUTPUT_FILE,
        sheet_name  = SHEET_NAME,
        description = DESCRIPTION,
    )

    # ── Option B : toutes les feuilles (décommenter si besoin) ────────────
    # excel_multi_sheets_to_json(
    #     excel_file  = EXCEL_FILE,
    #     output_file = OUTPUT_FILE,
    # )
