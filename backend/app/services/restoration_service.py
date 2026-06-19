"""Restoration ETA tracking — lifecycle management from outage to restoration."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restoration import RestorationEvent

_STATUS_ORDER = ["reported", "acknowledged", "crew_assigned", "crew_en_route", "crew_on_site", "restored"]


async def create_restoration_event(
    outage_report_id: uuid.UUID, h3_index: str, utility_id: uuid.UUID | None, db: AsyncSession
) -> RestorationEvent:
    event = RestorationEvent(
        outage_report_id=outage_report_id,
        h3_index=h3_index,
        utility_id=utility_id,
        status="reported",
    )
    db.add(event)
    await db.flush()
    return event


async def update_status(
    event_id: uuid.UUID,
    new_status: str,
    eta_minutes: int | None,
    crew_count: int | None,
    crew_reference: str | None,
    notes: str | None,
    db: AsyncSession,
) -> RestorationEvent | None:
    result = await db.execute(select(RestorationEvent).where(RestorationEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return None

    event.status = new_status
    if eta_minutes is not None:
        event.eta_minutes = eta_minutes
    if crew_count is not None:
        event.crew_count = crew_count
    if crew_reference is not None:
        event.crew_reference = crew_reference
    if notes is not None:
        event.notes = notes
    if new_status == "restored":
        event.resolved_at = datetime.now(timezone.utc)
        event.eta_minutes = 0

    await db.flush()
    return event


async def get_active_for_cell(h3_index: str, db: AsyncSession) -> RestorationEvent | None:
    result = await db.execute(
        select(RestorationEvent)
        .where(
            RestorationEvent.h3_index == h3_index,
            RestorationEvent.status != "restored",
            RestorationEvent.status != "cancelled",
        )
        .order_by(RestorationEvent.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_by_outage(outage_report_id: uuid.UUID, db: AsyncSession) -> RestorationEvent | None:
    result = await db.execute(
        select(RestorationEvent)
        .where(RestorationEvent.outage_report_id == outage_report_id)
        .order_by(RestorationEvent.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def eta_label(eta_minutes: int | None) -> str:
    if eta_minutes is None:
        return "Unknown"
    if eta_minutes == 0:
        return "Restored"
    if eta_minutes < 60:
        return f"~{eta_minutes} min"
    hours = eta_minutes // 60
    mins = eta_minutes % 60
    return f"~{hours}h {mins}min" if mins else f"~{hours}h"
