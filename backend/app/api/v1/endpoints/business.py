"""Business Impact Score endpoints."""
import uuid as _uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enterprise import BusinessProfile
from app.models.user import User
from app.services.business_impact_service import BUSINESS_TYPE_LABELS, compute_impact, get_area_impact

router = APIRouter(prefix="/business", tags=["business"])


class BusinessProfileCreate(BaseModel):
    h3_index: str
    business_type: str
    name: str | None = None
    monthly_revenue_usd: float | None = None
    employees: int | None = None


class BusinessProfileOut(BaseModel):
    id: _uuid.UUID
    h3_index: str
    business_type: str
    name: str | None
    monthly_revenue_usd: float | None
    employees: int | None

    model_config = {"from_attributes": True}


@router.post("/profile", response_model=BusinessProfileOut, status_code=201)
async def create_profile(
    payload: BusinessProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register your business to get a personalised impact score."""
    profile = BusinessProfile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    await db.flush()
    return profile


@router.get("/profile", response_model=list[BusinessProfileOut])
async def list_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BusinessProfile).where(BusinessProfile.user_id == current_user.id))
    return result.scalars().all()


@router.get("/impact/me")
async def my_impact(
    duration_hours: float = Query(default=2.0, ge=0.5, le=24.0),
    probability: float = Query(default=0.70, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute impact score for the current user's registered businesses."""
    result = await db.execute(select(BusinessProfile).where(BusinessProfile.user_id == current_user.id))
    profiles = result.scalars().all()

    if not profiles:
        return {
            "message": "No business profile registered. POST /business/profile to get a personalised score.",
            "types_available": list(BUSINESS_TYPE_LABELS.keys()),
        }

    return [
        compute_impact(
            p.business_type,
            current_user.country_code,
            duration_hours,
            probability,
            p.monthly_revenue_usd,
        )
        for p in profiles
    ]


@router.get("/impact/area/{h3_index}")
async def area_impact(
    h3_index: str,
    country_code: str = Query(...),
):
    """Get estimated financial impact of an outage for all businesses in an H3 cell."""
    return await get_area_impact(h3_index, country_code)


@router.get("/impact/estimate")
async def quick_estimate(
    business_type: str = Query(..., description="shop|restaurant|office|factory|hospital|other"),
    country_code: str = Query(...),
    duration_hours: float = Query(default=2.0, ge=0.5, le=24.0),
    probability: float = Query(default=0.70, ge=0.0, le=1.0),
    monthly_revenue_usd: float | None = Query(default=None),
):
    """Quick impact estimate without a registered profile — no auth required."""
    return compute_impact(business_type, country_code, duration_hours, probability, monthly_revenue_usd)
