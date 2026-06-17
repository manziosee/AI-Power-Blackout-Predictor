"""Prepaid Meter Integration endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.prepaid import PrepaidMeter
from app.models.user import User

router = APIRouter()


class MeterCreate(BaseModel):
    meter_number: str
    provider: str | None = None
    h3_index: str
    low_balance_threshold_kwh: float = 10.0
    alert_before_hours: int = 12


class MeterUpdate(BaseModel):
    last_balance_kwh: float | None = None
    low_balance_threshold_kwh: float | None = None
    alert_before_hours: int | None = None
    is_active: bool | None = None


class MeterOut(BaseModel):
    id: uuid.UUID
    meter_number: str
    provider: str | None
    h3_index: str
    last_balance_kwh: float | None
    low_balance_threshold_kwh: float
    alert_before_hours: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/meters", response_model=MeterOut, status_code=201)
async def register_meter(
    payload: MeterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meter = PrepaidMeter(
        user_id=current_user.id,
        meter_number=payload.meter_number,
        provider=payload.provider,
        h3_index=payload.h3_index,
        low_balance_threshold_kwh=payload.low_balance_threshold_kwh,
        alert_before_hours=payload.alert_before_hours,
    )
    db.add(meter)
    await db.flush()
    await db.commit()
    return meter


@router.get("/meters", response_model=List[MeterOut])
async def list_meters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PrepaidMeter).where(PrepaidMeter.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/meters/{meter_id}", response_model=MeterOut)
async def get_meter(
    meter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PrepaidMeter).where(
            PrepaidMeter.id == meter_id,
            PrepaidMeter.user_id == current_user.id,
        )
    )
    meter = result.scalar_one_or_none()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    return meter


@router.put("/meters/{meter_id}", response_model=MeterOut)
async def update_meter(
    meter_id: uuid.UUID,
    payload: MeterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PrepaidMeter).where(
            PrepaidMeter.id == meter_id,
            PrepaidMeter.user_id == current_user.id,
        )
    )
    meter = result.scalar_one_or_none()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meter, field, value)
    await db.flush()
    await db.commit()
    return meter


@router.delete("/meters/{meter_id}", status_code=204)
async def delete_meter(
    meter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PrepaidMeter).where(
            PrepaidMeter.id == meter_id,
            PrepaidMeter.user_id == current_user.id,
        )
    )
    meter = result.scalar_one_or_none()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    await db.delete(meter)
    await db.flush()
    await db.commit()
