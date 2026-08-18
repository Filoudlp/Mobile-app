#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
core/coefficient.py
======================

Gestion centralisée des coefficients des Annexes Nationales pour tous les Eurocodes,
implémentée à l'aide de ``dataclasses`` pour un accès direct et typé :

>>> na = NationalAnnex.from_country(Country.FR)
>>> na.ec3.gamma_m0          # float — autocomplétion IDE ✓
1.0
>>> na.ec2.alpha_cc
1.0
>>> na.ec5.kdef
{1: 0.6, 2: 0.8, 3: 2.0}

Chaque ``@dataclass`` (``EC2Params``, ``EC3Params``…) porte les valeurs
recommandées par l'Eurocode comme valeurs **par défaut**.  Les surcharges
nationales ne redéfinissent que les champs qui diffèrent.
"""

__all__ = [
    "Country",
    "EC2Params",
    "EC3Params",
    "EC4Params",
    "EC5Params",
    "NationalAnnex",
    "DEFAULT_NA",
]

import copy
from dataclasses import dataclass, field, fields, replace
from enum import Enum, unique
from typing import Any


# ============================================================================
# 1. Énumération des pays supportés
# ============================================================================

@unique
class Country(Enum):
    """Pays dont l'Annexe Nationale est disponible.

    - ``DEFAULT`` : valeurs recommandées par l'Eurocode (sans AN).
    - ``FR``      : France.
    - ``BE``      : Belgique.
    - ``LU``      : Luxembourg.

    Pour ajouter un pays, ajouter un membre ici **et** une entrée
    correspondante dans ``_COUNTRY_OVERRIDES``.
    """

    DEFAULT = "DEFAULT"
    FR = "FR"
    BE = "BE"
    LU = "LU"
    UK = "UK"


# ============================================================================
# 2. Dataclasses — un jeu de paramètres par Eurocode
#    Les valeurs par défaut = valeurs RECOMMANDÉES par l'Eurocode.
# ============================================================================

@dataclass(frozen=True)
class EC2Params:
    """Paramètres de l'Annexe Nationale — Eurocode 2 (béton).

    Attributes
    ----------
    gamma_c : float
        Coefficient partiel de sécurité du béton — §2.4.2.4 — Table 2.1N.
    gamma_s : float
        Coefficient partiel de sécurité de l'acier d'armature — §2.4.2.4.
    alpha_cc : float
        Coefficient tenant compte des effets à long terme sur la résistance
        en compression et des effets défavorables résultant de la façon
        dont la charge est appliquée — §3.1.6 (1)P.
    alpha_ct : float
        Idem ``alpha_cc`` mais pour la traction — §3.1.6 (2)P.
    k1 : float
        Coefficient pour la fissuration — §7.3.
    k2 : float
        Coefficient simplifié de fluage — §3.1.4.
    cnom_min_dur : dict[str, float]
        Enrobage minimal de durabilité [mm] par classe d'exposition
        — Table 4.4N.
    """

    gamma_c: float = 1.5
    gamma_s: float = 1.15
    alpha_cc: float = 1.0
    alpha_ct: float = 1.0
    k1: float = 0.6
    k2: float = 0.45



@dataclass(frozen=True)
class EC3Params:
    """Paramètres de l'Annexe Nationale — Eurocode 3 (acier).

    Attributes
    ----------
    gamma_m0 : float
        Coefficient partiel — résistance des sections — §6.1 (1).
    gamma_m1 : float
        Coefficient partiel — instabilité — §6.1 (1).
    gamma_m2 : float
        Coefficient partiel — résistance ultime / assemblages — §6.1 (1).
    gamma_m3 : float
        Coefficient partiel — assemblages par glissement ELU — §2.2.
    gamma_m3_ser : float
        Coefficient partiel — assemblages par glissement ELS (cat. B) — §2.2.
    alpha_imp : float
        Imperfection globale par défaut (1/200) — §5.3.2.
    """

    gamma_m0: float = 1.0
    gamma_m1: float = 1.0
    gamma_m2: float = 1.25
    gamma_m3: float = 1.25
    gamma_m3_ser: float = 1.1
    alpha_imp: float = 1 / 200


@dataclass(frozen=True)
class EC4Params:
    """Paramètres de l'Annexe Nationale — Eurocode 4 (mixte acier-béton).

    Attributes
    ----------
    gamma_c : float
        Coefficient partiel du béton — §2.4.1.2.
    gamma_s : float
        Coefficient partiel de l'acier d'armature — §2.4.1.2.
    gamma_a : float
        Coefficient partiel de l'acier de construction — §2.4.1.2.
    gamma_vs : float
        Coefficient partiel des connecteurs — §2.4.1.2.
    """

    gamma_c: float = 1.5
    gamma_s: float = 1.15
    gamma_a: float = 1.0
    gamma_vs: float = 1.25


@dataclass(frozen=True)
class EC5Params:
    """Paramètres de l'Annexe Nationale — Eurocode 5 (bois).

    Attributes
    ----------
    gamma_m : float
        Coefficient partiel du matériau — Table 2.3.
    gamma_m_connection : float
        Coefficient partiel pour les assemblages — Table 2.3.
    kdef : dict[int, float]
        Facteur de déformation par classe de service — Table 3.2.
    """

    gamma_m: float = 1.3
    gamma_m_connection: float = 1.3
    kdef: dict[int, float] = field(default_factory=lambda: {
        1: 0.6, 2: 0.8, 3: 2.0,
    })


# ============================================================================
# 3. Surcharges nationales
#    Seuls les champs qui DIFFÈRENT de la valeur recommandée sont listés.
# ============================================================================

_COUNTRY_OVERRIDES: dict[Country, dict[str, dict[str, Any]]] = {

    Country.DEFAULT: {},          # rien à surcharger

    Country.FR: {
        "ec2": {
            "alpha_cc": 1.0,
            "alpha_ct": 1.0,
        },
        "ec3": {
            "gamma_m0": 1.0,
            "gamma_m1": 1.0,
            "gamma_m2": 1.25,
        },
        "ec4": {},
        "ec5": {
            "gamma_m": 1.3,
        },
    },

    Country.BE: {
        "ec2": {
            "alpha_cc": 0.85,
            "alpha_ct": 1.0,
            "cnom_min_dur": {
                "X0": 15,
                "XC1": 20,
            },
        },
        "ec3": {
            "gamma_m0": 1.0,
            "gamma_m1": 1.0,
            "gamma_m2": 1.25,
        },
        "ec4": {},
        "ec5": {},
    },

    Country.LU: {},               # hérite intégralement de DEFAULT
    Country.UK: {},               # hérite intégralement de DEFAULT
}


# ============================================================================
# 4. Fonctions utilitaires internes
# ============================================================================

def _deep_merge_dict(base: dict, override: dict) -> dict:
    """Fusionne *override* dans une copie profonde de *base* (récursif).

    Utilisé pour les champs de type ``dict`` (ex. ``cnom_min_dur``,
    ``kdef``).

    Parameters
    ----------
    base : dict
        Dictionnaire de référence (non modifié).
    override : dict
        Dictionnaire de surcharge.

    Returns
    -------
    dict
        Nouveau dictionnaire fusionné.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _apply_overrides(dc_instance: Any, overrides: dict[str, Any]) -> Any:
    """Applique des surcharges à une instance de dataclass ``frozen``.

    Pour les champs de type ``dict``, un merge récursif est effectué
    afin de ne pas perdre les clés non redéfinies.

    Parameters
    ----------
    dc_instance : dataclass
        Instance de base (valeurs recommandées).
    overrides : dict[str, Any]
        Champs à surcharger.

    Returns
    -------
    dataclass
        Nouvelle instance avec les surcharges appliquées.
    """
    if not overrides:
        return dc_instance

    field_names: set[str] = {f.name for f in fields(dc_instance)}
    merged_overrides: dict[str, Any] = {}

    for key, value in overrides.items():
        if key not in field_names:
            continue  # ignore les clés inconnues

        current_value = getattr(dc_instance, key)

        # Merge récursif si les deux côtés sont des dicts
        if isinstance(current_value, dict) and isinstance(value, dict):
            merged_overrides[key] = _deep_merge_dict(current_value, value)
        else:
            merged_overrides[key] = copy.deepcopy(value)

    return replace(dc_instance, **merged_overrides)


# Correspondance nom de section → classe de dataclass
_EC_CLASSES: dict[str, type] = {
    "ec2": EC2Params,
    "ec3": EC3Params,
    "ec4": EC4Params,
    "ec5": EC5Params,
}


# ============================================================================
# 5. Classe NationalAnnex
# ============================================================================

@dataclass(frozen=True)
class NationalAnnex:
    """Annexe Nationale centralisée, utilisable par tous les Eurocodes.

    Tous les paramètres sont accessibles de manière **directe et typée** :

    >>> na = NationalAnnex.from_country(Country.FR)
    >>> na.ec3.gamma_m0
    1.0
    >>> na.ec2.cnom_min_dur["XC1"]
    15

    La création se fait via la *factory* :meth:`from_country` qui gère
    automatiquement le merge entre les valeurs recommandées et les
    surcharges nationales.

    Attributes
    ----------
    country : Country
        Pays de l'annexe nationale.
    ec2 : EC2Params
        Paramètres Eurocode 2.
    ec3 : EC3Params
        Paramètres Eurocode 3.
    ec4 : EC4Params
        Paramètres Eurocode 4.
    ec5 : EC5Params
        Paramètres Eurocode 5.
    """

    country: Country = Country.DEFAULT
    ec2: EC2Params = field(default_factory=EC2Params)
    ec3: EC3Params = field(default_factory=EC3Params)
    ec4: EC4Params = field(default_factory=EC4Params)
    ec5: EC5Params = field(default_factory=EC5Params)

    # ------------------------------------------------------- factory
    @classmethod
    def from_country(cls, country: Country = Country.DEFAULT) -> "NationalAnnex":
        """Crée une ``NationalAnnex`` pour un pays donné.

        Les valeurs recommandées sont instanciées par défaut, puis
        surchargées par les données nationales présentes dans
        ``_COUNTRY_OVERRIDES``.

        Parameters
        ----------
        country : Country, optional
            Pays cible.  ``Country.DEFAULT`` par défaut.

        Returns
        -------
        NationalAnnex
            Instance avec les paramètres fusionnés.

        Examples
        --------
        >>> na = NationalAnnex.from_country(Country.BE)
        >>> na.ec2.alpha_cc
        0.85
        """
        overrides: dict[str, dict[str, Any]] = _COUNTRY_OVERRIDES.get(
            country, {}
        )

        # Instancier chaque bloc EC avec ses surcharges
        ec_instances: dict[str, Any] = {}
        for ec_key, ec_class in _EC_CLASSES.items():
            base_instance = ec_class()  # valeurs recommandées
            ec_overrides = overrides.get(ec_key, {})
            ec_instances[ec_key] = _apply_overrides(base_instance, ec_overrides)

        return cls(
            country=country,
            **ec_instances,
        )

    # ------------------------------------------------------- list_params
    def list_params(self, eurocode: str) -> list[str]:
        """Liste les noms de champs disponibles pour un Eurocode donné.

        Parameters
        ----------
        eurocode : str
            Clé en minuscules : ``"ec2"``, ``"ec3"``, ``"ec4"``, ``"ec5"``.

        Returns
        -------
        list[str]
            Liste triée des noms de paramètres.

        Raises
        ------
        ValueError
            Si l'eurocode demandé n'existe pas.

        Examples
        --------
        >>> na = NationalAnnex.from_country(Country.FR)
        >>> na.list_params("ec3")
        ['alpha_imp', 'gamma_m0', 'gamma_m1', 'gamma_m2', 'gamma_m3', 'gamma_m3_ser']
        """
        ec_key = eurocode.lower()
        if not hasattr(self, ec_key):
            raise ValueError(
                f"Eurocode '{eurocode}' inconnu. "
                f"Valeurs acceptées : {list(_EC_CLASSES.keys())}"
            )
        ec_instance = getattr(self, ec_key)
        return sorted(f.name for f in fields(ec_instance))

    # ------------------------------------------------------- repr
    def __repr__(self) -> str:
        return f"NationalAnnex({self.country.value})"


# ============================================================================
# 6. Instance globale par défaut
# ============================================================================

DEFAULT_NA: NationalAnnex = NationalAnnex.from_country(Country.DEFAULT)
"""Instance par défaut (valeurs recommandées Eurocode, sans AN)."""


# ============================================================================
# 7. Démonstration
# ============================================================================

if __name__ == "__main__":

    print("=" * 65)
    print("  DÉMONSTRATION — core/national_annex.py  (dataclass)")
    print("=" * 65)

    print(list(Country))
    a = max(2.0, 2.0 + 0.085 * (30 - 50) ** 0.53) / 1000
    print(a)
    print(f"test: {a}")
    # --- Création d'un NA français ---
    ab = "FR"
    
    na_fr = NationalAnnex.from_country(Country[ab])
    print(f"\n>>> na_fr = {na_fr!r}")

    # --- Accès direct typé (autocomplétion IDE) ---
    print(f"\n--- Accès direct typé ---")
    print(f"  na_fr.ec3.gamma_m0          = {na_fr.ec3.gamma_m0}")
    print(f"  na_fr.ec3.gamma_m1          = {na_fr.ec3.gamma_m1}")
    print(f"  na_fr.ec3.gamma_m2          = {na_fr.ec3.gamma_m2}")
    print(f"  na_fr.ec3.alpha_imp         = {na_fr.ec3.alpha_imp}")
    print(f"  na_fr.ec2.gamma_c           = {na_fr.ec2.gamma_c}")
    print(f"  na_fr.ec2.gamma_s           = {na_fr.ec2.gamma_s}")
    print(f"  na_fr.ec2.alpha_cc          = {na_fr.ec2.alpha_cc}")
    print(f"  na_fr.ec4.gamma_vs          = {na_fr.ec4.gamma_vs}")
    print(f"  na_fr.ec5.gamma_m           = {na_fr.ec5.gamma_m}")
    print(f"  na_fr.ec5.kdef              = {na_fr.ec5.kdef}")
    print(f"  na_fr.ec2.cnom_min_dur      = {na_fr.ec2.cnom_min_dur}")

    # --- Listing des paramètres EC3 ---
    print(f"\n--- Paramètres EC3 disponibles ---")
    print(f"  {na_fr.list_params('ec3')}")

    # --- Comparaison BE vs DEFAULT ---
    print(f"\n--- Comparaison alpha_cc ---")
    na_be = NationalAnnex.from_country(Country.BE)
    na_def = NationalAnnex.from_country(Country.DEFAULT)
    print(f"  DEFAULT : alpha_cc = {na_def.ec2.alpha_cc}")
    print(f"  FR      : alpha_cc = {na_fr.ec2.alpha_cc}")
    print(f"  BE      : alpha_cc = {na_be.ec2.alpha_cc}")

    # --- Merge récursif : BE surcharge partiellement cnom_min_dur ---
    print(f"\n--- Merge récursif cnom_min_dur (BE) ---")
    print(f"  DEFAULT X0  = {na_def.ec2.cnom_min_dur['X0']:>3}  →  "
          f"BE X0  = {na_be.ec2.cnom_min_dur['X0']:>3}")
    print(f"  DEFAULT XC1 = {na_def.ec2.cnom_min_dur['XC1']:>3}  →  "
          f"BE XC1 = {na_be.ec2.cnom_min_dur['XC1']:>3}")
    print(f"  DEFAULT XD3 = {na_def.ec2.cnom_min_dur['XD3']:>3}  →  "
          f"BE XD3 = {na_be.ec2.cnom_min_dur['XD3']:>3}  (hérité)")

    # --- LU hérite intégralement de DEFAULT ---
    na_lu = NationalAnnex.from_country(Country.LU)
    print(f"\n>>> na_lu = {na_lu!r}")
    print(f"  gamma_m0 = {na_lu.ec3.gamma_m0}  (hérité de DEFAULT)")

    # --- Frozen : tentative de modification → erreur ---
    print(f"\n--- Sécurité : frozen=True ---")
    try:
        na_fr.ec3.gamma_m0 = 999  # type: ignore[misc]
    except AttributeError as e:
        print(f"  Modification interdite : {e}")

    print(f"\n{'=' * 65}")
    print("  FIN DÉMONSTRATION")
    print("=" * 65)
