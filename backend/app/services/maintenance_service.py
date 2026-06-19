"""Predictive maintenance scoring for grid transformers.

Risk score formula (0.0 – 1.0):
  - age_factor        (age_years / 50)                         → 30%
  - outage_density    (outages_90d in coverage cells / 20)     → 35%
  - cascade_risk      from latest GNN prediction               → 20%
  - maintenance_lag   (days since last maintenance / 365)      → 15%
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


async def score_all_transformers(db: AsyncSession) -> int:
    from app.models.gnn_model import GnnPrediction
    from app.models.grid_topology import GridTransformer, TransformerCellCoverage
    from app.models.outage import OutageReport

    cutoff_90d = datetime.now(timezone.utc) - timedelta(days=90)

    transformers_res = await db.execute(
        select(GridTransformer).where(GridTransformer.status != "decommissioned")
    )
    transformers = transformers_res.scalars().all()

    # Outage counts per cell for past 90 days
    outage_counts_res = await db.execute(
        select(OutageReport.h3_index, func.count(OutageReport.id).label("cnt"))
        .where(OutageReport.reported_at >= cutoff_90d, OutageReport.verified)
        .group_by(OutageReport.h3_index)
    )
    outage_by_cell: dict[str, int] = {r.h3_index: r.cnt for r in outage_counts_res.all()}

    # Latest cascade risk per transformer from GNN
    gnn_res = await db.execute(
        select(GnnPrediction.transformer_id, func.max(GnnPrediction.cascade_risk).label("max_risk"))
        .group_by(GnnPrediction.transformer_id)
    )
    gnn_by_transformer: dict = {str(r.transformer_id): float(r.max_risk or 0.0) for r in gnn_res.all()}

    # Coverage cells per transformer
    coverage_res = await db.execute(select(TransformerCellCoverage))
    coverage_by_transformer: dict[str, list[str]] = {}
    for row in coverage_res.scalars().all():
        tid = str(row.transformer_id)
        coverage_by_transformer.setdefault(tid, []).append(row.h3_index)

    now = datetime.now(timezone.utc)
    scored = 0

    for t in transformers:
        tid = str(t.id)
        cells = coverage_by_transformer.get(tid, [])

        # Age factor
        age = min(float(t.age_years or 0) / 50.0, 1.0)

        # Outage density across covered cells
        total_outages = sum(outage_by_cell.get(c, 0) for c in cells)
        density = min(float(total_outages) / max(len(cells), 1) / 5.0, 1.0)

        # Cascade risk from GNN
        cascade = gnn_by_transformer.get(tid, 0.0)

        # Maintenance lag
        if t.last_maintenance_at:
            days_since = (now - t.last_maintenance_at).days
        else:
            days_since = 730  # assume 2 years if unknown
        maint_lag = min(float(days_since) / 365.0, 1.0)

        score = round(age * 0.30 + density * 0.35 + cascade * 0.20 + maint_lag * 0.15, 4)

        t.maintenance_risk_score = score
        t.failure_count_90d = total_outages
        t.last_scored_at = now
        scored += 1

    await db.flush()
    return scored


async def get_top_at_risk(utility_id, limit: int, db: AsyncSession) -> list[dict]:
    from app.models.grid_topology import GridTransformer
    from sqlalchemy import desc

    query = (
        select(GridTransformer)
        .where(GridTransformer.maintenance_risk_score.isnot(None))
        .order_by(desc(GridTransformer.maintenance_risk_score))
        .limit(limit)
    )
    if utility_id:
        query = query.where(GridTransformer.utility_id == utility_id)

    result = await db.execute(query)
    transformers = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "h3_index": t.h3_index,
            "risk_score": t.maintenance_risk_score,
            "risk_label": _risk_label(t.maintenance_risk_score),
            "age_years": t.age_years,
            "failure_count_90d": t.failure_count_90d,
            "last_maintenance_at": t.last_maintenance_at.isoformat() if t.last_maintenance_at else None,
            "last_scored_at": t.last_scored_at.isoformat() if t.last_scored_at else None,
            "lat": float(t.lat) if t.lat else None,
            "lng": float(t.lng) if t.lng else None,
        }
        for t in transformers
    ]


def _risk_label(score: float | None) -> str:
    if score is None:
        return "unscored"
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.50:
        return "HIGH"
    if score >= 0.25:
        return "MEDIUM"
    return "LOW"
