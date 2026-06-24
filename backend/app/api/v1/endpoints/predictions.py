from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import HeatmapCell, PredictionOut

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/", response_model=List[PredictionOut],
            summary="Latest predictions for an H3 cell",
            description="Returns the most recent ML outage-probability forecasts for the given cell. Requires Bearer token authentication.")
async def list_predictions(
    h3_index: str = Query(..., description="H3 cell index"),
    limit: int = Query(default=6, le=24),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/cell/{h3_index}", response_model=List[PredictionOut],
            summary="Latest predictions for a cell (public)")
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


@router.get("/cell/{h3_index}/explain",
            summary="Explain prediction risk for a cell",
            description="Returns normalised feature importance weights explaining why this cell received its current risk score. Uses the most recent prediction's feature snapshot when available.")
async def explain_prediction(h3_index: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="No prediction found for this cell")

    # Canonical global feature importances (approximated from XGBoost training)
    _BASE_WEIGHTS: dict[str, float] = {
        "weather_risk": 0.28,
        "historical_frequency": 0.24,
        "grid_age": 0.18,
        "load_factor": 0.14,
        "time_since_last_outage": 0.10,
        "maintenance_score": 0.06,
    }

    snap: dict = {}
    if isinstance(pred.features_snapshot, dict):
        snap = pred.features_snapshot

    contributions: dict[str, float] = {}
    for feat, base in _BASE_WEIGHTS.items():
        val = snap.get(feat)
        if isinstance(val, (int, float)):
            scaled = min(abs(float(val)) / 10.0, 1.0)
            contributions[feat] = base * (0.5 + 0.5 * scaled)
        else:
            contributions[feat] = base * pred.probability

    total = sum(contributions.values()) or 1.0
    normalized = {k: round(v / total, 4) for k, v in contributions.items()}
    top_factor = max(normalized, key=lambda k: normalized[k])

    return {
        "h3_index": h3_index,
        "prediction_id": str(pred.id),
        "probability": pred.probability,
        "risk_level": pred.risk_level,
        "feature_weights": normalized,
        "top_factor": top_factor,
        "model_version": pred.model_version,
        "explanation_method": "feature_importance_approximation",
    }


@router.get("/heatmap", response_model=List[HeatmapCell],
            summary="Risk heatmap for a country",
            description="Returns the latest prediction per H3 cell for an entire country. Used to render the risk heatmap overlay on the map.")
async def get_heatmap(
    country_code: str = Query(..., description="ISO country code e.g. RW, US, FR"),
    db: AsyncSession = Depends(get_db),
):
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
