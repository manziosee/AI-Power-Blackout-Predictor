from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import HeatmapCell, PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/", response_model=List[PredictionOut])
async def list_predictions(
    h3_index: str = Query(..., description="H3 cell index"),
    limit: int = Query(default=6, le=24),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List predictions for an H3 cell. Requires authentication."""
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/cell/{h3_index}", response_model=List[PredictionOut])
async def get_predictions_for_cell(
    h3_index: str,
    limit: int = Query(default=6, le=24),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/heatmap", response_model=List[HeatmapCell])
async def get_heatmap(
    country_code: str = Query(..., description="ISO country code e.g. RW, US, FR"),
    db: AsyncSession = Depends(get_db),
):
    """Return latest prediction per H3 cell for a country (used to render the heatmap)."""
    from sqlalchemy import func, text

    # Latest prediction per h3_index via window function
    subq = (
        select(
            Prediction,
            func.row_number()
            .over(partition_by=Prediction.h3_index, order_by=Prediction.predicted_at.desc())
            .label("rn"),
        )
        .join(
            text("h3_cells ON h3_cells.h3_index = predictions.h3_index AND h3_cells.country_code = :cc"),
        )
        .params(cc=country_code)
        .subquery()
    )

    result = await db.execute(select(subq).where(subq.c.rn == 1))
    rows = result.fetchall()

    return [
        HeatmapCell(
            h3_index=r.h3_index,
            probability=r.probability,
            risk_level=r.risk_level,
            center_lat=r.center_lat or 0.0,
            center_lng=r.center_lng or 0.0,
        )
        for r in rows
    ]
