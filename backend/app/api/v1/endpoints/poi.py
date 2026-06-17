"""POI (ATM / Fuel Station) Status Layer endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.poi import PoiLocation
from app.models.user import User
from app.services.poi_service import get_pois_in_cell, record_report

router = APIRouter()


class PoiCreate(BaseModel):
    poi_type: str
    name: str
    address: str | None = None
    h3_index: str
    lat: float | None = None
    lng: float | None = None


class PoiReportCreate(BaseModel):
    is_operational: bool
    notes: str | None = None


class PoiOut(BaseModel):
    id: uuid.UUID
    poi_type: str
    name: str
    address: str | None
    h3_index: str
    is_operational: bool
    reports_up: int
    reports_down: int
    last_reported_at: str | None

    model_config = {"from_attributes": True}


@router.post("/", response_model=PoiOut, status_code=201)
async def add_poi(
    payload: PoiCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    poi = PoiLocation(
        poi_type=payload.poi_type,
        name=payload.name,
        address=payload.address,
        h3_index=payload.h3_index,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(poi)
    await db.flush()
    await db.commit()
    return poi


@router.get("/", response_model=List[PoiOut])
async def list_pois(
    h3_index: str = Query(...),
    poi_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await get_pois_in_cell(h3_index, db, poi_type)


@router.get("/{poi_id}", response_model=PoiOut)
async def get_poi(
    poi_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PoiLocation).where(PoiLocation.id == poi_id))
    poi = result.scalar_one_or_none()
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi


@router.post("/{poi_id}/report", status_code=201)
async def report_poi_status(
    poi_id: uuid.UUID,
    payload: PoiReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        rpt = await record_report(poi_id, current_user.id, payload.is_operational, payload.notes, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return {"id": str(rpt.id), "is_operational": rpt.is_operational}


@router.delete("/{poi_id}", status_code=204)
async def delete_poi(
    poi_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PoiLocation).where(PoiLocation.id == poi_id))
    poi = result.scalar_one_or_none()
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    await db.delete(poi)
    await db.flush()
    await db.commit()
