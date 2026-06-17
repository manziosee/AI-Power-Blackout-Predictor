"""Service for neighborhood resilience scoring."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import PredictionAccuracy
from app.models.outage import OutageReport
from app.models.resilience import ResilienceScore


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"


async def compute_score(h3_index: str, db: AsyncSession) -> float:
    """Compute resilience score 0-100 for a cell and upsert it."""
    now = datetime.now(timezone.utc)
    since_30d = now - timedelta(days=30)

    # Frequency component (weight 35%): fewer outages = higher score
    count_result = await db.execute(
        select(func.count()).where(
            OutageReport.h3_index == h3_index,
            OutageReport.reported_at >= since_30d,
        )
    )
    outages_30d = count_result.scalar() or 0
    freq_score = max(0.0, 100.0 - outages_30d * 10)

    # Duration component (weight 30%): shorter avg = higher score
    dur_result = await db.execute(
        select(func.avg(OutageReport.duration_minutes)).where(
            OutageReport.h3_index == h3_index,
            OutageReport.duration_minutes.is_not(None),
        )
    )
    avg_dur = dur_result.scalar()
    if avg_dur is None:
        dur_score = 70.0
    else:
        dur_score = max(0.0, 100.0 - avg_dur / 6.0)  # 600 min = 0, 0 min = 100

    # Accuracy component (weight 20%): latest f1_score
    acc_result = await db.execute(
        select(PredictionAccuracy.f1_score).where(
            PredictionAccuracy.h3_index == h3_index,
            PredictionAccuracy.f1_score.is_not(None),
        ).order_by(PredictionAccuracy.computed_at.desc()).limit(1)
    )
    f1 = acc_result.scalar()
    acc_score = (f1 * 100) if f1 is not None else 50.0

    # Participation component (weight 15%): proxy via report count
    part_score = min(100.0, outages_30d * 5)

    total = (
        freq_score * 0.35
        + dur_score * 0.30
        + acc_score * 0.20
        + part_score * 0.15
    )
    total = round(total, 2)
    grade = _grade(total)

    # Upsert
    existing = await db.execute(
        select(ResilienceScore).where(ResilienceScore.h3_index == h3_index)
    )
    rs = existing.scalar_one_or_none()
    if rs is None:
        rs = ResilienceScore(h3_index=h3_index)
        db.add(rs)

    rs.score = total
    rs.outage_frequency_score = freq_score
    rs.avg_duration_score = dur_score
    rs.prediction_accuracy_score = acc_score
    rs.report_participation_score = part_score
    rs.outages_30d = outages_30d
    rs.avg_duration_minutes = avg_dur
    rs.grade = grade
    rs.computed_at = now
    await db.flush()
    return total


async def get_or_compute(h3_index: str, db: AsyncSession) -> ResilienceScore:
    existing = await db.execute(
        select(ResilienceScore).where(ResilienceScore.h3_index == h3_index)
    )
    rs = existing.scalar_one_or_none()
    if rs is None:
        await compute_score(h3_index, db)
        existing2 = await db.execute(
            select(ResilienceScore).where(ResilienceScore.h3_index == h3_index)
        )
        rs = existing2.scalar_one_or_none()
    return rs
