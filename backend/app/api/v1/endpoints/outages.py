import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
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
    from datetime import datetime, timezone

    result = await db.execute(
        select(OutageReport).where(OutageReport.id == report_id, OutageReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.resolved_at = datetime.now(timezone.utc)
    report.duration_minutes = payload.duration_minutes
    return report


@router.post("/{report_id}/confirm", response_model=OutageReportOut)
async def confirm_outage(
    report_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Another user confirms an existing outage report — increases verification count.
    When count reaches 3 the report is auto-verified and an instant SMS/push alert fires."""
    from app.tasks.instant_alert import confirmed_outage_alert

    result = await db.execute(select(OutageReport).where(OutageReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.verification_count += 1

    just_verified = not report.verified and report.verification_count >= 3
    if just_verified:
        report.verified = True

    await db.flush()

    # Award confirm points to the confirmer
    from app.services.gamification_service import award_points
    await award_points(_.id, "confirm", str(report.id), db)

    # Fire instant alerts when newly verified
    if just_verified:
        confirmed_outage_alert.delay(report.h3_index, str(report.id))
        from app.tasks.webhook_dispatch import fire_confirmed_outage_webhooks
        fire_confirmed_outage_webhooks.delay(report.h3_index, str(report.id))

    return report
