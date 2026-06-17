"""Service for seasonal decomposition dashboard."""
import calendar
from datetime import datetime, timezone

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outage import OutageReport
from app.models.seasonal import SeasonalStats


async def compute_stats_for_cell(h3_index: str, db: AsyncSession) -> None:
    """Aggregate outage data into seasonal_stats."""
    result = await db.execute(
        select(
            extract("year", OutageReport.reported_at).label("yr"),
            extract("month", OutageReport.reported_at).label("mo"),
            func.count().label("cnt"),
            func.avg(OutageReport.duration_minutes).label("avg_dur"),
            func.sum(OutageReport.duration_minutes).label("sum_dur"),
        )
        .where(OutageReport.h3_index == h3_index)
        .group_by("yr", "mo")
    )
    rows = result.all()

    for row in rows:
        year = int(row.yr)
        month = int(row.mo)
        total_hours = (row.sum_dur / 60.0) if row.sum_dur else None

        existing = await db.execute(
            select(SeasonalStats).where(
                SeasonalStats.h3_index == h3_index,
                SeasonalStats.year == year,
                SeasonalStats.month == month,
            )
        )
        stat = existing.scalar_one_or_none()
        if stat is None:
            stat = SeasonalStats(h3_index=h3_index, year=year, month=month)
            db.add(stat)

        stat.outage_count = int(row.cnt)
        stat.avg_duration_minutes = round(row.avg_dur, 1) if row.avg_dur else None
        stat.total_outage_hours = round(total_hours, 2) if total_hours else None
        stat.computed_at = datetime.now(timezone.utc)

    await db.flush()


async def get_worst_months(h3_index: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            SeasonalStats.month,
            func.avg(SeasonalStats.outage_count).label("avg_outages"),
            func.avg(SeasonalStats.avg_duration_minutes).label("avg_duration"),
        )
        .where(SeasonalStats.h3_index == h3_index)
        .group_by(SeasonalStats.month)
        .order_by(func.avg(SeasonalStats.outage_count).desc())
        .limit(3)
    )
    return [
        {
            "month": row.month,
            "month_name": calendar.month_name[row.month],
            "avg_outages": round(row.avg_outages, 1),
            "avg_duration": round(row.avg_duration, 1) if row.avg_duration else None,
        }
        for row in result.all()
    ]


async def get_year_over_year(h3_index: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            SeasonalStats.year,
            func.sum(SeasonalStats.outage_count).label("total_outages"),
            func.sum(SeasonalStats.total_outage_hours).label("total_hours"),
        )
        .where(SeasonalStats.h3_index == h3_index)
        .group_by(SeasonalStats.year)
        .order_by(SeasonalStats.year)
    )
    return [
        {
            "year": row.year,
            "total_outages": int(row.total_outages or 0),
            "total_hours": round(row.total_hours, 2) if row.total_hours else None,
        }
        for row in result.all()
    ]
