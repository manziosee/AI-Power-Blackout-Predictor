"""Outage incident clustering endpoints."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.incident import OutageIncident
from app.models.outage import OutageReport

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    h3_cells: list
    root_cause_estimate: str | None
    status: str
    report_count: int

    model_config = {"from_attributes": True}


@router.get("/active", response_model=list[IncidentOut])
async def list_active_incidents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OutageIncident)
        .where(OutageIncident.status == "active")
        .order_by(OutageIncident.started_at.desc())
        .limit(100)
    )
    return result.scalars().all()


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OutageIncident).where(OutageIncident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/{incident_id}/reports")
async def get_incident_reports(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    incident = (await db.execute(select(OutageIncident).where(OutageIncident.id == incident_id))).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    reports = (await db.execute(
        select(OutageReport).where(OutageReport.incident_id == incident_id).order_by(OutageReport.reported_at.asc())
    )).scalars().all()

    return {
        "incident_id": str(incident_id),
        "root_cause_estimate": incident.root_cause_estimate,
        "report_count": len(reports),
        "reports": [
            {
                "id": str(r.id),
                "h3_index": r.h3_index,
                "reported_at": r.reported_at.isoformat(),
                "verified": r.verified,
                "source": r.source,
            }
            for r in reports
        ],
    }
