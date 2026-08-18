#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
core/formula.py

Brique fondamentale de la librairie de calculs d'ingénierie structure.

Fournit deux classes :
- FormulaResult  : résultat d'un calcul unique (valeur, formule, référence…).
- FormulaCollection : conteneur ordonné de FormulaResult formant un rapport.

Ces classes sont utilisées par TOUS les modules (Material, Section,
SectionMaterial) et par tous les Eurocodes (EC2, EC3, EC5…).

Aucune dépendance externe – uniquement la bibliothèque standard Python ≥ 3.10.
"""

__all__ = ["FormulaResult", "FormulaCollection"]

from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
#  FormulaResult
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FormulaResult:
    """Résultat d'UN calcul unique.

    Attributes
    ----------
    name : str
        Nom court du résultat (ex: ``"Npl,Rd"``).
    formula : str
        Expression littérale (ex: ``"Npl,Rd = A · fy / γM0"``).
    formula_values : str
        Expression avec valeurs numériques substituées.
        Chaîne vide si non demandé.
    result : float
        Valeur numérique du résultat.
    unit : str
        Unité du résultat (ex: ``"N"``, ``"MPa"``, ``"-"``).
    ref : str
        Référence normative (ex: ``"EC3-1-1 — §6.2.3 (2)a"``).
    is_check : bool
        ``True`` si le résultat est une vérification (taux ≤ limite).
    limit : float
        Valeur limite pour les vérifications.
    """

    name: str
    formula: str
    formula_values: str = ""
    result: float = 0.0
    unit: str = ""
    ref: str = ""
    is_check: bool = False
    limit: float = 1.0
    #status: str = None

    # -- Propriétés ----------------------------------------------------------

    @property
    def status(self) -> Optional[str]:
            """Statut de la vérification.

            Returns
            -------
            str or None
                ``"OK ✓"`` si *result* ≤ *limit*,
                ``"NON VÉRIFIÉ ✗"`` sinon,
                ``None`` si ce n'est pas une vérification.
            """
            if not self.is_check:
                return None
            return "OK ✓" if self.result <= self.limit else "NON VÉRIFIÉ ✗"

    @property
    def is_ok(self) -> Optional[bool]:
        """La vérification est-elle satisfaite ?

        Returns
        -------
        bool or None
            ``True`` / ``False`` selon *result* ≤ *limit*,
            ``None`` si ``is_check`` est ``False``.
        """
        if not self.is_check:
            return None
        return self.result <= self.limit


    # -- Méthodes spéciales ---------------------------------------------------

    def __repr__(self) -> str:
        """Affichage compact sur une ligne."""
        return f"FormulaResult({self.name} = {self.result:.2f} {self.unit})".rstrip()

    def __str__(self) -> str:
        """Affichage détaillé multi-lignes."""
        lines: list[str] = [
            self.name,
            f"  Formule  : {self.formula}",
        ]
        if self.formula_values:
            lines.append(f"  Valeurs  : {self.formula_values}")
        lines.append(f"  Résultat : {self.result:.2f} {self.unit}".rstrip())
        if self.ref:
            lines.append(f"  Réf      : {self.ref}")
        if self.is_check:
            lines.append(f"  Statut   : {self.status}")
        return "\n".join(lines)

    # -- Export ---------------------------------------------------------------

    def to_dict(self) -> dict:
        """Export en dictionnaire Python complet.

        Returns
        -------
        dict
            Tous les attributs de l'instance + la clé ``"status"``.
        """
        return {
            "name": self.name,
            "formula": self.formula,
            "formula_values": self.formula_values,
            "result": self.result,
            "unit": self.unit,
            "ref": self.ref,
            "is_check": self.is_check,
            "limit": self.limit,
            "status": self.status,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  FormulaCollection
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FormulaCollection:
    """Conteneur ordonné de :class:`FormulaResult` formant un rapport de calcul.

    Attributes
    ----------
    title : str
        Titre du rapport (ex: ``"Vérification à la traction"``).
    ref : str
        Référence normative globale.
    results : list[FormulaResult]
        Liste ordonnée des résultats, initialisée vide.
    """

    title: str
    ref: str = ""
    results: list[FormulaResult] = field(default_factory=list)

    # -- Propriétés ----------------------------------------------------------

    @property
    def checks(self) -> list[FormulaResult]:
        """Liste filtrée des résultats de type vérification.

        Returns
        -------
        list[FormulaResult]
            Sous-ensemble dont ``is_check`` vaut ``True``.
        """
        return [r for r in self.results if r.is_check]

    @property
    def is_ok(self) -> bool:
        """Toutes les vérifications passent-elles ?

        Returns
        -------
        bool
            ``True`` si chaque check satisfait *result* ≤ *limit*.
            ``True`` également si la collection ne contient aucun check.
        """
        return all(r.result <= r.limit for r in self.checks)

    @property
    def max_ratio(self) -> float:
        """Taux de travail maximal parmi les vérifications.

        Returns
        -------
        float
            Valeur ``result`` maximale des checks, ``0.0`` si aucun check.
        """
        c = self.checks
        if not c:
            return 0.0
        return max(r.result for r in c)

    # -- Méthodes publiques ---------------------------------------------------

    def add(self, result: FormulaResult) -> None:
        """Ajouter un résultat à la fin de la collection.

        Parameters
        ----------
        result : FormulaResult
            Résultat à ajouter.
        """
        self.results.append(result)

    def get(self, name: str) -> Optional[FormulaResult]:
        """Récupérer le premier résultat correspondant à *name*.

        Parameters
        ----------
        name : str
            Nom recherché (comparaison exacte).

        Returns
        -------
        FormulaResult or None
        """
        for r in self.results:
            if r.name == name:
                return r
        return None

    # -- Méthodes spéciales ---------------------------------------------------

    def __repr__(self) -> str:
        """Ligne résumé."""
        status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
        return (
            f"FormulaCollection({self.title} — "
            f"{len(self.results)} résultats — {status})"
        )

    def __str__(self) -> str:
        """Affichage du rapport complet."""
        w = 50
        sep_double = "═" * w
        sep_single = "─" * w

        lines: list[str] = [sep_double, self.title]
        if self.ref:
            lines.append(f"Réf : {self.ref}")
        lines.append(sep_double)

        for i, r in enumerate(self.results):
            if i > 0:
                lines.append("")
            lines.append(str(r))

        lines.append(sep_single)
        if self.checks:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            lines.append(
                f"STATUT GLOBAL : {status} (taux max = {self.max_ratio:.4f})"
            )
        else:
            status = "OK ✓" if self.is_ok else "NON VÉRIFIÉ ✗"
            lines.append(f"STATUT GLOBAL : {status}")
        lines.append(sep_single)

        return "\n".join(lines)

    def __iter__(self):
        """Itérable sur les résultats."""
        return iter(self.results)

    def __len__(self) -> int:
        """Nombre de résultats."""
        return len(self.results)

    def __getitem__(self, index: int) -> FormulaResult:
        """Accès par index.

        Parameters
        ----------
        index : int
            Position dans la liste ordonnée.
        """
        return self.results[index]

    # -- Export ---------------------------------------------------------------

    def to_dict(self) -> dict:
        """Export en dictionnaire Python complet.

        Returns
        -------
        dict
            Clés : *title*, *ref*, *is_ok*, *max_ratio*, *results* (liste de dict).
        """
        return {
            "title": self.title,
            "ref": self.ref,
            "is_ok": self.is_ok,
            "max_ratio": self.max_ratio,
            "results": [r.to_dict() for r in self.results],
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Exemple d'utilisation
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # 1) Création de FormulaResult ────────────────────────────────────────────

    npl = FormulaResult(
        name="Npl,Rd",
        formula="Npl,Rd = A · fy / γM0",
        formula_values="Npl,Rd = 1200.00 × 355.00 / 1.0 = 426000.00 N",
        result=426_000.0,
        unit="N",
        ref="EC3-1-1 — §6.2.3 (2)a",
    )

    nu = FormulaResult(
        name="Nu,Rd",
        formula="Nu,Rd = 0.9 · Anet · fu / γM2",
        formula_values="Nu,Rd = 0.9 × 1100.00 × 490.00 / 1.25 = 388080.00 N",
        result=388_080.0,
        unit="N",
        ref="EC3-1-1 — §6.2.3 (2)b",
    )

    verif = FormulaResult(
        name="Ned/Nt,Rd",
        formula="Ned / Nt,Rd ≤ 1.0",
        formula_values=(
            "Ned / Nt,Rd = 330000.00 / 388080.00 = 0.8504 ≤ 1.0 → OK ✓"
        ),
        result=0.8504,
        unit="-",
        ref="EC3-1-1 — §6.2.3 (1)",
        is_check=True,
        limit=1.0,
    )

    # 2) Création d'une FormulaCollection ─────────────────────────────────────

    rapport = FormulaCollection(
        title="Vérification à la traction",
        ref="EC3-1-1 — §6.2.3",
    )
    rapport.add(npl)
    rapport.add(nu)
    rapport.add(verif)

    # 3) Affichage du rapport ─────────────────────────────────────────────────

    print(rapport)
    print()

    # 4) Accès au statut global ───────────────────────────────────────────────

    print(f"repr  → {rapport!r}")
    print(f"is_ok → {rapport.is_ok}")
    print(f"max   → {rapport.max_ratio:.4f}")
    print(f"get   → {rapport.get('Nu,Rd')!r}")
    print(f"len   → {len(rapport)}")
    print(f"[0]   → {rapport[0]!r}")
