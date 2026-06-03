"""
Fraud / spam detection for outage reports.

Rules checked on every inbound report:
  rate_limit          — user submitted >10 reports in the last hour
  h3_flood            — same H3 cell has >8 reports from the same user in 30 min
  coord_mismatch      — lat/lng provided but resolves to a different H3 cell than declared
  location_impossible — lat/lng is >500 km from the center of the declared H3 cell
"""
import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fraud import FraudFlag
from app.models.outage import OutageReport

RATE_LIMIT_COUNT = 10       # max reports per user per hour
H3_FLOOD_COUNT = 8          # max reports per user per H3 cell per 30 min
MAX_COORD_DISTANCE_KM = 500 # impossible location threshold


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _h3_center(h3_index: str) -> tuple[float, float] | None:
    try:
        import h3
        lat, lng = h3.h3_to_geo(h3_index)
        return lat, lng
    except Exception:
        return None


async def _flag(db: AsyncSession, user_id: uuid.UUID | None, report_id: uuid.UUID,
                rule: str, detail: str, severity: str = "medium") -> None:
    flag = FraudFlag(
        user_id=user_id,
        report_id=report_id,
        rule=rule,
        detail=detail,
        severity=severity,
    )
    db.add(flag)


async def check_report(
    db: AsyncSession,
    report: OutageReport,
) -> list[str]:
    """
    Run all fraud checks against the given (already-added-but-not-committed) report.
    Returns list of triggered rule names. Flags are written to the session.
    """
    triggered: list[str] = []
    now = datetime.now(timezone.utc)
    user_id = report.user_id

    if user_id is None:
        return triggered   # anonymous reports — skip user-scoped checks

    # ── 1. Rate limit: >10 reports in last hour ───────────────────────────────
    count_1h = (await db.execute(
        select(func.count()).select_from(OutageReport).where(
            OutageReport.user_id == user_id,
            OutageReport.reported_at >= now - timedelta(hours=1),
        )
    )).scalar_one()
    if count_1h > RATE_LIMIT_COUNT:
        await _flag(db, user_id, report.id, "rate_limit",
                    f"{count_1h} reports in the last hour (limit {RATE_LIMIT_COUNT})", "high")
        triggered.append("rate_limit")

    # ── 2. H3 flood: >8 reports for same cell in 30 min ──────────────────────
    count_cell = (await db.execute(
        select(func.count()).select_from(OutageReport).where(
            OutageReport.user_id == user_id,
            OutageReport.h3_index == report.h3_index,
            OutageReport.reported_at >= now - timedelta(minutes=30),
        )
    )).scalar_one()
    if count_cell > H3_FLOOD_COUNT:
        await _flag(db, user_id, report.id, "h3_flood",
                    f"{count_cell} reports for cell {report.h3_index} in 30 min (limit {H3_FLOOD_COUNT})", "high")
        triggered.append("h3_flood")

    # ── 3 & 4. Coordinate checks (only if lat/lng provided) ──────────────────
    if report.lat is not None and report.lng is not None:
        center = _h3_center(report.h3_index)
        if center:
            cell_lat, cell_lng = center
            dist_km = _haversine_km(report.lat, report.lng, cell_lat, cell_lng)

            # location_impossible: >500 km from cell center
            if dist_km > MAX_COORD_DISTANCE_KM:
                await _flag(db, user_id, report.id, "location_impossible",
                            f"Reported coords ({report.lat:.4f},{report.lng:.4f}) are {dist_km:.0f} km from cell {report.h3_index}",
                            "medium")
                triggered.append("location_impossible")

            # coord_mismatch: cell from lat/lng doesn't match declared h3_index
            try:
                import h3
                actual_cell = h3.geo_to_h3(report.lat, report.lng, len(report.h3_index) - 1)
                if actual_cell != report.h3_index:
                    await _flag(db, user_id, report.id, "coord_mismatch",
                                f"Coords resolve to {actual_cell}, declared {report.h3_index}",
                                "low")
                    triggered.append("coord_mismatch")
            except Exception:
                pass

    return triggered


async def bulk_scan(db: AsyncSession, since_hours: int = 24) -> int:
    """
    Periodic scan: find users with high report volumes and flag them.
    Returns count of new flags created.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=since_hours)

    rows = await db.execute(
        select(OutageReport.user_id, func.count().label("cnt"))
        .where(OutageReport.reported_at >= cutoff, OutageReport.user_id.isnot(None))
        .group_by(OutageReport.user_id)
        .having(func.count() > RATE_LIMIT_COUNT * since_hours)
    )
    flagged = 0
    for row in rows:
        existing = (await db.execute(
            select(func.count()).select_from(FraudFlag).where(
                FraudFlag.user_id == row.user_id,
                FraudFlag.rule == "rate_limit",
                FraudFlag.resolved == False,
            )
        )).scalar_one()
        if not existing:
            db.add(FraudFlag(
                user_id=row.user_id,
                rule="rate_limit",
                detail=f"Bulk scan: {row.cnt} reports in {since_hours}h window",
                severity="high",
            ))
            flagged += 1
    await db.commit()
    return flagged
