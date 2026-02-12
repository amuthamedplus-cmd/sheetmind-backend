"""
Usage tracking service — tracks per-user, per-month usage
and enforces tier-based limits.

Free tier: 5 lifetime trial messages (not monthly)
Pro tier: 1000 messages per month
Team tier: Unlimited
"""

import logging
from datetime import date

from fastapi import HTTPException

from app.core.database import get_supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Free users get N LIFETIME trial messages (configurable)
FREE_TRIAL_LIMIT = settings.FREE_TRIAL_LIMIT

# Monthly limits for paid tiers
TIER_LIMITS = {
    "free": FREE_TRIAL_LIMIT,  # Lifetime limit for free
    "pro": 1000,               # Monthly limit
    "team": 999999,            # Effectively unlimited
}


def _get_current_period() -> str:
    """Return the first day of the current month as ISO string."""
    return date.today().replace(day=1).isoformat()


def get_trial_usage(user_id: str) -> dict:
    """
    Get LIFETIME trial usage for free tier users.

    Returns:
        {
            "total_used": int,
            "limit": 5,
            "remaining": int,
        }
    """
    sb = get_supabase()

    # Get ALL usage records for this user (not just current month)
    result = sb.table("usage_records") \
        .select("query_count, formula_count, chat_count") \
        .eq("user_id", user_id) \
        .execute()

    total_used = 0
    if result.data:
        for record in result.data:
            total_used += record.get("query_count", 0)
            total_used += record.get("formula_count", 0)
            total_used += record.get("chat_count", 0)

    return {
        "total_used": total_used,
        "limit": FREE_TRIAL_LIMIT,
        "remaining": max(0, FREE_TRIAL_LIMIT - total_used),
    }


def get_usage(user_id: str, tier: str = "free") -> dict:
    """
    Get current usage stats for a user.

    For FREE tier: Returns LIFETIME usage (5 total trials)
    For PRO/TEAM: Returns MONTHLY usage

    Returns:
        {
            "period": "2026-01-01" or "lifetime",
            "query_count": int,
            "formula_count": int,
            "chat_count": int,
            "total_used": int,
            "limit": int,
            "remaining": int,
            "is_trial": bool,
        }
    """
    sb = get_supabase()

    # FREE TIER: Check lifetime trial usage
    if tier == "free":
        trial_usage = get_trial_usage(user_id)
        return {
            "period": "lifetime",
            "query_count": 0,  # Not tracked separately for trials
            "formula_count": 0,
            "chat_count": trial_usage["total_used"],
            "total_used": trial_usage["total_used"],
            "limit": FREE_TRIAL_LIMIT,
            "remaining": trial_usage["remaining"],
            "is_trial": True,
        }

    # PRO/TEAM: Check monthly usage
    period = _get_current_period()

    result = sb.table("usage_records") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("period", period) \
        .execute()

    if result.data:
        record = result.data[0]
        query_count = record["query_count"]
        formula_count = record["formula_count"]
        chat_count = record["chat_count"]
    else:
        query_count = 0
        formula_count = 0
        chat_count = 0

    total_used = query_count + formula_count + chat_count
    limit = TIER_LIMITS.get(tier, 1000)

    return {
        "period": period,
        "query_count": query_count,
        "formula_count": formula_count,
        "chat_count": chat_count,
        "total_used": total_used,
        "limit": limit,
        "remaining": max(0, limit - total_used),
        "is_trial": False,
    }


def check_limit(user_id: str, tier: str = "free") -> None:
    """
    Check if user has remaining quota. Raises 402 if limit exceeded.

    For FREE tier: Checks lifetime trial limit (5 messages total)
    For PRO/TEAM: Checks monthly limit
    """
    usage = get_usage(user_id, tier)

    if usage["remaining"] <= 0:
        if tier == "free" or usage.get("is_trial"):
            # Trial expired message
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Trial limit exceeded",
                    "total_used": usage["total_used"],
                    "limit": usage["limit"],
                    "tier": tier,
                    "is_trial": True,
                    "message": f"You've used all {usage['limit']} free trial messages. "
                               f"Upgrade to Pro for 1,000 messages per month!",
                    "upgrade_url": "/pricing",
                },
            )
        else:
            # Monthly limit exceeded for paid users
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Usage limit exceeded",
                    "total_used": usage["total_used"],
                    "limit": usage["limit"],
                    "tier": tier,
                    "is_trial": False,
                    "message": f"You've used all {usage['limit']} messages for this month. "
                               f"Your quota resets next month, or upgrade for more.",
                },
            )

    # Log remaining for free tier users
    if tier == "free":
        logger.info(f"User {user_id[:8]}... has {usage['remaining']}/{usage['limit']} trial messages remaining")


def increment_usage(user_id: str, usage_type: str) -> None:
    """
    Increment usage counter for the current period.

    Args:
        user_id: The user's UUID string.
        usage_type: One of "chat_count", "formula_count", "query_count".
    """
    if usage_type not in ("chat_count", "formula_count", "query_count"):
        raise ValueError(f"Invalid usage_type: {usage_type}")

    sb = get_supabase()
    period = _get_current_period()

    # Try to find existing record for this period
    result = sb.table("usage_records") \
        .select("id", usage_type) \
        .eq("user_id", user_id) \
        .eq("period", period) \
        .execute()

    if result.data:
        # Update existing record
        record = result.data[0]
        new_count = record[usage_type] + 1
        sb.table("usage_records") \
            .update({usage_type: new_count}) \
            .eq("id", record["id"]) \
            .execute()
    else:
        # Create new record for this period
        new_record = {
            "user_id": user_id,
            "period": period,
            "query_count": 0,
            "formula_count": 0,
            "chat_count": 0,
        }
        new_record[usage_type] = 1
        sb.table("usage_records").insert(new_record).execute()
