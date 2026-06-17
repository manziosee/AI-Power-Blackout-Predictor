"""Neighborhood Resilience Score endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.resilience import ResilienceScore
from app.models.user import User
from app.services.resilience_service import compute_score, get_or_compute

router = APIRouter()


class ResilienceOut(BaseModel):
    h3_index: str
    score: float
    grade: str | None
    outages_30d: int
    avg_duration_minutes: float | None
    outage_frequency_score: float | None
    avg_duration_score: float | None
    prediction_accuracy_score: float | None
    report_participation_score: float | None

    model_config = {"from_attributes": True}


@router.get("/top", response_model=List[ResilienceOut])
async def top_resilient(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ResilienceScore).order_by(ResilienceScore.score.desc()).limit(20)
    )
    return result.scalars().all()


@router.get("/bottom", response_model=List[ResilienceOut])
async def worst_resilient(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ResilienceScore).order_by(ResilienceScore.score.asc()).limit(20)
    )
    return result.scalars().all()


@router.get("/{h3_index}", response_model=ResilienceOut)
async def get_resilience(
    h3_index: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rs = await get_or_compute(h3_index, db)
    if rs is None:
        raise HTTPException(status_code=404, detail="No resilience data")
    return rs


@router.post("/compute/{h3_index}")
async def trigger_compute(
    h3_index: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    score = await compute_score(h3_index, db)
    await db.commit()
    return {"h3_index": h3_index, "score": score}
