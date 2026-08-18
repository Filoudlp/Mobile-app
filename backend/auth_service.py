"""
Authentification par compte et quota journalier — C-Lab.

Comptes stockés dans MongoDB (collection ``users``), mots de passe hachés
avec bcrypt, sessions par jeton JWT.

Le quota est appliqué **côté serveur** (collection ``usage``) : c'est le
seul endroit où il est fiable. Le compteur local du frontend n'est qu'un
affichage — un utilisateur qui vide son navigateur ne regagne pas de
calculs.

    Gratuit  : FREE_DAILY_LIMIT calculs par jour et par compte
    Premium  : illimité

Le rattachement de l'abonnement Stripe se fait sur ``user_id`` ; l'ancien
``device_id`` reste accepté en lecture pour ne pas casser les abonnements
souscrits avant l'introduction des comptes.
"""
from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

#: Nombre de calculs offerts par jour à un compte gratuit.
FREE_DAILY_LIMIT = 5

#: Durée de validité d'un jeton de session.
TOKEN_TTL_DAYS = 30

_ALGO = "HS256"

# La clé de signature doit être stable entre deux redémarrages, sinon toutes
# les sessions sautent. En l'absence de variable d'environnement on en
# génère une éphémère (utile en développement, jamais en production).
_SECRET = os.environ.get("AUTH_SECRET") or secrets.token_urlsafe(48)
AUTH_SECRET_IS_EPHEMERAL = "AUTH_SECRET" not in os.environ

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------------------------
# Erreurs métier
# ---------------------------------------------------------------------------
class AuthError(Exception):
    """Erreur d'authentification à traduire en réponse HTTP par l'appelant."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_credentials(email: str, password: str) -> str:
    """Valide et normalise l'e-mail ; vérifie la robustesse du mot de passe."""
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise AuthError(400, "Adresse e-mail invalide.")
    if len(password or "") < 8:
        raise AuthError(400, "Le mot de passe doit faire au moins 8 caractères.")
    return email


# ---------------------------------------------------------------------------
# Jetons
# ---------------------------------------------------------------------------
def create_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGO)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGO])
    except jwt.ExpiredSignatureError:
        raise AuthError(401, "Session expirée — reconnectez-vous.")
    except jwt.InvalidTokenError:
        raise AuthError(401, "Session invalide.")


# ---------------------------------------------------------------------------
# Comptes
# ---------------------------------------------------------------------------
async def register(db, email: str, password: str) -> Dict[str, Any]:
    """Crée un compte et retourne (user public, token)."""
    email = validate_credentials(email, password)
    if await db.users.find_one({"email": email}):
        raise AuthError(409, "Un compte existe déjà avec cette adresse.")

    user_id = secrets.token_urlsafe(16)
    doc = {
        "user_id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc),
        "premium": False,
    }
    await db.users.insert_one(doc)
    return {"user": _public(doc), "token": create_token(user_id, email)}


async def login(db, email: str, password: str) -> Dict[str, Any]:
    email = (email or "").strip().lower()
    doc = await db.users.find_one({"email": email})
    # Message volontairement identique dans les deux cas : ne pas révéler
    # quelles adresses ont un compte.
    if not doc or not verify_password(password, doc.get("password_hash", "")):
        raise AuthError(401, "E-mail ou mot de passe incorrect.")
    return {"user": _public(doc), "token": create_token(doc["user_id"], email)}


async def change_password(db, user_id: str, current: str, new: str) -> None:
    doc = await db.users.find_one({"user_id": user_id})
    if not doc or not verify_password(current, doc.get("password_hash", "")):
        raise AuthError(401, "Mot de passe actuel incorrect.")
    if len(new or "") < 8:
        raise AuthError(400, "Le nouveau mot de passe doit faire au moins 8 caractères.")
    await db.users.update_one(
        {"user_id": user_id}, {"$set": {"password_hash": hash_password(new)}}
    )


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Projection publique d'un utilisateur — jamais le hash."""
    return {
        "user_id": doc["user_id"],
        "email": doc["email"],
        "premium": bool(doc.get("premium", False)),
        "created_at": (
            doc["created_at"].isoformat()
            if isinstance(doc.get("created_at"), datetime)
            else doc.get("created_at")
        ),
    }


async def get_user(db, user_id: str) -> Optional[Dict[str, Any]]:
    doc = await db.users.find_one({"user_id": user_id})
    return _public(doc) if doc else None


async def set_premium(db, user_id: str, premium: bool, **extra) -> None:
    """Marque un compte comme premium (appelé par le webhook Stripe)."""
    update = {"premium": premium, **extra}
    await db.users.update_one({"user_id": user_id}, {"$set": update})


# ---------------------------------------------------------------------------
# Quota journalier — appliqué côté serveur
# ---------------------------------------------------------------------------
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def get_usage(db, user_id: str, premium: bool) -> Dict[str, Any]:
    """État du quota du jour, sans le consommer."""
    if premium:
        return {
            "premium": True,
            "limit": None,
            "used": 0,
            "remaining": None,
            "can_compute": True,
        }
    doc = await db.usage.find_one({"user_id": user_id, "date": _today()})
    used = int(doc.get("count", 0)) if doc else 0
    remaining = max(FREE_DAILY_LIMIT - used, 0)
    return {
        "premium": False,
        "limit": FREE_DAILY_LIMIT,
        "used": used,
        "remaining": remaining,
        "can_compute": remaining > 0,
    }


async def consume_quota(db, user_id: str, premium: bool) -> Dict[str, Any]:
    """
    Consomme un calcul. Lève AuthError(402) si le quota est épuisé.

    L'incrément est atomique ($inc + upsert) : deux requêtes simultanées ne
    peuvent pas passer au travers du même crédit restant.
    """
    if premium:
        return await get_usage(db, user_id, True)

    doc = await db.usage.find_one_and_update(
        {"user_id": user_id, "date": _today()},
        {"$inc": {"count": 1}},
        upsert=True,
        return_document=True,
    )
    used = int(doc.get("count", 1)) if doc else 1
    if used > FREE_DAILY_LIMIT:
        # On rend le crédit consommé en trop pour que le compteur reflète la
        # réalité si l'utilisateur passe premium dans la journée.
        await db.usage.update_one(
            {"user_id": user_id, "date": _today()}, {"$inc": {"count": -1}}
        )
        raise AuthError(
            402,
            f"Quota gratuit atteint ({FREE_DAILY_LIMIT} calculs par jour). "
            f"Passez en illimité pour continuer.",
        )
    return {
        "premium": False,
        "limit": FREE_DAILY_LIMIT,
        "used": used,
        "remaining": max(FREE_DAILY_LIMIT - used, 0),
        "can_compute": used < FREE_DAILY_LIMIT,
    }


async def ensure_indexes(db) -> None:
    """Index à créer au démarrage."""
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.usage.create_index([("user_id", 1), ("date", 1)], unique=True)


# ---------------------------------------------------------------------------
# Dépendances FastAPI
# ---------------------------------------------------------------------------
def _bearer(request: Request) -> Optional[str]:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


async def current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Utilisateur connecté, ou None si pas de jeton valide."""
    token = _bearer(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except AuthError:
        return None
    db = getattr(request.app.state, "db", None)
    if db is None:
        return None
    return await get_user(db, payload.get("sub", ""))


async def current_user(request: Request) -> Dict[str, Any]:
    """Utilisateur connecté — 401 sinon."""
    user = await current_user_optional(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Connexion requise.")
    return user
