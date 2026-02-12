"""
Auth dependencies for FastAPI — validates Supabase JWT tokens
and provides current user info to endpoints.
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Header

from app.core.database import get_supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_current_user(authorization: str = Header(None, description="Bearer <supabase_access_token>")) -> dict:
    """
    FastAPI dependency that validates the Supabase access token
    and returns the user record from the users table.

    Usage:
        @router.get("/protected")
        async def endpoint(user: dict = Depends(get_current_user)):
            user_id = user["id"]
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")

    try:
        # Use Supabase client with the user's token to get their identity
        from supabase import create_client
        user_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        # Verify token by getting user from Supabase Auth
        auth_response = user_client.auth.get_user(token)
        supabase_user = auth_response.user

        if not supabase_user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch or create user in our users table
    sb = get_supabase()  # service role client
    user_id = supabase_user.id
    email = supabase_user.email or ""
    user_meta = supabase_user.user_metadata or {}
    name = user_meta.get("full_name", user_meta.get("name", email.split("@")[0]))
    avatar_url = user_meta.get("avatar_url", user_meta.get("picture"))
    google_id = user_meta.get("provider_id", user_meta.get("sub", user_id))

    # Try to find existing user
    result = sb.table("users").select("*").eq("id", user_id).execute()

    if result.data:
        return result.data[0]

    # User doesn't exist yet — create them
    new_user = {
        "id": user_id,
        "email": email,
        "name": name,
        "google_id": str(google_id),
        "avatar_url": avatar_url,
        "tier": "free",
    }

    try:
        insert_result = sb.table("users").insert(new_user).execute()
        return insert_result.data[0]
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        # Retry fetch in case of race condition
        result = sb.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]
        raise HTTPException(status_code=500, detail="Failed to create user account")


def require_tier(*allowed_tiers: str):
    """
    Dependency factory that checks if the user's tier is in the allowed list.

    Usage:
        @router.get("/pro-feature")
        async def endpoint(user: dict = Depends(require_tier("pro", "team"))):
            ...
    """
    async def _check_tier(user: dict = Depends(get_current_user)) -> dict:
        if user.get("tier", "free") not in allowed_tiers:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Insufficient tier",
                    "current_tier": user.get("tier", "free"),
                    "required_tier": list(allowed_tiers),
                    "message": "Upgrade your plan to access this feature.",
                },
            )
        return user
    return _check_tier


# Type alias for convenience
CurrentUser = Annotated[dict, Depends(get_current_user)]
