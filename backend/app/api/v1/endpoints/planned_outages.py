"""Planned Outage Calendar endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.planned_outage import PlannedOutage
from app.models.user import User
from app.schemas.planned_outage import PlannedOutageCreate, PlannedOutageOut, PlannedOutageStatusUpdate
from app.services.planned_outage_service import get_upcoming

router = APIRouter()


@router.get("/", response_model=List[PlannedOutageOut])
async def list_planned_outages(
    h3_index: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await get_upcoming(h3_index, db)


@router.post("/", response_model=PlannedOutageOut, status_code=201)
async def create_planned_outage(
    payload: PlannedOutageCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    outage = PlannedOutage(
        h3_index=payload.h3_index,
        title=payload.title,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        description=payload.description,
        source=payload.source,
    )
    db.add(outage)
    await db.flush()
    return outage


@router.put("/{outage_id}/status", response_model=PlannedOutageOut)
async def update_status(
    outage_id: uuid.UUID,
    payload: PlannedOutageStatusUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PlannedOutage).where(PlannedOutage.id == outage_id))
    outage = result.scalar_one_or_none()
    if not outage:
        raise HTTPException(status_code=404, detail="Planned outage not found")
    outage.status = payload.status
    await db.flush()
    return outage


@router.delete("/{outage_id}", status_code=204)
async def delete_planned_outage(
    outage_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PlannedOutage).where(PlannedOutage.id == outage_id))
    outage = result.scalar_one_or_none()
    if not outage:
        raise HTTPException(status_code=404, detail="Planned outage not found")
    await db.delete(outage)
    await db.flush()
