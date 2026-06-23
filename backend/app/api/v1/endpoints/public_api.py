import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rate_limit import enforce_rate_limit
from app.models.public_api import PublicApiKey
from app.services.public_api_service import (
    get_aggregate_stats,
    get_public_outages,
    get_public_predictions,
    register_key,
)

router = APIRouter()


async def _verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    result = await db.execute(select(PublicApiKey).where(PublicApiKey.key_hash == key_hash, PublicApiKey.is_active))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    if response is not None:
        await enforce_rate_limit(str(key.id), key.rate_limit_per_minute, key.rate_limit_per_day, response)
    return key


@router.get("/outages")
async def public_outages(
    country_code: str | None = Query(None, max_length=3),
    h3_index: str | None = Query(None, max_length=15),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    api_key: PublicApiKey = Depends(_verify_api_key),
):
    return await get_public_outages(country_code, h3_index, date_from, date_to, limit, db)


@router.get("/predictions/{h3_index}")
async def public_predictions(
    h3_index: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    api_key: PublicApiKey = Depends(_verify_api_key),
):
    return await get_public_predictions(h3_index, limit, db)


@router.get("/stats/{country_code}")
async def public_aggregate_stats(
    country_code: str,
    db: AsyncSession = Depends(get_db),
    api_key: PublicApiKey = Depends(_verify_api_key),
):
    return await get_aggregate_stats(country_code, db)


class RegisterKeyRequest(BaseModel):
    organization: str
    email: EmailStr
    tier: str = "ngo"


@router.post("/keys/register")
async def register_public_key(body: RegisterKeyRequest, db: AsyncSession = Depends(get_db)):
    raw_key, key_record = await register_key(body.organization, body.email, body.tier, db)
    await db.commit()
    return {
        "api_key": raw_key,
        "key_prefix": key_record.key_prefix,
        "tier": key_record.tier,
        "rate_limit_per_minute": key_record.rate_limit_per_minute,
        "warning": "Store this key securely — it will not be shown again.",
    }


# ── API Usage Analytics (Feature 16) ─────────────────────────────────────────

@router.get("/me/analytics")
async def my_api_analytics(
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    api_key: PublicApiKey = Depends(_verify_api_key),
):
    """Usage dashboard for API key holders — daily counts, endpoint breakdown, response times."""
    from app.models.public_api import PublicApiUsage

    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (await db.execute(
        select(PublicApiUsage).where(
            PublicApiUsage.api_key_id == api_key.id,
            PublicApiUsage.called_at >= since,
        ).order_by(PublicApiUsage.called_at.asc())
    )).scalars().all()

    daily: dict = defaultdict(int)
    endpoint_counts: dict = defaultdict(int)
    response_times: list = []
    error_count = 0

    for row in rows:
        day_key = row.called_at.strftime("%Y-%m-%d")
        daily[day_key] += 1
        endpoint_counts[row.endpoint] += 1
        if row.response_time_ms is not None:
            response_times.append(row.response_time_ms)
        if row.status_code and row.status_code >= 400:
            error_count += 1

    total_requests = len(rows)
    avg_response_ms = round(sum(response_times) / len(response_times), 1) if response_times else None

    endpoint_breakdown = [
        {"endpoint": ep, "requests": count, "pct": round(count / total_requests * 100, 1) if total_requests else 0}
        for ep, count in sorted(endpoint_counts.items(), key=lambda x: -x[1])
    ]

    rate_limit_headroom = {
        "per_minute": api_key.rate_limit_per_minute,
        "per_day": api_key.rate_limit_per_day,
        "used_today": daily.get(datetime.now(timezone.utc).strftime("%Y-%m-%d"), 0),
        "remaining_today": max(0, api_key.rate_limit_per_day - daily.get(datetime.now(timezone.utc).strftime("%Y-%m-%d"), 0)),
    }

    return {
        "api_key_prefix": api_key.key_prefix,
        "organization": api_key.organization,
        "tier": api_key.tier,
        "period_days": days,
        "total_requests": total_requests,
        "error_count": error_count,
        "error_rate_pct": round(error_count / total_requests * 100, 1) if total_requests else 0,
        "avg_response_ms": avg_response_ms,
        "daily_counts": [{"date": d, "requests": c} for d, c in sorted(daily.items())],
        "endpoint_breakdown": endpoint_breakdown,
        "rate_limit_headroom": rate_limit_headroom,
    }
