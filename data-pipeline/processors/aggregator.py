"""Aggregate per-cell statistics for the ML feature store."""
import os

import sqlalchemy as sa

DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:password@localhost:5432/blackout_predictor")
engine = sa.create_engine(DATABASE_URL)


def refresh_cell_stats() -> None:
    """Materialize outage stats per H3 cell into a summary table (future: cell_stats)."""
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS cell_stats AS
            SELECT
                h3_index,
                COUNT(*) FILTER (WHERE reported_at >= NOW() - INTERVAL '7 days')  AS outages_7d,
                COUNT(*) FILTER (WHERE reported_at >= NOW() - INTERVAL '30 days') AS outages_30d,
                AVG(duration_minutes)                                              AS avg_duration_min,
                MAX(reported_at)                                                   AS last_outage_at
            FROM outage_reports
            WHERE verified = TRUE
            GROUP BY h3_index
            ON CONFLICT DO NOTHING
        """))
