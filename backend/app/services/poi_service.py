"""Service for POI (ATM / fuel station) status layer."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.poi import PoiLocation, PoiStatusReport


async def get_pois_in_cell(
    h3_index: str, db: AsyncSession, poi_type: str | None = None
) -> list:
    query = select(PoiLocation).where(PoiLocation.h3_index == h3_index)
    if poi_type:
        query = query.where(PoiLocation.poi_type == poi_type)
    result = await db.execute(query.order_by(PoiLocation.name))
    return result.scalars().all()


async def record_report(
    poi_id: uuid.UUID,
    user_id: uuid.UUID,
    is_operational: bool,
    notes: str | None,
    db: AsyncSession,
) -> PoiStatusReport:
    poi_result = await db.execute(select(PoiLocation).where(PoiLocation.id == poi_id))
    poi = poi_result.scalar_one_or_none()
    if poi is None:
        raise ValueError(f"POI {poi_id} not found")

    report = PoiStatusReport(
        poi_id=poi_id,
        user_id=user_id,
        is_operational=is_operational,
        notes=notes,
    )
    db.add(report)

    # Update counters
    if is_operational:
        poi.reports_up = (poi.reports_up or 0) + 1
    else:
        poi.reports_down = (poi.reports_down or 0) + 1
    poi.last_reported_at = datetime.now(timezone.utc)

    # Majority of last 5 reports determines operational status
    recent_result = await db.execute(
        select(PoiStatusReport.is_operational)
        .where(PoiStatusReport.poi_id == poi_id)
        .order_by(PoiStatusReport.reported_at.desc())
        .limit(5)
    )
    recent = [r[0] for r in recent_result.all()]
    recent.append(is_operational)  # include current one
    if recent:
        poi.is_operational = sum(recent) > len(recent) / 2

    await db.flush()
    return report
