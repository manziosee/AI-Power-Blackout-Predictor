import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.restoration_service import eta_label, get_active_for_cell, get_by_outage, update_status

router = APIRouter()


class RestorationStatusUpdate(BaseModel):
    status: str
    eta_minutes: int | None = None
    crew_count: int | None = None
    crew_reference: str | None = None
    notes: str | None = None


@router.get("/cell/{h3_index}")
async def get_cell_restoration(
    h3_index: str,
    db: AsyncSession = Depends(get_db),
):
    event = await get_active_for_cell(h3_index, db)
    if not event:
        return {"h3_index": h3_index, "active_restoration": None}
    return {
        "id": str(event.id),
        "h3_index": event.h3_index,
        "status": event.status,
        "eta_minutes": event.eta_minutes,
        "eta_label": eta_label(event.eta_minutes),
        "crew_count": event.crew_count,
        "notes": event.notes,
        "updated_at": event.updated_at.isoformat(),
    }


@router.get("/outage/{outage_report_id}")
async def get_outage_restoration(
    outage_report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await get_by_outage(outage_report_id, db)
    if not event:
        raise HTTPException(status_code=404, detail="No restoration event for this outage")
    return {
        "id": str(event.id),
        "status": event.status,
        "eta_minutes": event.eta_minutes,
        "eta_label": eta_label(event.eta_minutes),
        "crew_count": event.crew_count,
        "crew_reference": event.crew_reference,
        "notes": event.notes,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "updated_at": event.updated_at.isoformat(),
    }


@router.patch("/{event_id}/status")
async def patch_restoration_status(
    event_id: uuid.UUID,
    body: RestorationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valid = {"acknowledged", "crew_assigned", "crew_en_route", "crew_on_site", "restored", "cancelled"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {', '.join(sorted(valid))}")

    event = await update_status(
        event_id, body.status, body.eta_minutes, body.crew_count,
        body.crew_reference, body.notes, db
    )
    if not event:
        raise HTTPException(status_code=404, detail="Restoration event not found")

    await db.commit()

    # Broadcast ETA update via push + SMS
    from app.tasks.restoration_broadcast import broadcast_restoration_update
    broadcast_restoration_update.delay(str(event.id), event.h3_index, event.status, event.eta_minutes)

    return {
        "id": str(event.id),
        "status": event.status,
        "eta_label": eta_label(event.eta_minutes),
        "updated_at": event.updated_at.isoformat(),
    }
