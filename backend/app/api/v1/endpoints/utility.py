"""Utility Company Dashboard API — B2B portal for power companies."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enterprise import UtilityCompany
from app.models.outage import OutageReport
from app.models.prediction import Prediction

router = APIRouter(prefix="/utility", tags=["utility"])
log = logging.getLogger(__name__)


# ── Utility-key authentication ────────────────────────────────────────────────

async def get_utility(
    x_api_key: str = Header(..., alias="X-Utility-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> UtilityCompany:
    result = await db.execute(
        select(UtilityCompany).where(
            UtilityCompany.api_key == x_api_key,
            UtilityCompany.is_active,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=401, detail="Invalid or inactive utility API key")
    return company


# ── Registration (admin-only in production; open for demo) ────────────────────

class UtilityRegisterRequest(BaseModel):
    name: str
    country_code: str
    contact_email: EmailStr


@router.post("/register", status_code=201)
async def register_utility(payload: UtilityRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a utility company and receive an API key."""
    company = UtilityCompany(
        name=payload.name,
        country_code=payload.country_code.upper(),
        contact_email=str(payload.contact_email),
    )
    db.add(company)
    await db.flush()
    return {
        "id": str(company.id),
        "name": company.name,
        "api_key": company.api_key,
        "plan": company.plan,
        "message": "Store your API key securely — it will not be shown again.",
    }


# ── Dashboard overview ────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(
    company: UtilityCompany = Depends(get_utility),
    db: AsyncSession = Depends(get_db),
):
    """High-level KPIs for the utility's service area."""
    now = datetime.now(timezone.utc)
    d24 = now - timedelta(hours=24)
    d7  = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    base = _cell_filter(company)

    async def count(since: datetime, verified_only: bool = False) -> int:
        q = select(func.count()).where(OutageReport.reported_at >= since)
        if base:
            q = q.where(OutageReport.h3_index.in_(base))
        if verified_only:
            q = q.where(OutageReport.verified)
        return (await db.execute(q)).scalar() or 0

    total_24h   = await count(d24)
    verified_7d = await count(d7, verified_only=True)
    total_30d   = await count(d30)

    # Active (unresolved) outages
    active_q = select(func.count()).where(
        OutageReport.resolved_at.is_(None),
        OutageReport.reported_at >= d24,
    )
    if base:
        active_q = active_q.where(OutageReport.h3_index.in_(base))
    active_count = (await db.execute(active_q)).scalar() or 0

    # Avg resolution time (minutes)
    resolved_q = select(func.avg(OutageReport.duration_minutes)).where(
        OutageReport.duration_minutes.isnot(None),
        OutageReport.reported_at >= d30,
    )
    if base:
        resolved_q = resolved_q.where(OutageReport.h3_index.in_(base))
    avg_duration = (await db.execute(resolved_q)).scalar()

    # High-risk predictions right now
    high_risk_q = select(func.count()).where(
        Prediction.window_start >= now,
        Prediction.probability >= 0.65,
    )
    if base:
        high_risk_q = high_risk_q.where(Prediction.h3_index.in_(base))
    high_risk_count = (await db.execute(high_risk_q)).scalar() or 0

    return {
        "company": company.name,
        "country_code": company.country_code,
        "plan": company.plan,
        "stats": {
            "outages_last_24h": total_24h,
            "active_unresolved": active_count,
            "verified_last_7d": verified_7d,
            "total_last_30d": total_30d,
            "avg_duration_minutes": round(float(avg_duration), 1) if avg_duration else None,
            "high_risk_areas_now": high_risk_count,
        },
        "generated_at": now.isoformat(),
    }


# ── Live outage feed ──────────────────────────────────────────────────────────

@router.get("/outages/live")
async def live_outages(
    hours: int = Query(default=24, ge=1, le=168),
    verified_only: bool = Query(default=False),
    company: UtilityCompany = Depends(get_utility),
    db: AsyncSession = Depends(get_db),
):
    """Return all outage reports in the last N hours for the utility's service area."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    base = _cell_filter(company)

    q = (
        select(OutageReport)
        .where(OutageReport.reported_at >= since)
        .order_by(OutageReport.reported_at.desc())
        .limit(500)
    )
    if base:
        q = q.where(OutageReport.h3_index.in_(base))
    if verified_only:
        q = q.where(OutageReport.verified)

    result = await db.execute(q)
    outages = result.scalars().all()

    return [
        {
            "id": str(o.id),
            "h3_index": o.h3_index,
            "lat": float(o.lat) if o.lat else None,
            "lng": float(o.lng) if o.lng else None,
            "reported_at": o.reported_at.isoformat(),
            "resolved_at": o.resolved_at.isoformat() if o.resolved_at else None,
            "duration_minutes": o.duration_minutes,
            "verification_count": o.verification_count,
            "verified": o.verified,
            "source": o.source,
        }
        for o in outages
    ]


# ── Outage management ─────────────────────────────────────────────────────────

class ResolveRequest(BaseModel):
    duration_minutes: int | None = None
    notes: str | None = None


@router.patch("/outages/{report_id}/resolve")
async def utility_resolve_outage(
    report_id: str,
    payload: ResolveRequest,
    company: UtilityCompany = Depends(get_utility),
    db: AsyncSession = Depends(get_db),
):
    """Allow utility staff to mark an outage as resolved."""
    import uuid as _uuid
    result = await db.execute(select(OutageReport).where(OutageReport.id == _uuid.UUID(report_id)))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.resolved_at = datetime.now(timezone.utc)
    if payload.duration_minutes:
        report.duration_minutes = payload.duration_minutes
    if payload.notes:
        report.notes = (report.notes or "") + f"\n[Utility: {payload.notes}]"
    return {"status": "resolved", "report_id": report_id}


# ── Predictions for service area ──────────────────────────────────────────────

@router.get("/predictions/high-risk")
async def high_risk_predictions(
    threshold: float = Query(default=0.65, ge=0.5, le=1.0),
    company: UtilityCompany = Depends(get_utility),
    db: AsyncSession = Depends(get_db),
):
    """Return high-risk predictions for the utility's service area."""
    now = datetime.now(timezone.utc)
    base = _cell_filter(company)

    q = (
        select(Prediction)
        .where(
            Prediction.window_start >= now,
            Prediction.probability >= threshold,
        )
        .order_by(Prediction.probability.desc())
        .limit(200)
    )
    if base:
        q = q.where(Prediction.h3_index.in_(base))

    result = await db.execute(q)
    preds = result.scalars().all()

    return [
        {
            "h3_index": p.h3_index,
            "probability": p.probability,
            "risk_level": p.risk_level,
            "window_start": p.window_start.isoformat(),
            "window_end": p.window_end.isoformat(),
            "predicted_duration_median": p.predicted_duration_median,
        }
        for p in preds
    ]


# ── Most affected neighborhoods ───────────────────────────────────────────────

@router.get("/neighborhoods/most-affected")
async def most_affected(
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=20, ge=5, le=100),
    company: UtilityCompany = Depends(get_utility),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = _cell_filter(company)

    q = (
        select(
            OutageReport.h3_index,
            func.count().label("outage_count"),
            func.avg(OutageReport.duration_minutes).label("avg_duration"),
        )
        .where(OutageReport.reported_at >= since, OutageReport.verified)
        .group_by(OutageReport.h3_index)
        .order_by(func.count().desc())
        .limit(limit)
    )
    if base:
        q = q.where(OutageReport.h3_index.in_(base))

    rows = (await db.execute(q)).fetchall()

    return [
        {
            "h3_index": r.h3_index,
            "outage_count": r.outage_count,
            "avg_duration_minutes": round(float(r.avg_duration), 1) if r.avg_duration else None,
        }
        for r in rows
    ]


def _cell_filter(company: UtilityCompany) -> list[str] | None:
    cells = company.service_area_h3_cells
    return cells if cells else None
