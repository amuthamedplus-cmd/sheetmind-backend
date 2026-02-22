"""
Response cache — stores AI responses in Redis to avoid redundant API calls.

Cache key: hash of (user_id, prompt, sheet_data_hash, endpoint_type)
Default TTL: 1 hour (configurable)

Falls open: if Redis is unavailable, requests go straight to AI.
"""

import hashlib
import json
import logging
import time

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1 hour in seconds
_REDIS_RETRY_INTERVAL = 60  # seconds before retrying a failed Redis connection

_redis_client: redis.Redis | None = None
_redis_last_fail: float = 0
_redis_down_since: float = 0  # Tracks when Redis first went down


def _get_redis() -> redis.Redis | None:
    """Get Redis client. Returns None if Redis is unavailable.

    After a failed connection, skips retries for _REDIS_RETRY_INTERVAL seconds
    to avoid adding timeout latency to every request.
    """
    global _redis_client, _redis_last_fail, _redis_down_since

    if _redis_client is not None:
        return _redis_client

    # Don't retry if we recently failed
    if _redis_last_fail and (time.time() - _redis_last_fail) < _REDIS_RETRY_INTERVAL:
        return None

    try:
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            max_connections=50,
        )
        client.ping()
        _redis_client = client
        _redis_last_fail = 0
        if _redis_down_since:
            downtime = int(time.time() - _redis_down_since)
            logger.info(f"Redis cache recovered after {downtime}s of downtime")
            _redis_down_since = 0
        return _redis_client
    except Exception as e:
        _redis_last_fail = time.time()
        if not _redis_down_since:
            _redis_down_since = time.time()
            logger.error(f"Redis cache DOWN — caching disabled: {e}")
        elif time.time() - _redis_down_since > 300:
            logger.error(f"Redis cache still DOWN for {int(time.time() - _redis_down_since)}s — caching disabled")
        return None


def _make_key(user_id: str, endpoint: str, prompt: str, data: dict | list | None = None) -> str:
    """Build a deterministic cache key from request params."""
    raw = json.dumps({
        "user_id": user_id,
        "endpoint": endpoint,
        "prompt": prompt,
        "data": data,
    }, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f"cache:{endpoint}:{digest}"


def get_cached(user_id: str, endpoint: str, prompt: str, data: dict | list | None = None) -> dict | None:
    """
    Look up a cached response.

    Returns the cached dict (with content, confidence, sources, etc.) or None on miss.
    """
    r = _get_redis()
    if r is None:
        return None

    key = _make_key(user_id, endpoint, prompt, data)
    try:
        raw = r.get(key)
        if raw:
            logger.info(f"Cache HIT: {key}")
            return json.loads(raw)
        return None
    except redis.exceptions.ConnectionError as e:
        global _redis_client, _redis_last_fail
        _redis_client = None
        _redis_last_fail = time.time()
        logger.warning(f"Cache get failed (connection lost): {e}")
        return None
    except Exception as e:
        logger.warning(f"Cache get failed: {e}")
        return None


def set_cached(
    user_id: str,
    endpoint: str,
    prompt: str,
    response: dict,
    data: dict | list | None = None,
    ttl: int = CACHE_TTL,
) -> None:
    """Store a response in the cache."""
    r = _get_redis()
    if r is None:
        return

    key = _make_key(user_id, endpoint, prompt, data)
    try:
        r.setex(key, ttl, json.dumps(response, default=str))
        logger.info(f"Cache SET: {key} (TTL={ttl}s)")
    except redis.exceptions.ConnectionError as e:
        global _redis_client, _redis_last_fail
        _redis_client = None
        _redis_last_fail = time.time()
        logger.warning(f"Cache set failed (connection lost): {e}")
    except Exception as e:
        logger.warning(f"Cache set failed: {e}")


def invalidate(user_id: str, endpoint: str, prompt: str, data: dict | list | None = None) -> None:
    """Delete a specific cache entry."""
    r = _get_redis()
    if r is None:
        return

    key = _make_key(user_id, endpoint, prompt, data)
    try:
        r.delete(key)
    except Exception as e:
        logger.warning(f"Cache invalidate failed: {e}")
