"""Redis sliding-window rate limiters — public API and auth endpoints."""
from __future__ import annotations

import logging
import time
import uuid

import redis.asyncio as aioredis
from fastapi import HTTPException, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

_MINUTE_MS = 60_000
_DAY_MS = 86_400_000


async def enforce_rate_limit(
    key_id: str,
    rate_per_minute: int,
    rate_per_day: int,
    response: Response,
) -> None:
    """Enforce sliding-window rate limits using Redis sorted sets.

    Raises HTTP 429 if either limit is exceeded.
    Silently allows the request when Redis is unavailable (fail-open).
    """
    now_ms = int(time.time() * 1000)
    member = f"{now_ms}:{uuid.uuid4().hex[:8]}"

    try:
        async with aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1) as r:
            pipe = r.pipeline()

            min_key = f"rl:min:{key_id}"
            pipe.zadd(min_key, {member: now_ms})
            pipe.zremrangebyscore(min_key, 0, now_ms - _MINUTE_MS)
            pipe.zcard(min_key)
            pipe.expire(min_key, 60)

            day_key = f"rl:day:{key_id}"
            pipe.zadd(day_key, {member + "d": now_ms})
            pipe.zremrangebyscore(day_key, 0, now_ms - _DAY_MS)
            pipe.zcard(day_key)
            pipe.expire(day_key, 86400)

            results = await pipe.execute()

        min_count: int = results[2]
        day_count: int = results[6]

        response.headers["X-RateLimit-Limit-Minute"] = str(rate_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, rate_per_minute - min_count))
        response.headers["X-RateLimit-Limit-Day"] = str(rate_per_day)
        response.headers["X-RateLimit-Remaining-Day"] = str(max(0, rate_per_day - day_count))

        if min_count > rate_per_minute:
            response.headers["Retry-After"] = "60"
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {rate_per_minute} requests/minute. Retry after 60s.",
                headers={"Retry-After": "60"},
            )
        if day_count > rate_per_day:
            response.headers["Retry-After"] = "86400"
            raise HTTPException(
                status_code=429,
                detail=f"Daily rate limit exceeded: {rate_per_day} requests/day.",
                headers={"Retry-After": "86400"},
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Rate limit Redis unavailable — allowing request: {exc}")


# Per-IP limits for sensitive auth endpoints
_AUTH_MINUTE_LIMIT = 10   # max 10 attempts per minute per IP
_AUTH_HOUR_LIMIT = 30     # max 30 attempts per hour per IP
_HOUR_MS = 3_600_000


async def enforce_auth_rate_limit(client_ip: str) -> None:
    """Brute-force protection for register/login/OTP endpoints.

    Raises HTTP 429 after 10 attempts/minute or 30 attempts/hour from the same IP.
    Fail-open when Redis is unavailable.
    Disabled entirely in test environment to avoid flaky rate-limit failures.
    """
    if settings.ENVIRONMENT == "test":
        return
    now_ms = int(time.time() * 1000)
    member = f"{now_ms}:{uuid.uuid4().hex[:8]}"

    try:
        async with aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1) as r:
            pipe = r.pipeline()

            min_key = f"auth:min:{client_ip}"
            pipe.zadd(min_key, {member: now_ms})
            pipe.zremrangebyscore(min_key, 0, now_ms - _MINUTE_MS)
            pipe.zcard(min_key)
            pipe.expire(min_key, 60)

            hour_key = f"auth:hour:{client_ip}"
            pipe.zadd(hour_key, {member + "h": now_ms})
            pipe.zremrangebyscore(hour_key, 0, now_ms - _HOUR_MS)
            pipe.zcard(hour_key)
            pipe.expire(hour_key, 3600)

            results = await pipe.execute()

        min_count: int = results[2]
        hour_count: int = results[6]

        if min_count > _AUTH_MINUTE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many authentication attempts. Try again in 60 seconds.",
                headers={"Retry-After": "60"},
            )
        if hour_count > _AUTH_HOUR_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many authentication attempts. Try again in 1 hour.",
                headers={"Retry-After": "3600"},
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Auth rate limit Redis unavailable — allowing request: {exc}")
