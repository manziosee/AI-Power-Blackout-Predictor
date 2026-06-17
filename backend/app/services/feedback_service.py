"""Service for prediction feedback loop."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction_feedback import PredictionFeedback
from app.models.user import User, UserLocation


async def schedule_feedback(
    prediction_id: uuid.UUID,
    h3_index: str,
    user_ids: list[uuid.UUID],
    db: AsyncSession,
) -> None:
    """Create PredictionFeedback rows and schedule SMS send via Celery."""
    for uid in user_ids:
        fb = PredictionFeedback(
            prediction_id=prediction_id,
            user_id=uid,
            h3_index=h3_index,
        )
        db.add(fb)
    await db.flush()

    # Schedule Celery tasks (import inside to avoid circular imports)
    from app.tasks.feedback_followup import send_feedback_sms  # noqa: F401
    # Tasks would be called here with .apply_async(countdown=14400)


async def record_response(phone: str, response: str, db: AsyncSession) -> bool:
    """Look up user by phone, find pending feedback, record outage_occurred."""
    user_result = await db.execute(select(User).where(User.phone == phone))
    user = user_result.scalar_one_or_none()
    if not user:
        return False

    normalized = response.strip().upper()
    outage_occurred = normalized in ("YES", "OUI", "NDIYO", "نعم", "SÍ", "SIM")
    if normalized not in ("YES", "NO", "OUI", "NON", "NDIYO", "HAPANA", "نعم", "لا", "SÍ", "NO", "SIM", "NÃO"):
        return False

    # Find pending feedback for this user's cells
    loc_result = await db.execute(
        select(UserLocation).where(UserLocation.user_id == user.id, UserLocation.is_active)
    )
    locations = loc_result.scalars().all()
    h3_cells = [loc.h3_index for loc in locations]

    if not h3_cells:
        return False

    fb_result = await db.execute(
        select(PredictionFeedback).where(
            PredictionFeedback.user_id == user.id,
            PredictionFeedback.h3_index.in_(h3_cells),
            PredictionFeedback.outage_occurred.is_(None),
        )
    )
    feedbacks = fb_result.scalars().all()
    if not feedbacks:
        return False

    now = datetime.now(timezone.utc)
    for fb in feedbacks:
        fb.outage_occurred = outage_occurred
        fb.response_received_at = now
    await db.flush()
    return True


async def get_accuracy(h3_index: str, db: AsyncSession) -> dict:
    """Aggregate feedback stats for a cell."""
    total_result = await db.execute(
        select(func.count()).where(
            PredictionFeedback.h3_index == h3_index,
            PredictionFeedback.outage_occurred.is_not(None),
        )
    )
    total = total_result.scalar() or 0

    if total == 0:
        return {"total_feedback": 0, "outage_occurred_pct": None, "accuracy": None}

    occurred_result = await db.execute(
        select(func.count()).where(
            PredictionFeedback.h3_index == h3_index,
            PredictionFeedback.outage_occurred.is_(True),
        )
    )
    occurred = occurred_result.scalar() or 0
    pct = round(occurred / total * 100, 1)
    return {"total_feedback": total, "outage_occurred_pct": pct, "accuracy": pct}
