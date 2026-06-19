from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.maintenance_service import get_top_at_risk

router = APIRouter()


@router.get("/transformers/at-risk")
async def top_at_risk_transformers(
    limit: int = Query(20, ge=1, le=100),
    utility_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return top N transformers ranked by maintenance risk score."""
    import uuid
    uid = None
    if utility_id:
        try:
            uid = uuid.UUID(utility_id)
        except ValueError:
            pass
    return await get_top_at_risk(uid, limit, db)


@router.post("/transformers/score")
async def trigger_maintenance_score(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger maintenance scoring for all transformers."""
    from app.tasks.maintenance_score import score_transformers_task
    score_transformers_task.delay()
    return {"queued": True, "message": "Maintenance scoring task queued"}
