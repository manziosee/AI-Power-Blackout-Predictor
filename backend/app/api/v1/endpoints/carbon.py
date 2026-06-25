from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.outage import OutageReport
from app.models.user import User
from app.services.carbon_service import estimate_impact

router = APIRouter(prefix="/carbon", tags=["Carbon Impact"])


@router.get("/impact")
async def carbon_impact(
    hours: float = Query(default=2.0, gt=0, le=168, description="Assumed outage duration"),
    load_mw: float = Query(default=0.5, gt=0, description="Assumed MW per H3 cell"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Return estimated CO₂ impact based on distinct H3 cells with active outage reports."""
    result = await db.execute(
        select(func.count(func.distinct(OutageReport.h3_index))).where(
            OutageReport.verified.is_(True)
        )
    )
    affected_cells = result.scalar_one_or_none() or 0
    return estimate_impact(affected_cells, hours, load_mw_per_cell=load_mw)
