"""Service for regulatory reporting."""
from datetime import datetime, timezone

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.neighborhood import H3Cell
from app.models.outage import OutageReport
from app.models.regulatory import RegulatoryReport


def calculate_uptime(total_hours_in_period: float, total_outage_hours: float) -> float:
    if total_hours_in_period <= 0:
        return 100.0
    uptime = (1 - total_outage_hours / total_hours_in_period) * 100.0
    return round(max(0.0, min(100.0, uptime)), 2)


async def generate_report(
    country_code: str,
    district: str | None,
    year: int,
    month: int,
    db: AsyncSession,
) -> RegulatoryReport:
    import calendar

    # Hours in the month
    days_in_month = calendar.monthrange(year, month)[1]
    total_hours = days_in_month * 24.0

    # Query outage data for country/district/month
    query = select(
        func.count(OutageReport.id).label("total"),
        func.sum(OutageReport.duration_minutes).label("sum_minutes"),
        func.avg(OutageReport.duration_minutes).label("avg_repair"),
        func.count(func.distinct(OutageReport.h3_index)).label("affected_cells"),
    ).join(H3Cell, H3Cell.h3_index == OutageReport.h3_index, isouter=True).where(
        H3Cell.country_code == country_code,
        extract("year", OutageReport.reported_at) == year,
        extract("month", OutageReport.reported_at) == month,
    )

    if district:
        query = query.where(H3Cell.region == district)

    result = await db.execute(query)
    row = result.one_or_none()

    total_outages = int(row.total or 0) if row else 0
    total_outage_hours = round((row.sum_minutes or 0) / 60.0, 2) if row else 0.0
    avg_repair = round(row.avg_repair, 1) if row and row.avg_repair else None
    affected_cells = int(row.affected_cells or 0) if row else 0
    uptime_pct = calculate_uptime(total_hours, total_outage_hours)

    # Find worst cell
    worst_result = await db.execute(
        select(OutageReport.h3_index, func.count().label("cnt"))
        .join(H3Cell, H3Cell.h3_index == OutageReport.h3_index, isouter=True)
        .where(
            H3Cell.country_code == country_code,
            extract("year", OutageReport.reported_at) == year,
            extract("month", OutageReport.reported_at) == month,
        )
        .group_by(OutageReport.h3_index)
        .order_by(func.count().desc())
        .limit(1)
    )
    worst_row = worst_result.one_or_none()
    worst_cell = worst_row[0] if worst_row else None

    # Upsert
    existing = await db.execute(
        select(RegulatoryReport).where(
            RegulatoryReport.country_code == country_code,
            RegulatoryReport.district == district,
            RegulatoryReport.report_year == year,
            RegulatoryReport.report_month == month,
        )
    )
    report = existing.scalar_one_or_none()
    if report is None:
        report = RegulatoryReport(
            country_code=country_code,
            district=district,
            report_year=year,
            report_month=month,
        )
        db.add(report)

    report.total_outages = total_outages
    report.total_outage_hours = total_outage_hours
    report.uptime_pct = uptime_pct
    report.affected_cells_count = affected_cells
    report.worst_cell_h3 = worst_cell
    report.avg_repair_minutes = avg_repair
    report.generated_at = datetime.now(timezone.utc)
    await db.flush()
    return report
