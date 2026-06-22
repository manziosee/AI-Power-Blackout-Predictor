"""Build a human-readable milestone timeline for an outage report."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outage import OutageReport
from app.models.restoration import RestorationEvent


class TimelineEvent:
    def __init__(self, step: str, label: str, occurred_at: datetime | None, pending: bool = False):
        self.step = step
        self.label = label
        self.occurred_at = occurred_at
        self.pending = pending


async def build_timeline(report_id: uuid.UUID, db: AsyncSession) -> list[TimelineEvent] | None:
    r = (await db.execute(select(OutageReport).where(OutageReport.id == report_id))).scalar_one_or_none()
    if not r:
        return None

    evt = (
        await db.execute(
            select(RestorationEvent)
            .where(RestorationEvent.outage_report_id == report_id)
            .order_by(RestorationEvent.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    _STATUS_TS: dict[str, datetime | None] = {}
    if evt:
        _STATUS_TS["utility_notified"] = evt.created_at
        _STATUS_TS["restored"] = evt.resolved_at

    steps = [
        ("reported",         "Outage reported",       r.reported_at),
        ("confirmed",        "Community confirmed",   r.confirmed_at),
        ("utility_notified", "Utility notified",      _STATUS_TS.get("utility_notified")),
        ("crew_assigned",    "Crew assigned",         None),
        ("crew_on_site",     "Crew on site",          None),
        ("restored",         "Power restored",        _STATUS_TS.get("restored") or r.resolved_at),
    ]

    # Mark steps that fall at/before the current restoration status as reached
    _reached = {
        "reported":         True,
        "confirmed":        r.confirmed_at is not None,
        "utility_notified": evt is not None,
        "crew_assigned":    evt is not None and evt.status in ("crew_assigned", "crew_en_route", "crew_on_site", "restored"),
        "crew_on_site":     evt is not None and evt.status in ("crew_on_site", "restored"),
        "restored":         (evt is not None and evt.status == "restored") or r.resolved_at is not None,
    }

    result: list[TimelineEvent] = []
    for step, label, ts in steps:
        reached = _reached.get(step, False)
        result.append(TimelineEvent(
            step=step,
            label=label,
            occurred_at=ts if reached else None,
            pending=not reached,
        ))

    return result
