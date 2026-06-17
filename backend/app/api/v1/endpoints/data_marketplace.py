"""Data Marketplace endpoints."""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.data_marketplace import DataExportRequest
from app.models.user import User
from app.services.data_marketplace_service import get_public_preview, validate_request

router = APIRouter()


class ExportRequestCreate(BaseModel):
    requester_email: str
    requester_org: str | None = None
    data_type: str
    h3_cells: list | None = None
    date_from: datetime
    date_to: datetime
    format: str = "json"


class ExportRequestStatusUpdate(BaseModel):
    status: str


class ExportRequestOut(BaseModel):
    id: uuid.UUID
    requester_email: str
    requester_org: str | None
    data_type: str
    status: str
    price_usd: float
    paid: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/request", response_model=ExportRequestOut, status_code=201)
async def submit_request(
    payload: ExportRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    error = validate_request(payload.data_type, payload.date_from, payload.date_to)
    if error:
        raise HTTPException(status_code=422, detail=error)

    req = DataExportRequest(
        requester_email=payload.requester_email,
        requester_org=payload.requester_org,
        data_type=payload.data_type,
        h3_cells=payload.h3_cells,
        date_from=payload.date_from,
        date_to=payload.date_to,
        format=payload.format,
    )
    db.add(req)
    await db.flush()
    await db.commit()
    return req


@router.get("/requests", response_model=List[ExportRequestOut])
async def list_requests(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataExportRequest).order_by(DataExportRequest.created_at.desc())
    )
    return result.scalars().all()


@router.get("/requests/{request_id}", response_model=ExportRequestOut)
async def get_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataExportRequest).where(DataExportRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.put("/requests/{request_id}/status", response_model=ExportRequestOut)
async def update_request_status(
    request_id: uuid.UUID,
    payload: ExportRequestStatusUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataExportRequest).where(DataExportRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = payload.status
    await db.flush()
    await db.commit()
    return req


@router.get("/preview/{h3_index}")
async def preview(
    h3_index: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_public_preview(h3_index, db)
