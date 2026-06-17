"""IVR Phone Call Alert endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.ivr import IvrCall
from app.models.user import User
from app.services.ivr_service import queue_calls_for_cell

router = APIRouter()


class IvrTrigger(BaseModel):
    h3_index: str
    risk_level: str
    probability: float


class IvrCallback(BaseModel):
    call_sid: str
    call_status: str
    duration: int | None = None


class IvrCallOut(BaseModel):
    id: uuid.UUID
    phone: str
    h3_index: str
    language: str
    risk_level: str
    probability: float
    call_status: str
    call_sid: str | None
    attempted_at: str

    model_config = {"from_attributes": True}


@router.post("/trigger")
async def trigger_ivr(
    payload: IvrTrigger,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    calls = await queue_calls_for_cell(
        h3_index=payload.h3_index,
        risk_level=payload.risk_level,
        probability=payload.probability,
        db=db,
    )
    await db.commit()
    return {"queued": len(calls), "call_ids": [str(c.id) for c in calls]}


@router.get("/logs")
async def ivr_logs(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IvrCall).order_by(IvrCall.attempted_at.desc()).limit(100)
    )
    calls = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "phone": c.phone,
            "h3_index": c.h3_index,
            "call_status": c.call_status,
            "call_sid": c.call_sid,
            "attempted_at": c.attempted_at.isoformat(),
        }
        for c in calls
    ]


@router.post("/callback")
async def ivr_callback(
    payload: IvrCallback,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IvrCall).where(IvrCall.call_sid == payload.call_sid)
    )
    call = result.scalar_one_or_none()
    if not call:
        # Try to find by queued status if no SID yet
        raise HTTPException(status_code=404, detail="Call not found")

    call.call_status = payload.call_status
    if payload.duration is not None:
        call.duration_seconds = payload.duration
    await db.flush()
    await db.commit()
    return {"status": "updated"}
