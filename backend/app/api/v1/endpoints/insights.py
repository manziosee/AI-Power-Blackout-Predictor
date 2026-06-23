"""AI Insights endpoint — Groq-powered explanations for predictions and history."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.outage import OutageReport
from app.models.prediction import Prediction
from app.models.user import User
from app.models.weather import WeatherSnapshot
from app.services.groq_service import explain_prediction, summarize_outage_history

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/prediction/{h3_index}")
async def ai_prediction_explanation(
    h3_index: str,
    language: str = Query(default="en", pattern="^(en|fr|rw|sw|ar|es|pt)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the latest prediction for an H3 cell plus an AI-generated explanation."""
    now = datetime.now(timezone.utc)

    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index, Prediction.window_end > now)
        .order_by(Prediction.probability.desc())
        .limit(1)
    )
    pred = pred_result.scalar_one_or_none()

    if not pred:
        return {
            "h3_index": h3_index,
            "prediction": None,
            "ai_explanation": "",
            "message": "No active predictions for this area.",
        }

    weather_result = await db.execute(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.h3_index == h3_index)
        .order_by(WeatherSnapshot.recorded_at.desc())
        .limit(1)
    )
    weather = weather_result.scalar_one_or_none()

    outages_7d = (await db.execute(
        select(OutageReport).where(
            OutageReport.h3_index == h3_index,
            OutageReport.reported_at >= now - timedelta(days=7),
        )
    )).scalars().all()

    explanation = await explain_prediction(
        risk_level=pred.risk_level,
        probability=pred.probability,
        rainfall_mm=float(weather.rainfall_mm) if weather else 0.0,
        wind_speed_ms=float(weather.wind_speed_ms) if weather else 0.0,
        temperature_c=float(weather.temperature_c) if weather else 20.0,
        outages_7d=len(outages_7d),
        window_start=pred.window_start.strftime("%Y-%m-%d %H:%M UTC"),
        language=language,
    )

    return {
        "h3_index": h3_index,
        "prediction": {
            "probability": pred.probability,
            "risk_level": pred.risk_level,
            "window_start": pred.window_start.isoformat(),
            "window_end": pred.window_end.isoformat(),
            "model_version": pred.model_version,
        },
        "ai_explanation": explanation,
        "weather": {
            "rainfall_mm": float(weather.rainfall_mm) if weather else None,
            "wind_speed_ms": float(weather.wind_speed_ms) if weather else None,
            "temperature_c": float(weather.temperature_c) if weather else None,
        } if weather else None,
    }


@router.get("/history/{h3_index}")
async def ai_history_summary(
    h3_index: str,
    language: str = Query(default="en", pattern="^(en|fr|rw|sw|ar|es|pt)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return an AI-generated summary of a neighborhood's outage history."""
    from sqlalchemy import func

    now = datetime.now(timezone.utc)

    count_7d = (await db.execute(
        select(func.count()).where(
            OutageReport.h3_index == h3_index,
            OutageReport.reported_at >= now - timedelta(days=7),
        )
    )).scalar() or 0

    count_30d = (await db.execute(
        select(func.count()).where(
            OutageReport.h3_index == h3_index,
            OutageReport.reported_at >= now - timedelta(days=30),
        )
    )).scalar() or 0

    avg_dur = (await db.execute(
        select(func.avg(OutageReport.duration_minutes)).where(
            OutageReport.h3_index == h3_index,
            OutageReport.duration_minutes.isnot(None),
        )
    )).scalar()

    summary = await summarize_outage_history(
        h3_index=h3_index,
        outage_count_7d=count_7d,
        outage_count_30d=count_30d,
        avg_duration_minutes=float(avg_dur) if avg_dur else None,
        language=language,
    )

    return {
        "h3_index": h3_index,
        "outages_7d": count_7d,
        "outages_30d": count_30d,
        "avg_duration_minutes": round(float(avg_dur), 1) if avg_dur else None,
        "ai_summary": summary,
    }
