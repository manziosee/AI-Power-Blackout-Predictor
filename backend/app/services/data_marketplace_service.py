"""Service for data marketplace."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outage import OutageReport

_VALID_DATA_TYPES = {"outage_history", "predictions", "resilience", "weather_correlation"}


def validate_request(data_type: str, date_from: datetime, date_to: datetime) -> str | None:
    if data_type not in _VALID_DATA_TYPES:
        return f"Invalid data_type. Must be one of: {', '.join(_VALID_DATA_TYPES)}"
    if date_from >= date_to:
        return "date_from must be before date_to"
    if (date_to - date_from).days > 365:
        return "Date range cannot exceed 365 days"
    return None


async def get_public_preview(h3_index: str, db: AsyncSession) -> dict:
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)

    count_result = await db.execute(
        select(func.count()).where(
            OutageReport.h3_index == h3_index,
            OutageReport.reported_at >= since_30d,
        )
    )
    outage_count = count_result.scalar() or 0

    dur_result = await db.execute(
        select(func.avg(OutageReport.duration_minutes)).where(
            OutageReport.h3_index == h3_index,
            OutageReport.duration_minutes.is_not(None),
        )
    )
    avg_dur = dur_result.scalar()

    if outage_count == 0:
        risk_level = "low"
    elif outage_count <= 3:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "h3_index": h3_index,
        "outage_count_30d": outage_count,
        "avg_duration_minutes": round(avg_dur, 1) if avg_dur else None,
        "risk_level": risk_level,
    }
