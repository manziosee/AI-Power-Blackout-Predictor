from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.neighborhood import H3Cell
from app.schemas.prediction import HeatmapCell

router = APIRouter(prefix="/neighborhoods", tags=["neighborhoods"])


@router.get("/cell/{h3_index}")
async def get_cell_info(h3_index: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(H3Cell).where(H3Cell.h3_index == h3_index))
    cell = result.scalar_one_or_none()
    if not cell:
        return {"h3_index": h3_index, "detail": "Cell not yet tracked"}
    return cell


@router.get("/lookup")
async def lookup_cell(
    lat: float = Query(...),
    lng: float = Query(...),
    resolution: int = Query(default=8, ge=5, le=12),
):
    """Convert lat/lng to H3 cell index."""
    import h3
    h3_index = h3.latlng_to_cell(lat, lng, resolution)
    center = h3.cell_to_latlng(h3_index)
    return {"h3_index": h3_index, "center_lat": center[0], "center_lng": center[1], "resolution": resolution}


@router.get("/country/{country_code}", response_model=List[HeatmapCell])
async def cells_by_country(country_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(H3Cell).where(H3Cell.country_code == country_code.upper()).limit(5000)
    )
    cells = result.scalars().all()
    return [
        HeatmapCell(
            h3_index=c.h3_index,
            probability=0.0,
            risk_level="low",
            center_lat=c.center_lat or 0.0,
            center_lng=c.center_lng or 0.0,
        )
        for c in cells
    ]
