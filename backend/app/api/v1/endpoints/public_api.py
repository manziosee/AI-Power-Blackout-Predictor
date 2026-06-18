import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.public_api import PublicApiKey
from app.services.public_api_service import (
    get_aggregate_stats,
    get_public_outages,
    get_public_predictions,
    register_key,
)

router = APIRouter()


async def _verify_api_key(x_api_key: str = Header(..., alias="X-API-Key"), db: AsyncSession = Depends(get_db)):
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    result = await db.execute(select(PublicApiKey).where(PublicApiKey.key_hash == key_hash, PublicApiKey.is_active))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
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
