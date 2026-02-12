"""
Rate limiter — per-user, per-minute request limiting using Redis.

Tier limits:
  - Free: 5 requests/minute
  - Pro: 20 requests/minute
  - Team: 50 requests/minute
"""

import time
import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

RATE_LIMITS = {
    "free": 5,
    "pro": 20,
    "team": 50,
}

WINDOW_SECONDS = 60
_REDIS_RETRY_INTERVAL = 60  # seconds before retrying a failed connection

_redis_client: redis.Redis | None = None
_redis_last_fail: float = 0


def _get_redis() -> redis.Redis | None:
    """Get Redis client. Returns None if Redis is unavailable.

    After a failed connection, skips retries for _REDIS_RETRY_INTERVAL seconds
    to avoid adding timeout latency to every request.
    """
    global _redis_client, _redis_last_fail

    if _redis_client is not None:
        return _redis_client

    # Don't retry if we recently failed
    if _redis_last_fail and (time.time() - _redis_last_fail) < _REDIS_RETRY_INTERVAL:
        return None

    try:
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
        client.ping()
        _redis_client = client
        _redis_last_fail = 0
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable, rate limiting disabled: {e}")
        _redis_last_fail = time.time()
        return None


def check_rate_limit(user_id: str, tier: str = "free") -> dict:
    """
    Check if the user is within their per-minute rate limit.

    Returns:
        {
            "allowed": bool,
            "limit": int,
            "remaining": int,
            "retry_after": int | None,  # seconds until window resets
        }
    """
    r = _get_redis()
    if r is None:
        # If Redis is down, allow the request (fail open)
        limit = RATE_LIMITS.get(tier, 5)
        return {"allowed": True, "limit": limit, "remaining": limit, "retry_after": None}

    limit = RATE_LIMITS.get(tier, 5)
    key = f"rate:{user_id}:{int(time.time()) // WINDOW_SECONDS}"

    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS)
        results = pipe.execute()

        current_count = results[0]
        remaining = max(0, limit - current_count)
        allowed = current_count <= limit

        retry_after = None
        if not allowed:
            ttl = r.ttl(key)
            retry_after = ttl if ttl > 0 else WINDOW_SECONDS

        return {
            "allowed": allowed,
            "limit": limit,
            "remaining": remaining,
            "retry_after": retry_after,
        }
    except Exception as e:
        logger.warning(f"Rate limit check failed, allowing request: {e}")
        return {"allowed": True, "limit": limit, "remaining": limit, "retry_after": None}
