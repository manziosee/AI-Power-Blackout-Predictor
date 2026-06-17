"""Seasonal Decomposition Dashboard endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.seasonal import SeasonalStats
from app.models.user import User
from app.services.seasonal_service import get_worst_months, get_year_over_year

router = APIRouter()


@router.get("/{h3_index}")
async def seasonal_stats(
    h3_index: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SeasonalStats)
        .where(SeasonalStats.h3_index == h3_index)
        .order_by(SeasonalStats.year.desc(), SeasonalStats.month.desc())
        .limit(24)
    )
    rows = result.scalars().all()
    return [
        {
            "year": r.year,
            "month": r.month,
            "outage_count": r.outage_count,
            "avg_duration_minutes": r.avg_duration_minutes,
            "total_outage_hours": r.total_outage_hours,
        }
        for r in rows
    ]


@router.get("/{h3_index}/worst-months")
async def worst_months(
    h3_index: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_worst_months(h3_index, db)


@router.get("/{h3_index}/trend")
async def year_over_year(
    h3_index: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_year_over_year(h3_index, db)
