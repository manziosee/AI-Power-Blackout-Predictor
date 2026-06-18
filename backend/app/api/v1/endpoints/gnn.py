from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.gnn_model import GnnPrediction
from app.models.user import User

router = APIRouter()


@router.get("/predictions/{h3_index}")
async def gnn_predictions_for_cell(
    h3_index: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GnnPrediction)
        .where(GnnPrediction.h3_index == h3_index)
        .order_by(GnnPrediction.predicted_at.desc())
        .limit(limit)
    )
    preds = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "h3_index": p.h3_index,
            "probability": p.probability,
            "cascade_risk": p.cascade_risk,
            "affected_cells": p.affected_cells,
            "model_version": p.model_version,
            "confidence": p.confidence,
            "predicted_at": p.predicted_at.isoformat(),
        }
        for p in preds
    ]


@router.get("/cascade-risk/{transformer_id}")
async def cascade_risk_for_transformer(
    transformer_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import uuid as uuid_lib
    try:
        t_uuid = uuid_lib.UUID(transformer_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid transformer UUID")
    result = await db.execute(
        select(GnnPrediction)
        .where(GnnPrediction.transformer_id == t_uuid)
        .order_by(GnnPrediction.cascade_risk.desc())
        .limit(limit)
    )
    preds = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "h3_index": p.h3_index,
            "probability": p.probability,
            "cascade_risk": p.cascade_risk,
            "affected_cells": p.affected_cells,
            "confidence": p.confidence,
            "predicted_at": p.predicted_at.isoformat(),
        }
        for p in preds
    ]
