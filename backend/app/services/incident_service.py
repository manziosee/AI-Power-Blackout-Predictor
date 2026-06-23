"""Outage incident clustering — groups spatially adjacent reports into incidents."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import h3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import OutageIncident
from app.models.outage import OutageReport

_CLUSTER_WINDOW_MINUTES = 30
_MIN_REPORTS = 5
_CELL_RING = 2  # h3 grid_disk radius


def _estimate_root_cause(cells: list[str], report_count: int) -> str:
    if report_count >= 15:
        return "substation_fault"
    if report_count >= 8:
        return "feeder_fault"
    return "equipment_failure"


async def cluster_recent_outages(db: AsyncSession) -> list[OutageIncident]:
    """Find unassigned verified outage reports and cluster into incidents."""
    since = datetime.now(timezone.utc) - timedelta(minutes=_CLUSTER_WINDOW_MINUTES)

    result = await db.execute(
        select(OutageReport).where(
            OutageReport.verified.is_(True),
            OutageReport.reported_at >= since,
            OutageReport.incident_id.is_(None),
        )
    )
    reports = list(result.scalars().all())

    if len(reports) < _MIN_REPORTS:
        return []

    assigned: set[uuid.UUID] = set()
    incidents_created: list[OutageIncident] = []

    for anchor in reports:
        if anchor.id in assigned:
            continue
        nearby_cells = set(h3.grid_disk(anchor.h3_index, _CELL_RING))
        cluster = [r for r in reports if r.id not in assigned and r.h3_index in nearby_cells]
        if len(cluster) < _MIN_REPORTS:
            continue

        cells_in_cluster = list({r.h3_index for r in cluster})
        incident = OutageIncident(
            started_at=min(r.reported_at for r in cluster),
            h3_cells=cells_in_cluster,
            root_cause_estimate=_estimate_root_cause(cells_in_cluster, len(cluster)),
            status="active",
            report_count=len(cluster),
        )
        db.add(incident)
        await db.flush()

        for r in cluster:
            r.incident_id = incident.id
            assigned.add(r.id)

        incidents_created.append(incident)

    return incidents_created


async def resolve_incident(incident_id: uuid.UUID, db: AsyncSession) -> OutageIncident | None:
    result = await db.execute(select(OutageIncident).where(OutageIncident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return None
    incident.status = "resolved"
    incident.ended_at = datetime.now(timezone.utc)
    await db.flush()
    return incident
