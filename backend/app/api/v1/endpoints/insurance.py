"""Parametric Outage Insurance endpoints."""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.insurance import InsuranceClaim, InsurancePolicy
from app.models.user import User
from app.services.insurance_service import create_policy, trigger_claims_for_outage

router = APIRouter()


class PolicyCreate(BaseModel):
    h3_index: str
    premium_usd_monthly: float
    payout_usd_per_hour: float
    min_duration_hours: float = 2.0
    max_payout_usd: float
    start_date: datetime


class ClaimTrigger(BaseModel):
    h3_index: str
    outage_start: datetime
    outage_end: datetime


class PolicyOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    premium_usd_monthly: float
    payout_usd_per_hour: float
    min_duration_hours: float
    max_payout_usd: float
    insurer: str
    is_active: bool
    start_date: datetime

    model_config = {"from_attributes": True}


class ClaimOut(BaseModel):
    id: uuid.UUID
    policy_id: uuid.UUID
    h3_index: str
    outage_start: datetime
    outage_end: datetime | None
    duration_hours: float | None
    payout_usd: float | None
    status: str
    triggered_at: datetime

    model_config = {"from_attributes": True}


@router.post("/policies", response_model=PolicyOut, status_code=201)
async def create_new_policy(
    payload: PolicyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    policy = await create_policy(
        user_id=current_user.id,
        h3_index=payload.h3_index,
        premium=payload.premium_usd_monthly,
        payout_per_hour=payload.payout_usd_per_hour,
        min_hours=payload.min_duration_hours,
        max_payout=payload.max_payout_usd,
        start_date=payload.start_date,
        db=db,
    )
    await db.commit()
    return policy


@router.get("/policies", response_model=List[PolicyOut])
async def list_policies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsurancePolicy).where(InsurancePolicy.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/policies/{policy_id}", response_model=PolicyOut)
async def get_policy(
    policy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.id == policy_id,
            InsurancePolicy.user_id == current_user.id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/claims", response_model=List[ClaimOut])
async def list_claims(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsuranceClaim)
        .join(InsurancePolicy, InsurancePolicy.id == InsuranceClaim.policy_id)
        .where(InsurancePolicy.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/claims/{claim_id}", response_model=ClaimOut)
async def get_claim(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsuranceClaim)
        .join(InsurancePolicy, InsurancePolicy.id == InsuranceClaim.policy_id)
        .where(InsuranceClaim.id == claim_id, InsurancePolicy.user_id == current_user.id)
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.post("/claims/trigger")
async def trigger_claims(
    payload: ClaimTrigger,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    claims = await trigger_claims_for_outage(
        h3_index=payload.h3_index,
        outage_start=payload.outage_start,
        outage_end=payload.outage_end,
        db=db,
    )
    await db.commit()
    return {"triggered": len(claims), "claims": [str(c.id) for c in claims]}
