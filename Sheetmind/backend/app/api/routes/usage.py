from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.services.usage import get_usage, FREE_TRIAL_LIMIT

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/stats")
async def get_usage_stats(user: dict = Depends(get_current_user)):
    """
    Get usage statistics for the current user.

    For FREE tier users:
    - Returns lifetime trial usage (5 total messages)
    - is_trial: true
    - Shows remaining free messages

    For PRO/TEAM users:
    - Returns monthly usage
    - is_trial: false
    - Shows remaining messages for current month
    """
    user_id = user["id"]
    tier = user.get("tier", "free")

    usage = get_usage(user_id, tier)
    usage["tier"] = tier
    usage["user_email"] = user.get("email", "")
    usage["user_name"] = user.get("name", "")

    # Add helpful messages for frontend
    if tier == "free":
        remaining = usage["remaining"]
        if remaining > 0:
            usage["status_message"] = f"You have {remaining} free trial message{'s' if remaining != 1 else ''} remaining"
        else:
            usage["status_message"] = "Your free trial has ended. Upgrade to Pro for unlimited access!"
            usage["show_upgrade"] = True
    else:
        usage["status_message"] = f"{usage['remaining']} messages remaining this month"

    return usage


@router.get("/trial")
async def get_trial_status(user: dict = Depends(get_current_user)):
    """
    Get trial status for the current user.

    Returns:
        - is_trial: Whether user is on free trial
        - trial_limit: Total trial messages (5)
        - trial_used: Messages used
        - trial_remaining: Messages left
        - trial_expired: Whether trial is exhausted
    """
    user_id = user["id"]
    tier = user.get("tier", "free")

    usage = get_usage(user_id, tier)

    if tier == "free":
        return {
            "is_trial": True,
            "trial_limit": FREE_TRIAL_LIMIT,
            "trial_used": usage["total_used"],
            "trial_remaining": usage["remaining"],
            "trial_expired": usage["remaining"] <= 0,
            "upgrade_message": "Upgrade to Pro for 1,000 messages per month!" if usage["remaining"] <= 0 else None,
        }
    else:
        return {
            "is_trial": False,
            "tier": tier,
            "monthly_limit": usage["limit"],
            "monthly_used": usage["total_used"],
            "monthly_remaining": usage["remaining"],
        }
