"""Grid Topology Model endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.grid_topology import GridTransformer, TransformerCellCoverage
from app.models.user import User
from app.services.grid_topology_service import (
    get_affected_cells,
    get_transformers_for_cell,
)

router = APIRouter()


class TransformerCreate(BaseModel):
    name: str
    transformer_type: str = "distribution"
    lat: float | None = None
    lng: float | None = None
    h3_index: str | None = None
    capacity_kva: float | None = None
    age_years: int | None = None
    utility_id: uuid.UUID | None = None


class TransformerStatusUpdate(BaseModel):
    status: str


class CoverageAdd(BaseModel):
    h3_index: str
    is_primary: bool = True


class TransformerOut(BaseModel):
    id: uuid.UUID
    name: str
    transformer_type: str
    h3_index: str | None
    status: str
    capacity_kva: float | None
    age_years: int | None

    model_config = {"from_attributes": True}


@router.post("/transformers", response_model=TransformerOut, status_code=201)
async def add_transformer(
    payload: TransformerCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    t = GridTransformer(**payload.model_dump())
    db.add(t)
    await db.flush()
    await db.commit()
    return t


@router.get("/transformers", response_model=List[TransformerOut])
async def list_transformers(
    h3_index: str | None = Query(default=None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(GridTransformer)
    if h3_index:
        query = query.where(GridTransformer.h3_index == h3_index)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/transformers/{transformer_id}", response_model=TransformerOut)
async def get_transformer(
    transformer_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GridTransformer).where(GridTransformer.id == transformer_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transformer not found")
    return t


@router.put("/transformers/{transformer_id}/status", response_model=TransformerOut)
async def update_transformer_status(
    transformer_id: uuid.UUID,
    payload: TransformerStatusUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GridTransformer).where(GridTransformer.id == transformer_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transformer not found")
    t.status = payload.status
    await db.flush()
    await db.commit()
    return t


@router.post("/transformers/{transformer_id}/coverage", status_code=201)
async def add_coverage(
    transformer_id: uuid.UUID,
    payload: CoverageAdd,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cov = TransformerCellCoverage(
        transformer_id=transformer_id,
        h3_index=payload.h3_index,
        is_primary=payload.is_primary,
    )
    db.add(cov)
    await db.flush()
    await db.commit()
    return {"transformer_id": str(transformer_id), "h3_index": payload.h3_index}


@router.get("/affected-cells/{transformer_id}")
async def affected_cells(
    transformer_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cells = await get_affected_cells(transformer_id, db)
    return {"transformer_id": str(transformer_id), "cells": cells}


@router.get("/cell-transformers/{h3_index}")
async def cell_transformers(
    h3_index: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    transformers = await get_transformers_for_cell(h3_index, db)
    return [
        {"id": str(t.id), "name": t.name, "status": t.status}
        for t in transformers
    ]
