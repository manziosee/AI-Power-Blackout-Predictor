import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.outage import OutageReport
from app.models.user import User
from app.schemas.outage import OutageReportCreate, OutageReportOut, OutageResolve
from app.services.outage_service import resolve_h3_from_coords

router = APIRouter(prefix="/outages", tags=["outages"])


@router.post("/report", response_model=OutageReportOut, status_code=status.HTTP_201_CREATED)
async def report_outage(
    payload: OutageReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h3_index = payload.h3_index
    if not h3_index and payload.lat and payload.lng:
        h3_index = resolve_h3_from_coords(payload.lat, payload.lng)
    if not h3_index:
        raise HTTPException(status_code=400, detail="Provide h3_index or lat/lng")

    report = OutageReport(
        user_id=current_user.id,
        h3_index=h3_index,
        lat=payload.lat,
        lng=payload.lng,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(report)
    await db.flush()

    # Fraud check (non-blocking — flags written to session, committed with report)
    from app.services.fraud_service import check_report
    await check_report(db, report)

    # Award points + trigger neighbor alert asynchronously
    from app.services.gamification_service import award_points
    from app.tasks.community_tasks import send_neighbor_alerts
    await award_points(current_user.id, "report", str(report.id), db)
    send_neighbor_alerts.delay(str(report.id), h3_index, str(current_user.id))

    return report


@router.get("/cell/{h3_index}", response_model=List[OutageReportOut])
async def get_cell_outages(h3_index: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OutageReport)
        .where(OutageReport.h3_index == h3_index)
        .order_by(OutageReport.reported_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.patch("/{report_id}/resolve", response_model=OutageReportOut)
async def resolve_outage(
    report_id: uuid.UUID,
    payload: OutageResolve,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OutageReport).where(OutageReport.id == report_id, OutageReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.resolved_at = datetime.now(timezone.utc)
    report.duration_minutes = payload.duration_minutes
    return report


# ── Timeline ────────────────────────────────────────────────────────────────

class TimelineEventOut(BaseModel):
    step: str
    label: str
    occurred_at: datetime | None
    pending: bool

    model_config = {"from_attributes": True}


class TimelineOut(BaseModel):
    report_id: uuid.UUID
    events: list[TimelineEventOut]


@router.get("/{report_id}/timeline", response_model=TimelineOut)
async def get_outage_timeline(report_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.services.timeline_service import build_timeline
    events = await build_timeline(report_id, db)
    if events is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return TimelineOut(
        report_id=report_id,
        events=[TimelineEventOut(
            step=e.step, label=e.label, occurred_at=e.occurred_at, pending=e.pending
        ) for e in events],
    )


@router.post("/{report_id}/confirm", response_model=OutageReportOut)
async def confirm_outage(
    report_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Another user confirms an existing outage report — increases verification count.
    When count reaches 3 the report is auto-verified and an instant SMS/push alert fires."""
    from app.tasks.instant_alert import confirmed_outage_alert

    from app.models.community import UserPoints
    from app.services.gamification_service import award_points

    result = await db.execute(select(OutageReport).where(OutageReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Look up confirmer's trust score (default 0.5 for new users)
    up_result = await db.execute(select(UserPoints).where(UserPoints.user_id == _.id))
    up = up_result.scalar_one_or_none()
    trust = float(up.trust_score) if up else 0.5

    report.verification_count += 1
    report.weighted_verification_score = (report.weighted_verification_score or 0.0) + trust
    if report.confirmed_at is None and report.verification_count >= 2:
        report.confirmed_at = datetime.now(timezone.utc)

    # Verified when weighted score reaches 3.0 (equivalent to 3 avg-trust users)
    just_verified = not report.verified and report.weighted_verification_score >= 3.0
    if just_verified:
        report.verified = True

    await db.flush()

    await award_points(_.id, "confirm", str(report.id), db)

    # Update confirmer's trust score after confirming
    from app.services.gamification_service import recompute_trust_score
    await recompute_trust_score(_.id, db)

    if just_verified:
        confirmed_outage_alert.delay(report.h3_index, str(report.id))
        from app.tasks.webhook_dispatch import fire_confirmed_outage_webhooks
        fire_confirmed_outage_webhooks.delay(report.h3_index, str(report.id))
        # Auto-create restoration tracking event
        from app.services.restoration_service import create_restoration_event
        await create_restoration_event(report.id, report.h3_index, None, db)

    return report
