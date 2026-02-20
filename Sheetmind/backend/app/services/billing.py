"""
Dodo Payments billing service — handles checkout sessions, webhook events,
and subscription management.
"""

import hashlib
import hmac
import base64
import json
import logging
import time
from typing import Literal

from dodopayments import DodoPayments

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# Webhook replay tolerance: reject events older than 5 minutes
_WEBHOOK_TIMESTAMP_TOLERANCE = 300  # seconds

# Webhook idempotency: remember processed webhook IDs for 48 hours
_WEBHOOK_ID_TTL = 48 * 60 * 60  # seconds

PlanType = Literal["pro_monthly", "pro_annual", "team_monthly", "team_annual"]

PLAN_PRODUCT_MAP: dict[str, str] = {}
PRODUCT_TIER_MAP: dict[str, str] = {}


def _init_maps():
    """Populate product maps from settings once values are available."""
    global PLAN_PRODUCT_MAP, PRODUCT_TIER_MAP
    PLAN_PRODUCT_MAP = {
        "pro_monthly": settings.DODO_PRO_MONTHLY_PRODUCT_ID,
        "pro_annual": settings.DODO_PRO_ANNUAL_PRODUCT_ID,
        "team_monthly": settings.DODO_TEAM_MONTHLY_PRODUCT_ID,
        "team_annual": settings.DODO_TEAM_ANNUAL_PRODUCT_ID,
    }
    PRODUCT_TIER_MAP = {
        settings.DODO_PRO_MONTHLY_PRODUCT_ID: "pro",
        settings.DODO_PRO_ANNUAL_PRODUCT_ID: "pro",
        settings.DODO_TEAM_MONTHLY_PRODUCT_ID: "team",
        settings.DODO_TEAM_ANNUAL_PRODUCT_ID: "team",
    }


def _get_client() -> DodoPayments:
    return DodoPayments(
        bearer_token=settings.DODO_PAYMENTS_API_KEY,
        environment=settings.DODO_PAYMENTS_ENVIRONMENT,
    )


def create_checkout_session(user: dict, plan: PlanType) -> str:
    """
    Create a Dodo Payments checkout session and return the checkout URL.
    """
    _init_maps()
    product_id = PLAN_PRODUCT_MAP.get(plan)
    if not product_id:
        raise ValueError(f"Unknown plan: {plan}")

    client = _get_client()
    response = client.checkout_sessions.create(
        product_cart=[{"product_id": product_id, "quantity": 1}],
        customer={"email": user["email"]},
        return_url=f"{settings.FRONTEND_URL}/billing/success",
        metadata={
            "user_id": str(user["id"]),
            "plan": plan,
        },
    )
    return response.url


def get_customer_portal_url(customer_id: str) -> str:
    """Create a customer portal session and return its URL."""
    client = _get_client()
    session = client.customers.customer_portal.create(customer_id)
    return session.link


def verify_webhook_signature(payload: str, headers: dict[str, str]) -> bool:
    """
    Verify the Dodo Payments webhook signature using the Standard Webhooks spec.
    Headers: webhook-id, webhook-timestamp, webhook-signature
    """
    secret = settings.DODO_PAYMENTS_WEBHOOK_KEY
    if not secret:
        logger.error("DODO_PAYMENTS_WEBHOOK_KEY is not configured")
        return False

    webhook_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signature = headers.get("webhook-signature", "")

    if not all([webhook_id, timestamp, signature]):
        return False

    # Reject stale webhooks to prevent replay attacks (Standard Webhooks spec)
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > _WEBHOOK_TIMESTAMP_TOLERANCE:
            logger.warning(f"Webhook timestamp too old/future: {timestamp} (delta={abs(time.time() - ts):.0f}s)")
            return False
    except (ValueError, TypeError):
        logger.warning(f"Invalid webhook timestamp: {timestamp}")
        return False

    # Standard Webhooks: secret is base64-encoded, possibly prefixed with "whsec_"
    secret_str = secret
    if secret_str.startswith("whsec_"):
        secret_str = secret_str[6:]
    secret_bytes = base64.b64decode(secret_str)

    # Signature payload: "{webhook_id}.{timestamp}.{body}"
    to_sign = f"{webhook_id}.{timestamp}.{payload}"
    expected = hmac.new(secret_bytes, to_sign.encode("utf-8"), hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected).decode("utf-8")

    # webhook-signature may contain multiple sigs: "v1,<sig1> v1,<sig2>"
    for sig_part in signature.split(" "):
        parts = sig_part.split(",", 1)
        if len(parts) == 2 and parts[0] == "v1":
            if hmac.compare_digest(expected_b64, parts[1]):
                return True

    return False


def _tier_from_product_id(product_id: str) -> str | None:
    """Map a Dodo product ID to a user tier."""
    _init_maps()
    return PRODUCT_TIER_MAP.get(product_id)


def _is_duplicate_webhook(webhook_id: str) -> bool:
    """
    Check if a webhook has already been processed (idempotency).
    Uses Redis with a TTL. Returns False (allow processing) if Redis is unavailable.
    """
    if not webhook_id:
        return False

    try:
        from app.services.rate_limiter import _get_redis
        redis = _get_redis()
        if not redis:
            return False  # Redis unavailable — fail open

        key = f"webhook:processed:{webhook_id}"
        # SET NX returns True only if the key didn't exist (first time seeing this ID)
        is_new = redis.set(key, "1", ex=_WEBHOOK_ID_TTL, nx=True)
        if is_new:
            return False  # First time — not a duplicate
        return True  # Key already existed — duplicate
    except Exception as e:
        logger.warning(f"Redis idempotency check failed: {e}")
        return False  # Fail open


def handle_webhook_event(payload: str, headers: dict[str, str]) -> dict:
    """
    Process a Dodo Payments webhook event.
    Returns a dict with processing result.
    """
    if not verify_webhook_signature(payload, headers):
        raise PermissionError("Invalid webhook signature")

    # Idempotency: skip duplicate webhook deliveries
    webhook_id = headers.get("webhook-id", "")
    if _is_duplicate_webhook(webhook_id):
        logger.info(f"Skipping duplicate webhook: {webhook_id}")
        return {"status": "skipped", "reason": "duplicate"}

    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Webhook payload is not valid JSON: {e}")
        raise ValueError("Malformed webhook payload")
    event_type = event.get("type", "")
    data = event.get("data", {})
    sb = get_supabase()

    logger.info(f"Processing webhook event: {event_type}")

    customer = data.get("customer", {})
    customer_id = customer.get("customer_id", "")
    subscription_id = data.get("subscription_id", "")
    product_id = data.get("product_id", "")
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id", "")

    # Try to find user by metadata user_id, or by customer email
    user = None
    if user_id:
        result = sb.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            user = result.data[0]

    if not user and customer.get("email"):
        result = sb.table("users").select("*").eq("email", customer["email"]).execute()
        if result.data:
            user = result.data[0]

    if not user:
        logger.warning(f"No user found for webhook event {event_type}")
        return {"status": "skipped", "reason": "user_not_found"}

    update_data: dict = {}

    if customer_id:
        update_data["payment_customer_id"] = customer_id
    if subscription_id:
        update_data["payment_subscription_id"] = subscription_id

    if event_type in ("subscription.active", "subscription.renewed"):
        tier = _tier_from_product_id(product_id)
        if tier:
            update_data["tier"] = tier
        elif event_type == "subscription.active":
            logger.warning(f"Unknown product_id {product_id}, defaulting to pro")
            update_data["tier"] = "pro"

    elif event_type == "subscription.plan_changed":
        tier = _tier_from_product_id(product_id)
        if tier:
            update_data["tier"] = tier

    elif event_type in ("subscription.cancelled", "subscription.expired"):
        update_data["tier"] = "free"
        update_data["payment_subscription_id"] = None

    elif event_type == "subscription.on_hold":
        update_data["subscription_status"] = "on_hold"

    elif event_type == "payment.failed":
        update_data["subscription_status"] = "payment_failed"

    if update_data:
        sb.table("users").update(update_data).eq("id", user["id"]).execute()
        logger.info(f"Updated user {user['id']}: {update_data}")

    return {"status": "processed", "event_type": event_type, "user_id": user["id"]}


def get_subscription_status(user: dict) -> dict:
    """Return subscription info for a user."""
    return {
        "tier": user.get("tier", "free"),
        "payment_customer_id": user.get("payment_customer_id"),
        "payment_subscription_id": user.get("payment_subscription_id"),
        "subscription_status": user.get("subscription_status"),
    }
