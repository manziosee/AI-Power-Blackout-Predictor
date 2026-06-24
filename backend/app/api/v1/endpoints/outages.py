import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.ws_manager import manager as ws_manager
from app.models.outage import OutageReport
from app.models.user import User
from app.schemas.outage import OutageReportCreate, OutageReportOut, OutageResolve
from app.services.outage_service import resolve_h3_from_coords

router = APIRouter(prefix="/outages", tags=["Outage Reports"])


@router.post("/report", response_model=OutageReportOut, status_code=status.HTTP_201_CREATED,
             summary="Submit a new outage report",
             description="Report a power outage at a given H3 cell or lat/lng coordinate. Awards gamification points and triggers neighbor alerts.")
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

    # Broadcast to live WebSocket subscribers
    await ws_manager.broadcast({
        "event": "new_report",
        "h3_index": h3_index,
        "id": str(report.id),
        "verified": report.verified,
    })

    # Fraud check (non-blocking — flags written to session, committed with report)
    from app.services.fraud_service import check_report
    await check_report(db, report)

    # Award points + trigger neighbor alert asynchronously
    from app.services.gamification_service import award_points
    from app.tasks.community_tasks import send_neighbor_alerts
    await award_points(current_user.id, "report", str(report.id), db)
    send_neighbor_alerts.delay(str(report.id), h3_index, str(current_user.id))

    return report


@router.get("/cell/{h3_index}", response_model=List[OutageReportOut],
            summary="List recent outage reports for a cell")
async def get_cell_outages(h3_index: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OutageReport)
        .where(OutageReport.h3_index == h3_index)
        .order_by(OutageReport.reported_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/cell/{h3_index}/neighbor-stats",
            summary="Social-proof stats for a cell and its neighbors",
            description="Returns report counts for the given cell and its immediate H3 neighbors in the last hour — used to show 'X people nearby reported an outage'.")
async def get_neighbor_stats(h3_index: str, db: AsyncSession = Depends(get_db)):
    import h3 as _h3
    from sqlalchemy import func as sqlfunc

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    nearby_cells = list(_h3.grid_disk(h3_index, 1))  # includes the center cell

    counts = (await db.execute(
        select(OutageReport.h3_index, sqlfunc.count().label("n"))
        .where(OutageReport.h3_index.in_(nearby_cells), OutageReport.reported_at >= since)
        .group_by(OutageReport.h3_index)
    )).fetchall()

    count_map = {r.h3_index: r.n for r in counts}
    this_cell = count_map.get(h3_index, 0)
    neighbor_total = sum(v for k, v in count_map.items() if k != h3_index)
    total = this_cell + neighbor_total

    if total == 0:
        message = "No outages reported nearby in the last hour."
    elif total == 1:
        message = "1 person reported a power outage in the last hour."
    else:
        message = f"{total} people reported power outages nearby in the last hour."

    return {
        "h3_index": h3_index,
        "reports_this_cell": this_cell,
        "reports_nearby": neighbor_total,
        "total_reports_last_hour": total,
        "message": message,
    }


@router.patch("/{report_id}/resolve", response_model=OutageReportOut,
              summary="Mark your outage as resolved")
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


@router.get("/{report_id}/timeline", response_model=TimelineOut,
            summary="Step-by-step timeline for an outage report",
            description="Returns ordered milestones: reported → confirmed → utility notified → crew assigned → crew on-site → restored.")
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


@router.post("/{report_id}/confirm", response_model=OutageReportOut,
             summary="Confirm another user's outage report",
             description="Trust-weighted confirmation. A report auto-verifies when its weighted score reaches 3.0 (equivalent to 3 average-trust confirmers), triggering instant SMS/push alerts.")
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


# ── GeoJSON map feed ──────────────────────────────────────────────────────────

@router.get("/map/geojson",
            summary="GeoJSON FeatureCollection of active outage reports",
            description="Returns a GeoJSON FeatureCollection of recent unresolved outage reports for map overlay rendering. Filter by country_code or bounding box.")
async def outage_geojson(
    country_code: str | None = None,
    hours: int = 24,
    lat_min: float | None = None,
    lat_max: float | None = None,
    lng_min: float | None = None,
    lng_max: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = (
        select(OutageReport)
        .where(
            OutageReport.reported_at >= since,
            OutageReport.resolved_at.is_(None),
            OutageReport.lat.isnot(None),
            OutageReport.lng.isnot(None),
        )
        .order_by(OutageReport.reported_at.desc())
        .limit(2000)
    )

    if country_code:
        from app.models.neighborhood import H3Cell
        cells_in_country = (await db.execute(
            select(H3Cell.h3_index).where(H3Cell.country_code == country_code.upper())
        )).scalars().all()
        if cells_in_country:
            q = q.where(OutageReport.h3_index.in_(cells_in_country))

    if lat_min is not None:
        q = q.where(OutageReport.lat >= lat_min)
    if lat_max is not None:
        q = q.where(OutageReport.lat <= lat_max)
    if lng_min is not None:
        q = q.where(OutageReport.lng >= lng_min)
    if lng_max is not None:
        q = q.where(OutageReport.lng <= lng_max)

    reports = (await db.execute(q)).scalars().all()

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(r.lng), float(r.lat)],
            },
            "properties": {
                "id": str(r.id),
                "h3_index": r.h3_index,
                "reported_at": r.reported_at.isoformat(),
                "verified": r.verified,
                "verification_count": r.verification_count,
                "source": r.source,
            },
        }
        for r in reports
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "total": len(features),
            "hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
