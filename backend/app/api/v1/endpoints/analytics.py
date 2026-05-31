"""Analytics endpoints — duration prediction, calendar, accuracy, rankings."""
import calendar
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.outage import OutageReport
from app.models.prediction import Prediction
from app.services.accuracy_service import compute_accuracy
from app.services.duration_service import predict_duration
from app.services.ranking_service import get_cell_rank, get_rankings

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── 1. Outage Duration Predictor ──────────────────────────────────────────────

@router.get("/duration/{h3_index}")
async def get_duration_prediction(
    h3_index: str,
    country_code: str = Query(default="US"),
):
    """Predict how long an outage will last at this H3 cell.

    Returns: min/median/max duration in minutes + human-readable label.
    """
    return await predict_duration(h3_index, country_code)


# ── 2. Outage Calendar View ───────────────────────────────────────────────────

@router.get("/calendar/{h3_index}")
async def get_outage_calendar(
    h3_index: str,
    year: int = Query(default=None),
    month: int = Query(default=None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """Return a calendar month view with past outages + predicted risk per day."""
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month

    _, days_in_month = calendar.monthrange(year, month)
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    month_end = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)

    # Past outages grouped by day
    outages_result = await db.execute(
        select(OutageReport).where(
            OutageReport.h3_index == h3_index,
            OutageReport.reported_at >= month_start,
            OutageReport.reported_at <= month_end,
        )
    )
    outages = outages_result.scalars().all()

    # Predictions grouped by day
    preds_result = await db.execute(
        select(Prediction).where(
            Prediction.h3_index == h3_index,
            Prediction.window_start >= month_start,
            Prediction.window_start <= month_end,
        ).order_by(Prediction.probability.desc())
    )
    predictions = preds_result.scalars().all()

    # Build day-by-day data
    days: dict[int, dict] = {}
    for day in range(1, days_in_month + 1):
        days[day] = {
            "day": day,
            "date": f"{year}-{month:02d}-{day:02d}",
            "outage_count": 0,
            "total_duration_minutes": 0,
            "max_probability": 0.0,
            "risk_level": "none",
            "is_future": datetime(year, month, day, tzinfo=timezone.utc) > now,
        }

    for o in outages:
        d = o.reported_at.day
        days[d]["outage_count"] += 1
        days[d]["total_duration_minutes"] += o.duration_minutes or 0

    for p in predictions:
        d = p.window_start.day
        if p.probability > days[d]["max_probability"]:
            days[d]["max_probability"] = round(p.probability, 4)
            days[d]["risk_level"] = p.risk_level

    return {
        "h3_index": h3_index,
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "days_in_month": days_in_month,
        "total_outages": len(outages),
        "days": list(days.values()),
    }


# ── 3. Prediction Accuracy Tracker ───────────────────────────────────────────

@router.get("/accuracy/{h3_index}")
async def get_prediction_accuracy(
    h3_index: str,
    days: int = Query(default=30, ge=7, le=90),
):
    """Return how accurately the model predicted outages for this cell.

    Compares closed prediction windows against actual verified outage reports.
    """
    return await compute_accuracy(h3_index, days)


# ── 4. Neighborhood Ranking ───────────────────────────────────────────────────

@router.get("/rankings")
async def get_neighborhood_rankings(
    country_code: str = Query(..., description="ISO country code e.g. RW, KE, US"),
    limit: int = Query(default=20, ge=5, le=100),
    period_days: int = Query(default=30, ge=7, le=90),
):
    """Return the most outage-affected neighborhoods in a country, ranked."""
    return await get_rankings(country_code, limit, period_days)


@router.get("/rankings/cell/{h3_index}")
async def get_cell_ranking(h3_index: str):
    """Return the ranking position of a specific H3 cell in its country."""
    result = await get_cell_rank(h3_index)
    if not result:
        return {"h3_index": h3_index, "message": "No ranking data yet — check back after first stats refresh"}
    return result


# ── 5. Combined summary (dashboard widget) ───────────────────────────────────

@router.get("/summary/{h3_index}")
async def get_analytics_summary(
    h3_index: str,
    country_code: str = Query(default="US"),
    db: AsyncSession = Depends(get_db),
):
    """All 4 analytics in one call — for dashboard widgets."""
    duration, accuracy, rank = await _fetch_parallel(h3_index, country_code)
    return {
        "h3_index": h3_index,
        "duration": duration,
        "accuracy": accuracy,
        "rank": rank,
    }


async def _fetch_parallel(h3_index: str, country_code: str):
    import asyncio
    return await asyncio.gather(
        predict_duration(h3_index, country_code),
        compute_accuracy(h3_index, 30),
        get_cell_rank(h3_index),
    )
