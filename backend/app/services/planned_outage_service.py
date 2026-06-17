"""Service for planned outage calendar."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planned_outage import PlannedOutage


async def get_upcoming(h3_index: str, db: AsyncSession) -> list:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PlannedOutage)
        .where(
            PlannedOutage.h3_index == h3_index,
            PlannedOutage.status != "cancelled",
            PlannedOutage.ends_at >= now,
        )
        .order_by(PlannedOutage.starts_at)
    )
    return result.scalars().all()


async def merge_with_prediction(h3_index: str, prediction: dict, db: AsyncSession) -> dict:
    outages = await get_upcoming(h3_index, db)
    prediction["planned_outages"] = [
        {
            "id": str(o.id),
            "title": o.title,
            "starts_at": o.starts_at.isoformat(),
            "ends_at": o.ends_at.isoformat(),
            "status": o.status,
        }
        for o in outages
    ]
    prediction["has_planned_outage"] = len(outages) > 0
    return prediction
