"""Stripe subscription service — recurring EUR 4.99 / month.

Design notes
------------

The app does **not** have user accounts yet: paywall/quotas are keyed by a
`device_id` generated on-device and persisted in AsyncStorage. That id is
carried through Stripe metadata so the webhook can update the correct user
document in MongoDB without any auth layer.

The Stripe credentials are configured in `backend/.env`:

    STRIPE_API_KEY          # secret key (sk_test_... or sk_live_...)
    STRIPE_WEBHOOK_SECRET   # whsec_... (leave "LINKTOADD" in dev to skip verify)
    STRIPE_PRICE_ID         # price_... (optional — inline price used if missing)
    STRIPE_SUCCESS_URL      # redirect after successful checkout
    STRIPE_CANCEL_URL       # redirect after cancel

When ``STRIPE_API_KEY`` starts with ``sk_test_emergent`` we route the API
through the Emergent integration proxy (same trick used by
``emergentintegrations.payments.stripe``) so the flow works out-of-the-box
without needing a real Stripe account.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import stripe
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PLACEHOLDER = "LINKTOADD"

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", PLACEHOLDER)
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", PLACEHOLDER)

# Default redirect URLs — the frontend can override these per-request.
DEFAULT_SUCCESS_URL = os.environ.get("STRIPE_SUCCESS_URL", PLACEHOLDER)
DEFAULT_CANCEL_URL = os.environ.get("STRIPE_CANCEL_URL", PLACEHOLDER)

# Product presentation.
SUB_PRICE_EUR = 4.99
SUB_CURRENCY = "eur"
SUB_INTERVAL = "month"
SUB_PRODUCT_NAME = "Structura Premium"

stripe.api_key = STRIPE_API_KEY
if "sk_test_emergent" in STRIPE_API_KEY:
    # Route through Emergent's Stripe proxy so the shared test key works.
    stripe.api_base = "https://integrations.emergentagent.com/stripe"
    logger.info("Stripe: using Emergent integration proxy")


# ---------------------------------------------------------------------------
# Mongo helpers — collection: premium_users, keyed by device_id
# ---------------------------------------------------------------------------
async def _upsert_user(
    db: AsyncIOMotorDatabase,
    device_id: str,
    fields: Dict[str, Any],
) -> None:
    await db.premium_users.update_one(
        {"device_id": device_id},
        {"$set": {**fields, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


async def get_status(
    db: AsyncIOMotorDatabase,
    device_id: str,
) -> Dict[str, Any]:
    doc = await db.premium_users.find_one({"device_id": device_id})
    if not doc:
        return {
            "device_id": device_id,
            "is_premium": False,
            "status": None,
            "current_period_end": None,
        }
    period_end = doc.get("current_period_end")
    if isinstance(period_end, datetime):
        period_end = int(period_end.timestamp())
    return {
        "device_id": device_id,
        "is_premium": bool(doc.get("is_premium", False)),
        "status": doc.get("status"),
        "current_period_end": period_end,
        "stripe_customer_id": doc.get("stripe_customer_id"),
        "stripe_subscription_id": doc.get("stripe_subscription_id"),
        "cancel_at_period_end": doc.get("cancel_at_period_end", False),
    }


# ---------------------------------------------------------------------------
# Checkout session creation
# ---------------------------------------------------------------------------
def _build_line_items() -> list:
    """Prefer a real Stripe price_id when configured, otherwise inline."""
    if STRIPE_PRICE_ID and STRIPE_PRICE_ID != PLACEHOLDER:
        return [{"price": STRIPE_PRICE_ID, "quantity": 1}]
    # Inline recurring price — works without pre-creating a product.
    return [
        {
            "price_data": {
                "currency": SUB_CURRENCY,
                "product_data": {"name": SUB_PRODUCT_NAME},
                "unit_amount": int(SUB_PRICE_EUR * 100),
                "recurring": {"interval": SUB_INTERVAL},
            },
            "quantity": 1,
        }
    ]


async def create_checkout_session(
    db: AsyncIOMotorDatabase,
    device_id: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> Dict[str, str]:
    """Create a Stripe Checkout Session in ``subscription`` mode."""
    if not STRIPE_API_KEY:
        raise RuntimeError("STRIPE_API_KEY not configured on the server")

    # Reuse existing Stripe customer if we already know one for this device.
    existing = await db.premium_users.find_one({"device_id": device_id})
    stripe_customer_id = existing.get("stripe_customer_id") if existing else None

    params: Dict[str, Any] = {
        "mode": "subscription",
        "line_items": _build_line_items(),
        "success_url": success_url
        or DEFAULT_SUCCESS_URL
        or f"{PLACEHOLDER}?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": cancel_url or DEFAULT_CANCEL_URL or PLACEHOLDER,
        "client_reference_id": device_id,
        "metadata": {"device_id": device_id},
        "subscription_data": {"metadata": {"device_id": device_id}},
    }
    if stripe_customer_id:
        params["customer"] = stripe_customer_id
    elif customer_email:
        params["customer_email"] = customer_email

    session = stripe.checkout.Session.create(**params)
    logger.info(
        "Stripe checkout created device=%s session=%s", device_id, session.id
    )

    # Track pending session so we can reconcile on redirect / webhook race.
    await _upsert_user(
        db,
        device_id,
        {
            "device_id": device_id,
            "last_checkout_session_id": session.id,
            "status": "pending_checkout",
        },
    )

    return {"url": session.url, "session_id": session.id}


# ---------------------------------------------------------------------------
# Webhook handling
# ---------------------------------------------------------------------------
async def _record_event_idempotent(
    db: AsyncIOMotorDatabase, event_id: str
) -> bool:
    """Insert the event id; return False if we've already processed it."""
    try:
        await db.stripe_events.insert_one(
            {"event_id": event_id, "processed_at": datetime.utcnow()}
        )
        return True
    except Exception:  # DuplicateKeyError once index exists
        return False


async def _apply_subscription_state(
    db: AsyncIOMotorDatabase,
    device_id: Optional[str],
    subscription: Dict[str, Any],
) -> None:
    if not device_id:
        # Fallback: find by customer id
        customer_id = subscription.get("customer")
        if customer_id:
            existing = await db.premium_users.find_one(
                {"stripe_customer_id": customer_id}
            )
            if existing:
                device_id = existing["device_id"]
    if not device_id:
        logger.warning("Stripe webhook: could not resolve device_id for sub")
        return

    status = subscription.get("status")
    is_premium = status in ("active", "trialing")
    period_end = subscription.get("current_period_end")
    if period_end:
        period_end = datetime.utcfromtimestamp(period_end)

    await _upsert_user(
        db,
        device_id,
        {
            "device_id": device_id,
            "is_premium": is_premium,
            "status": status,
            "stripe_customer_id": subscription.get("customer"),
            "stripe_subscription_id": subscription.get("id"),
            "current_period_end": period_end,
            "cancel_at_period_end": subscription.get(
                "cancel_at_period_end", False
            ),
        },
    )


async def process_webhook_event(
    db: AsyncIOMotorDatabase,
    payload: bytes,
    signature: Optional[str],
) -> Dict[str, Any]:
    """Verify + dispatch Stripe webhook payload."""
    if STRIPE_WEBHOOK_SECRET and STRIPE_WEBHOOK_SECRET != PLACEHOLDER:
        try:
            event = stripe.Webhook.construct_event(
                payload, signature or "", STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            logger.warning("Invalid Stripe signature: %s", exc)
            raise
    else:
        # Dev mode — signature secret not configured yet (LINKTOADD).
        import json

        event = json.loads(payload.decode("utf-8"))
        logger.warning(
            "Stripe webhook signature NOT verified (STRIPE_WEBHOOK_SECRET=LINKTOADD)"
        )

    event_id = event.get("id", "")
    if event_id and not await _record_event_idempotent(db, event_id):
        return {"received": True, "duplicate": True}

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {}) or {}
    logger.info("Stripe webhook: %s (%s)", event_type, event_id)

    if event_type == "checkout.session.completed":
        device_id = (
            obj.get("metadata", {}).get("device_id")
            or obj.get("client_reference_id")
        )
        if device_id:
            await _upsert_user(
                db,
                device_id,
                {
                    "device_id": device_id,
                    "stripe_customer_id": obj.get("customer"),
                    "stripe_subscription_id": obj.get("subscription"),
                    # Optimistic — will be confirmed by subscription.updated
                    "is_premium": obj.get("payment_status") == "paid",
                    "status": "active"
                    if obj.get("payment_status") == "paid"
                    else "processing",
                },
            )

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        device_id = obj.get("metadata", {}).get("device_id")
        await _apply_subscription_state(db, device_id, obj)

    return {"received": True, "type": event_type}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.premium_users.create_index("device_id", unique=True)
    await db.premium_users.create_index("stripe_customer_id")
    await db.stripe_events.create_index("event_id", unique=True)


# ---------------------------------------------------------------------------
# Manual reconciliation (client polls after redirect)
# ---------------------------------------------------------------------------
async def reconcile_from_session(
    db: AsyncIOMotorDatabase, device_id: str, session_id: str
) -> Dict[str, Any]:
    """Client fallback when webhook is late — fetch session + subscription."""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as exc:
        logger.warning("Cannot retrieve session %s: %s", session_id, exc)
        return await get_status(db, device_id)

    sub_id = session.get("subscription") if isinstance(session, dict) else session.subscription
    customer_id = session.get("customer") if isinstance(session, dict) else session.customer

    fields: Dict[str, Any] = {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": sub_id,
    }

    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            status = sub.get("status") if isinstance(sub, dict) else sub.status
            period_end = (
                sub.get("current_period_end")
                if isinstance(sub, dict)
                else sub.current_period_end
            )
            fields["status"] = status
            fields["is_premium"] = status in ("active", "trialing")
            if period_end:
                fields["current_period_end"] = datetime.utcfromtimestamp(
                    period_end
                )
        except stripe.error.StripeError as exc:
            logger.warning("Cannot retrieve subscription %s: %s", sub_id, exc)

    await _upsert_user(db, device_id, {"device_id": device_id, **fields})
    return await get_status(db, device_id)
