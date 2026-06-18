"""Public REST API service — anonymized data for governments and NGOs."""
import hashlib
import secrets
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_api import PublicApiKey


def generate_api_key() -> str:
    return "pub_" + secrets.token_urlsafe(24)


async def register_key(organization: str, email: str, tier: str, db: AsyncSession) -> tuple[str, PublicApiKey]:
    raw_key = generate_api_key()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = PublicApiKey(
        organization=organization,
        contact_email=email,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        tier=tier,
        rate_limit_per_minute=60 if tier == "ngo" else 120,
        rate_limit_per_day=1000 if tier == "ngo" else 5000,
    )
    db.add(api_key)
    await db.flush()
    return raw_key, api_key


async def get_public_outages(
    country_code: str | None, h3_index: str | None,
    date_from: datetime | None, date_to: datetime | None,
    limit: int, db: AsyncSession,
) -> list[dict]:
    from app.models.outage import OutageReport
    query = select(
        OutageReport.h3_index,
        OutageReport.reported_at,
        OutageReport.duration_minutes,
        OutageReport.verified,
    ).where(OutageReport.verified.is_(True))
    if h3_index:
        query = query.where(OutageReport.h3_index == h3_index)
    if date_from:
        query = query.where(OutageReport.reported_at >= date_from)
    if date_to:
        query = query.where(OutageReport.reported_at <= date_to)
    query = query.order_by(OutageReport.reported_at.desc()).limit(limit)
    result = await db.execute(query)
    return [
        {
            "h3_index": r.h3_index,
            "reported_at": r.reported_at.isoformat(),
            "duration_minutes": r.duration_minutes,
        }
        for r in result.all()
    ]


async def get_public_predictions(h3_index: str, limit: int, db: AsyncSession) -> list[dict]:
    from app.models.prediction import Prediction
    result = await db.execute(
        select(Prediction.h3_index, Prediction.predicted_at, Prediction.probability, Prediction.risk_level)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
    )
    return [
        {
            "h3_index": r.h3_index,
            "predicted_at": r.predicted_at.isoformat(),
            "probability": r.probability,
            "risk_level": r.risk_level,
        }
        for r in result.all()
    ]


async def get_aggregate_stats(country_code: str, db: AsyncSession) -> dict:
    from app.models.neighborhood import H3Cell
    from app.models.outage import OutageReport
    from datetime import timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(
            func.count(OutageReport.id).label("outage_count"),
            func.avg(OutageReport.duration_minutes).label("avg_duration"),
        )
        .join(H3Cell, H3Cell.h3_index == OutageReport.h3_index)
        .where(H3Cell.country_code == country_code.upper(), OutageReport.reported_at >= cutoff)
    )
    row = result.first()
    return {
        "country_code": country_code.upper(),
        "outage_count_30d": int(row.outage_count or 0),
        "avg_duration_minutes": round(float(row.avg_duration or 0), 1),
    }
