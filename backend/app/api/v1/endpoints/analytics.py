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


# ── 6. Utility Response Time Benchmarking (Feature 9) ────────────────────────

@router.get("/utility-response-times")
async def utility_response_times(
    days: int = Query(default=30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
):
    """Per-utility avg/median response time from verified outage to power restored."""
    from app.models.enterprise import UtilityCompany
    from app.models.restoration import RestorationEvent

    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (await db.execute(
        select(
            RestorationEvent.utility_id,
            RestorationEvent.outage_report_id,
            RestorationEvent.resolved_at,
            OutageReport.confirmed_at,
            OutageReport.reported_at,
        )
        .join(OutageReport, OutageReport.id == RestorationEvent.outage_report_id)
        .where(
            RestorationEvent.status == "restored",
            RestorationEvent.resolved_at.isnot(None),
            OutageReport.verified.is_(True),
            OutageReport.reported_at >= since,
        )
    )).fetchall()

    from collections import defaultdict
    buckets: dict = defaultdict(list)
    for row in rows:
        if not row.resolved_at:
            continue
        start = row.confirmed_at or row.reported_at
        if not start:
            continue
        minutes = (row.resolved_at - start).total_seconds() / 60.0
        if minutes >= 0:
            buckets[str(row.utility_id) if row.utility_id else "unknown"].append(minutes)

    utilities = {str(u.id): u.name for u in (await db.execute(select(UtilityCompany))).scalars().all()}

    leaderboard = []
    for uid, times in buckets.items():
        times.sort()
        n = len(times)
        avg = sum(times) / n
        median = times[n // 2] if n else 0
        leaderboard.append({
            "utility_id": uid,
            "utility_name": utilities.get(uid, "Unknown"),
            "avg_response_minutes": round(avg, 1),
            "median_response_minutes": round(median, 1),
            "resolved_incidents": n,
        })

    leaderboard.sort(key=lambda x: x["avg_response_minutes"])
    return {
        "period_days": days,
        "leaderboard": leaderboard,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 7. Weather Correlation Dashboard (Feature 10) ────────────────────────────

@router.get("/weather-correlation/{h3_index}")
async def weather_correlation(
    h3_index: str,
    days: int = Query(default=90, ge=14, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Show which weather conditions most correlate with outages at this cell."""
    from app.models.weather import WeatherSnapshot

    since = datetime.now(timezone.utc) - timedelta(days=days)

    outages = (await db.execute(
        select(OutageReport).where(
            OutageReport.h3_index == h3_index,
            OutageReport.verified.is_(True),
            OutageReport.reported_at >= since,
        )
    )).scalars().all()

    snaps = (await db.execute(
        select(WeatherSnapshot).where(
            WeatherSnapshot.h3_index == h3_index,
            WeatherSnapshot.recorded_at >= since,
        ).order_by(WeatherSnapshot.recorded_at.asc())
    )).scalars().all()

    if not snaps:
        return {"h3_index": h3_index, "message": "No weather data available", "correlations": []}

    # Mark each snapshot as "during outage" if within 2h of any outage
    outage_times = [(o.reported_at, o.resolved_at or (o.reported_at + timedelta(hours=4))) for o in outages]

    during: list[WeatherSnapshot] = []
    baseline: list[WeatherSnapshot] = []
    for s in snaps:
        in_outage = any(start <= s.recorded_at <= end for start, end in outage_times)
        (during if in_outage else baseline).append(s)

    def _avg(lst, attr):
        vals = [getattr(x, attr) for x in lst if getattr(x, attr) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    metrics = [
        ("wind_speed_ms", "Wind Speed (m/s)"),
        ("rainfall_mm", "Rainfall (mm)"),
        ("temperature_c", "Temperature (°C)"),
        ("humidity_pct", "Humidity (%)"),
    ]

    correlations = []
    for attr, label in metrics:
        avg_during = _avg(during, attr)
        avg_baseline = _avg(baseline, attr)
        if avg_during is None or avg_baseline is None or avg_baseline == 0:
            continue
        pct_diff = round((avg_during - avg_baseline) / abs(avg_baseline) * 100, 1)
        correlations.append({
            "metric": attr,
            "label": label,
            "avg_during_outage": avg_during,
            "avg_baseline": avg_baseline,
            "pct_higher_during_outage": pct_diff,
        })

    correlations.sort(key=lambda x: abs(x["pct_higher_during_outage"]), reverse=True)

    return {
        "h3_index": h3_index,
        "period_days": days,
        "outage_count": len(outages),
        "outage_snapshots": len(during),
        "baseline_snapshots": len(baseline),
        "correlations": correlations,
    }
