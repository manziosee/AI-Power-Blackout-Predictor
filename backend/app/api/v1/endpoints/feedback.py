"""Prediction Feedback Loop endpoints."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.prediction_feedback import PredictionFeedback
from app.models.user import User
from app.services.feedback_service import get_accuracy, record_response

router = APIRouter()


class FeedbackResponse(BaseModel):
    phone: str
    response: str


@router.post("/respond")
async def respond_to_feedback(
    payload: FeedbackResponse,
    db: AsyncSession = Depends(get_db),
):
    ok = await record_response(payload.phone, payload.response, db)
    if not ok:
        raise HTTPException(status_code=400, detail="Could not record response. Check phone number and response value.")
    await db.commit()
    return {"status": "recorded"}


@router.get("/accuracy/{h3_index}")
async def feedback_accuracy(
    h3_index: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_accuracy(h3_index, db)


@router.get("/pending")
async def pending_feedbacks(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=8)
    result = await db.execute(
        select(PredictionFeedback).where(
            PredictionFeedback.outage_occurred.is_(None),
            PredictionFeedback.created_at <= cutoff,
        ).order_by(PredictionFeedback.created_at)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "h3_index": r.h3_index,
            "user_id": str(r.user_id) if r.user_id else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
