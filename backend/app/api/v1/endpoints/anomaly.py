from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.grid_load import GridLoadSnapshot
from app.models.user import User
from app.services.anomaly_service import detect_anomalies, summarize

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection"])


@router.get("/{region}")
async def get_anomalies(
    region: str,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    rows = await db.execute(
        select(GridLoadSnapshot)
        .where(GridLoadSnapshot.region == region)
        .order_by(GridLoadSnapshot.recorded_at.desc())
        .limit(limit)
    )
    snapshots = rows.scalars().all()
    data = [
        {
            "id": str(s.id),
            "region": s.region,
            "recorded_at": s.recorded_at.isoformat() if s.recorded_at else None,
            "load_mw": float(s.load_mw) if s.load_mw is not None else 0.0,
            "capacity_mw": float(s.capacity_mw) if s.capacity_mw is not None else 0.0,
            "load_pct": float(s.load_pct) if s.load_pct is not None else 0.0,
            "renewable_pct": float(s.renewable_pct) if s.renewable_pct is not None else 0.0,
        }
        for s in snapshots
    ]
    scored = detect_anomalies(data)
    return summarize(scored)
