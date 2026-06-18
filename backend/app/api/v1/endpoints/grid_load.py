from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.grid_load_service import fetch_eia_load, fetch_entso_e_load, get_history, get_latest_load

router = APIRouter()


@router.get("/{region}")
async def get_grid_load(
    region: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshot = await get_latest_load(region, db)
    if not snapshot:
        return {"region": region, "data": None}
    return {
        "region": snapshot.region,
        "source": snapshot.source,
        "load_mw": snapshot.load_mw,
        "capacity_mw": snapshot.capacity_mw,
        "load_pct": snapshot.load_pct,
        "renewable_pct": snapshot.renewable_pct,
        "recorded_at": snapshot.recorded_at.isoformat(),
    }


@router.get("/{region}/history")
async def get_grid_load_history(
    region: str,
    limit: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshots = await get_history(region, db, limit)
    return [
        {
            "region": s.region,
            "source": s.source,
            "load_mw": s.load_mw,
            "load_pct": s.load_pct,
            "recorded_at": s.recorded_at.isoformat(),
        }
        for s in snapshots
    ]


@router.post("/{region}/fetch")
async def trigger_grid_load_fetch(
    region: str,
    source: str = Query("eia", pattern="^(eia|entso-e)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if source == "eia":
        snapshot = await fetch_eia_load(region, db)
    else:
        snapshot = await fetch_entso_e_load(region, db)
    await db.commit()
    if not snapshot:
        return {"fetched": False, "reason": "No API key configured or fetch failed"}
    return {"fetched": True, "region": snapshot.region, "source": snapshot.source, "load_mw": snapshot.load_mw}
