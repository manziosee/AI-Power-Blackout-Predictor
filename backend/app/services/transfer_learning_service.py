"""Service for transfer learning across regions."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outage import OutageReport
from app.models.transfer_learning import RegionSimilarity


async def get_similar_regions(region: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(RegionSimilarity)
        .where(RegionSimilarity.source_region == region)
        .order_by(RegionSimilarity.similarity_score.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "target_region": r.target_region,
            "similarity_score": r.similarity_score,
            "basis": r.basis,
            "climate_score": r.climate_score,
            "infrastructure_score": r.infrastructure_score,
            "computed_at": r.computed_at.isoformat(),
        }
        for r in rows
    ]


async def list_regions_with_data(db: AsyncSession) -> list[dict]:
    # Assumes outage_reports has a region column or we use h3_cells region
    from app.models.neighborhood import H3Cell
    result = await db.execute(
        select(
            H3Cell.region,
            func.count(OutageReport.id).label("outage_count"),
            func.count(func.distinct(OutageReport.h3_index)).label("h3_cell_count"),
        )
        .join(OutageReport, OutageReport.h3_index == H3Cell.h3_index, isouter=True)
        .where(H3Cell.region.is_not(None))
        .group_by(H3Cell.region)
        .order_by(func.count(OutageReport.id).desc())
    )
    return [
        {
            "region": row.region,
            "outage_count": int(row.outage_count or 0),
            "h3_cell_count": int(row.h3_cell_count or 0),
        }
        for row in result.all()
    ]
