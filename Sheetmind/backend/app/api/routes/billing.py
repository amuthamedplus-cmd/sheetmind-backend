"""
Billing routes — Dodo Payments checkout, webhooks, status, and portal.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.billing import (
    create_checkout_session,
    get_customer_portal_url,
    get_subscription_status,
    handle_webhook_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    plan: Literal["pro_monthly", "pro_annual", "team_monthly", "team_annual"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class StatusResponse(BaseModel):
    tier: str
    payment_customer_id: str | None
    payment_subscription_id: str | None
    subscription_status: str | None


class PortalResponse(BaseModel):
    portal_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(body: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Create a Dodo Payments checkout session for the chosen plan."""
    try:
        url = create_checkout_session(user, body.plan)
        return CheckoutResponse(checkout_url=url)
    except ValueError as e:
        logger.warning(f"Checkout validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid checkout request. Please try again.")
    except Exception as e:
        logger.error(f"Checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook")
async def webhook(request: Request):
    """Receive and process Dodo Payments webhook events."""
    payload = await request.body()
    payload_str = payload.decode("utf-8")

    headers = {
        "webhook-id": request.headers.get("webhook-id", ""),
        "webhook-signature": request.headers.get("webhook-signature", ""),
        "webhook-timestamp": request.headers.get("webhook-timestamp", ""),
    }

    try:
        result = handle_webhook_event(payload_str, headers)
        return result
    except PermissionError:
        logger.warning(
            f"Webhook signature verification failed | "
            f"webhook-id={headers.get('webhook-id', 'missing')} | "
            f"webhook-timestamp={headers.get('webhook-timestamp', 'missing')} | "
            f"payload_bytes={len(payload)}"
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except Exception as e:
        logger.error(
            f"Webhook processing failed | "
            f"webhook-id={headers.get('webhook-id', 'missing')} | "
            f"error={e}"
        )
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/status", response_model=StatusResponse)
async def status(user: dict = Depends(get_current_user)):
    """Return current subscription info for the authenticated user."""
    info = get_subscription_status(user)
    return StatusResponse(**info)


@router.post("/portal", response_model=PortalResponse)
async def portal(user: dict = Depends(get_current_user)):
    """Create a Dodo Payments customer portal session."""
    customer_id = user.get("payment_customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No payment account found. Please subscribe to a plan first.",
        )
    try:
        url = get_customer_portal_url(customer_id)
        return PortalResponse(portal_url=url)
    except Exception as e:
        logger.error(f"Customer portal creation failed for customer {customer_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session. Please try again.")
