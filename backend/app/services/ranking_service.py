"""Compute and return neighborhood outage rankings."""
import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)


async def get_rankings(country_code: str, limit: int = 20, period_days: int = 30) -> list[dict]:
    """Return top N most-affected H3 cells in a country, sorted by outage count."""
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import NeighborhoodStats
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NeighborhoodStats).where(
                NeighborhoodStats.country_code == country_code.upper()
            ).order_by(
                NeighborhoodStats.outages_30d.desc()
            ).limit(limit)
        )
        rows = result.scalars().all()

    return [
        {
            "rank": i + 1,
            "h3_index": r.h3_index,
            "city": r.city or "Unknown",
            "country_code": r.country_code,
            "outages_7d": r.outages_7d,
            "outages_30d": r.outages_30d,
            "outages_90d": r.outages_90d,
            "avg_duration_minutes": r.avg_duration_minutes,
            "avg_probability_7d": r.avg_probability_7d,
            "rank_in_country": r.rank_country,
            "rank_in_city": r.rank_city,
        }
        for i, r in enumerate(rows)
    ]


async def get_cell_rank(h3_index: str) -> dict | None:
    """Return ranking info for a specific H3 cell."""
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import NeighborhoodStats
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NeighborhoodStats).where(NeighborhoodStats.h3_index == h3_index)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        # Total cells in same country for context
        total = await db.execute(
            select(func.count()).where(
                NeighborhoodStats.country_code == row.country_code,
                NeighborhoodStats.outages_30d > 0,
            )
        )
        total_count = total.scalar() or 1

    return {
        "h3_index": h3_index,
        "city": row.city or "Unknown",
        "country_code": row.country_code,
        "outages_7d": row.outages_7d,
        "outages_30d": row.outages_30d,
        "rank_in_country": row.rank_country,
        "rank_in_city": row.rank_city,
        "total_ranked_cells": total_count,
        "percentile": round((1 - (row.rank_country or total_count) / total_count) * 100, 1) if row.rank_country else None,
    }


async def refresh_neighborhood_stats() -> int:
    """Recompute NeighborhoodStats for all tracked cells. Returns number updated."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select, text

    from app.core.database import AsyncSessionLocal
    from app.models.analytics import NeighborhoodStats
    from app.models.neighborhood import H3Cell
    from app.models.outage import OutageReport
    from app.models.prediction import Prediction

    now = datetime.now(timezone.utc)
    d7, d30, d90 = now - timedelta(days=7), now - timedelta(days=30), now - timedelta(days=90)

    async with AsyncSessionLocal() as db:
        cells_result = await db.execute(select(H3Cell))
        cells = cells_result.scalars().all()
        updated = 0

        for cell in cells:
            h3 = cell.h3_index

            def count_outages(since):
                return select(func.count()).where(
                    OutageReport.h3_index == h3,
                    OutageReport.reported_at >= since,
                    OutageReport.verified == True,
                )

            c7  = (await db.execute(count_outages(d7))).scalar() or 0
            c30 = (await db.execute(count_outages(d30))).scalar() or 0
            c90 = (await db.execute(count_outages(d90))).scalar() or 0

            avg_dur = (await db.execute(
                select(func.avg(OutageReport.duration_minutes)).where(
                    OutageReport.h3_index == h3,
                    OutageReport.duration_minutes.isnot(None),
                )
            )).scalar()

            avg_prob = (await db.execute(
                select(func.avg(Prediction.probability)).where(
                    Prediction.h3_index == h3,
                    Prediction.predicted_at >= d7,
                )
            )).scalar()

            existing = await db.execute(
                select(NeighborhoodStats).where(NeighborhoodStats.h3_index == h3)
            )
            stat = existing.scalar_one_or_none()

            if stat:
                stat.outages_7d = c7
                stat.outages_30d = c30
                stat.outages_90d = c90
                stat.avg_duration_minutes = float(avg_dur) if avg_dur else None
                stat.avg_probability_7d = float(avg_prob) if avg_prob else None
                stat.city = cell.city
                stat.country_code = cell.country_code
                stat.updated_at = now
            else:
                db.add(NeighborhoodStats(
                    h3_index=h3,
                    country_code=cell.country_code,
                    city=cell.city,
                    outages_7d=c7,
                    outages_30d=c30,
                    outages_90d=c90,
                    avg_duration_minutes=float(avg_dur) if avg_dur else None,
                    avg_probability_7d=float(avg_prob) if avg_prob else None,
                ))
            updated += 1

        await db.flush()

        # Compute rankings within each country
        await db.execute(text("""
            WITH ranked AS (
                SELECT h3_index,
                       RANK() OVER (PARTITION BY country_code ORDER BY outages_30d DESC) AS rank_c,
                       RANK() OVER (PARTITION BY city ORDER BY outages_30d DESC) AS rank_ci
                FROM neighborhood_stats
            )
            UPDATE neighborhood_stats ns
            SET rank_country = r.rank_c,
                rank_city    = r.rank_ci
            FROM ranked r
            WHERE ns.h3_index = r.h3_index
        """))

        await db.commit()
    return updated
