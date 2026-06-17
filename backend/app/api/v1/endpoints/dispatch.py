"""Crew Dispatch Recommendation endpoints."""
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.regulatory import DispatchRecommendation
from app.models.user import User
from app.services.dispatch_service import generate_recommendations

router = APIRouter()


class DispatchGenerate(BaseModel):
    utility_id: uuid.UUID | None = None
    crew_count: int = 1


class DispatchOut(BaseModel):
    id: uuid.UUID
    utility_id: uuid.UUID | None
    generated_at: datetime
    valid_until: datetime
    crew_count: int
    total_priority_score: float | None
    is_acknowledged: bool

    model_config = {"from_attributes": True}


@router.get("/recommend", response_model=List[DispatchOut])
async def get_recommendations(
    utility_id: uuid.UUID | None = Query(default=None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(DispatchRecommendation).order_by(DispatchRecommendation.generated_at.desc()).limit(20)
    if utility_id:
        query = query.where(DispatchRecommendation.utility_id == utility_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/recommend/generate", response_model=DispatchOut, status_code=201)
async def generate_dispatch(
    payload: DispatchGenerate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rec = await generate_recommendations(
        utility_id=payload.utility_id,
        crew_count=payload.crew_count,
        db=db,
    )
    await db.commit()
    return rec


@router.put("/recommend/{rec_id}/acknowledge", response_model=DispatchOut)
async def acknowledge(
    rec_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DispatchRecommendation).where(DispatchRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.is_acknowledged = True
    rec.acknowledged_by = current_user.id
    rec.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return rec
