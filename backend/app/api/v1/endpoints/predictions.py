"""
Predictions API — all endpoints for ML outage-probability forecasts.

Fixes applied:
  - /cell/{h3_index} now requires auth (matches /predictions/)
  - Removed duplicate public list endpoint
  - Added GET /latest/{h3_index}  → single PredictionOut
  - Added GET /compare            → side-by-side two cells
  - Added GET /accuracy/{h3_index}→ per-cell model accuracy metrics
  - Added POST /trigger           → admin on-demand prediction run
  - Added offset pagination on list endpoints
  - Fixed heatmap SQL (pure ORM join, no raw text)
  - /explain now reads real XGBoost feature importances from ML engine
  - Redis cache (5-min TTL) on heatmap endpoint
  - features_snapshot now returned in PredictionOut
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.models.neighborhood import H3Cell
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import (
    ExplainOut,
    HeatmapCell,
    PredictionAccuracyOut,
    PredictionCompareOut,
    PredictionOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])

_HEATMAP_CACHE_TTL = 300  # 5 minutes


# ── helpers ────────────────────────────────────────────────────────────────────

def _classify(p: float) -> str:
    if p >= 0.80:
        return "VERY_HIGH"
    if p >= 0.60:
        return "HIGH"
    if p >= 0.35:
        return "MEDIUM"
    return "LOW"


async def _redis() -> "redis.asyncio.Redis | None":  # noqa: F821
    """Return a Redis client or None when Redis is not available."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        return client
    except Exception:
        return None


# ── list predictions (auth required) ──────────────────────────────────────────

@router.get(
    "/",
    response_model=List[PredictionOut],
    summary="Latest predictions for an H3 cell",
    description="Returns ML outage-probability forecasts for the cell. Requires Bearer token.",
)
async def list_predictions(
    h3_index: str = Query(..., description="H3 cell index"),
    limit: int = Query(default=6, ge=1, le=48),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


# ── single latest prediction ───────────────────────────────────────────────────

@router.get(
    "/latest/{h3_index}",
    response_model=PredictionOut,
    summary="Single latest prediction for a cell",
    description="Returns only the most recent prediction record for the given H3 cell.",
)
async def get_latest_prediction(
    h3_index: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="No prediction found for this cell")
    return pred


# ── cell predictions (auth required — was incorrectly public) ─────────────────

@router.get(
    "/cell/{h3_index}",
    response_model=List[PredictionOut],
    summary="Predictions for a cell (paginated)",
)
async def get_predictions_for_cell(
    h3_index: str,
    limit: int = Query(default=6, ge=1, le=48),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


# ── explain prediction ─────────────────────────────────────────────────────────

@router.get(
    "/cell/{h3_index}/explain",
    response_model=ExplainOut,
    summary="Explain prediction risk for a cell",
    description=(
        "Returns normalised feature importance weights explaining why this cell "
        "received its current risk score. Fetches real importances from the ML engine "
        "when available; falls back to stored feature snapshot weights."
    ),
)
async def explain_prediction(
    h3_index: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="No prediction found for this cell")

    # Try fetching real feature importances from the ML engine
    real_weights: dict[str, float] | None = None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.ML_ENGINE_URL}/feature-importance/{pred.region_model}"
            )
            if resp.status_code == 200:
                real_weights = resp.json().get("importances")
    except Exception as exc:
        logger.debug("ML engine feature importance unavailable: %s", exc)

    if real_weights and isinstance(real_weights, dict) and len(real_weights) >= 3:
        total = sum(real_weights.values()) or 1.0
        normalized = {k: round(v / total, 4) for k, v in real_weights.items()}
        method = "xgboost_feature_importance"
    else:
        # Derive weights from stored feature snapshot
        snap: dict = pred.features_snapshot or {}
        _BASE_WEIGHTS: dict[str, float] = {
            "weather_risk": 0.28,
            "historical_frequency": 0.24,
            "grid_age": 0.18,
            "load_factor": 0.14,
            "time_since_last_outage": 0.10,
            "maintenance_score": 0.06,
        }
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
        method = "feature_importance_approximation"

    top_factor = max(normalized, key=lambda k: normalized[k])

    return ExplainOut(
        h3_index=h3_index,
        prediction_id=str(pred.id),
        probability=pred.probability,
        risk_level=pred.risk_level,
        feature_weights=normalized,
        top_factor=top_factor,
        model_version=pred.model_version,
        explanation_method=method,
    )


# ── heatmap (Redis-cached, public) ────────────────────────────────────────────

@router.get(
    "/heatmap",
    response_model=List[HeatmapCell],
    summary="Risk heatmap for a country",
    description=(
        "Returns the latest prediction per H3 cell for an entire country. "
        "Cached in Redis for 5 minutes to handle high frontend traffic."
    ),
)
async def get_heatmap(
    country_code: str = Query(..., description="ISO country code e.g. RW, US, FR"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"heatmap:{country_code.upper()}"

    # Try Redis cache first
    r = await _redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Latest prediction per h3_index — pure ORM, no raw text
    # Step 1: get all cells for the country
    cells_res = await db.execute(
        select(H3Cell.h3_index, H3Cell.center_lat, H3Cell.center_lng)
        .where(H3Cell.country_code == country_code.upper())
    )
    cells = cells_res.all()
    if not cells:
        return []

    cell_index_set = [c.h3_index for c in cells]
    cell_coords = {c.h3_index: (c.center_lat or 0.0, c.center_lng or 0.0) for c in cells}

    # Step 2: latest prediction per cell via window function (pure ORM)
    row_number = (
        func.row_number()
        .over(
            partition_by=Prediction.h3_index,
            order_by=Prediction.predicted_at.desc(),
        )
        .label("rn")
    )
    subq = (
        select(Prediction, row_number)
        .where(Prediction.h3_index.in_(cell_index_set))
        .subquery()
    )
    result = await db.execute(select(subq).where(subq.c.rn == 1))
    rows = result.fetchall()

    output = [
        HeatmapCell(
            h3_index=r.h3_index,
            probability=r.probability,
            risk_level=r.risk_level,
            center_lat=cell_coords.get(r.h3_index, (0.0, 0.0))[0],
            center_lng=cell_coords.get(r.h3_index, (0.0, 0.0))[1],
        )
        for r in rows
    ]

    # Populate Redis cache
    if r:
        try:
            await r.setex(cache_key, _HEATMAP_CACHE_TTL, json.dumps([o.model_dump() for o in output]))
        except Exception:
            pass

    return output


# ── compare two cells ─────────────────────────────────────────────────────────

@router.get(
    "/compare",
    response_model=PredictionCompareOut,
    summary="Compare latest predictions for two H3 cells",
)
async def compare_predictions(
    h3_a: str = Query(..., description="First H3 cell index"),
    h3_b: str = Query(..., description="Second H3 cell index"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async def _latest(h3: str) -> Prediction | None:
        res = await db.execute(
            select(Prediction)
            .where(Prediction.h3_index == h3)
            .order_by(Prediction.predicted_at.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()

    pred_a = await _latest(h3_a)
    pred_b = await _latest(h3_b)

    delta: float | None = None
    higher: str | None = None
    if pred_a and pred_b:
        delta = round(pred_a.probability - pred_b.probability, 4)
        if abs(delta) < 0.01:
            higher = "equal"
        elif delta > 0:
            higher = "a"
        else:
            higher = "b"

    return PredictionCompareOut(
        cell_a=pred_a,
        cell_b=pred_b,
        delta_probability=delta,
        higher_risk=higher,
    )


# ── per-cell accuracy ─────────────────────────────────────────────────────────

@router.get(
    "/accuracy/{h3_index}",
    response_model=PredictionAccuracyOut,
    summary="Model accuracy metrics for a cell",
    description="Returns precision, recall, F1 and accuracy grade for this cell over the past N days.",
)
async def get_prediction_accuracy(
    h3_index: str,
    days: int = Query(default=30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
):
    from app.services.accuracy_service import compute_accuracy

    metrics = await compute_accuracy(h3_index, days)
    return PredictionAccuracyOut(**metrics)


# ── admin on-demand trigger ────────────────────────────────────────────────────

@router.post(
    "/trigger",
    status_code=202,
    summary="Trigger a prediction run (admin)",
    description=(
        "Enqueues an immediate Celery prediction task. "
        "Returns 202 Accepted immediately — results appear in ~30 seconds."
    ),
    tags=["Admin"],
)
async def trigger_predictions(
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
):
    from app.tasks.predict import run_all_predictions

    background_tasks.add_task(run_all_predictions.delay)
    return {"status": "accepted", "message": "Prediction run enqueued"}
