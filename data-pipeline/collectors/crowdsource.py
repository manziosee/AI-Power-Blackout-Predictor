"""Process and verify crowdsourced outage reports — auto-verify when ≥3 users confirm."""
import logging
import os

import sqlalchemy as sa

log = logging.getLogger(__name__)
DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:password@localhost:5432/blackout_predictor")
engine = sa.create_engine(DATABASE_URL)


def auto_verify_reports() -> int:
    """Mark reports as verified when verification_count >= 3."""
    with engine.begin() as conn:
        result = conn.execute(
            sa.text("""
                UPDATE outage_reports
                SET verified = TRUE
                WHERE verified = FALSE AND verification_count >= 3
                RETURNING id
            """)
        )
        count = len(result.fetchall())
    log.info(f"Auto-verified {count} outage reports")
    return count


def resolve_stale_outages(max_duration_hours: int = 12) -> int:
    """Auto-resolve outages with no resolution after max_duration_hours."""
    with engine.begin() as conn:
        result = conn.execute(
            sa.text("""
                UPDATE outage_reports
                SET resolved_at = NOW()
                WHERE resolved_at IS NULL
                  AND reported_at < NOW() - INTERVAL ':hours hours'
                RETURNING id
            """).bindparams(hours=max_duration_hours)
        )
        count = len(result.fetchall())
    log.info(f"Auto-resolved {count} stale outage reports")
    return count


if __name__ == "__main__":
    auto_verify_reports()
    resolve_stale_outages()
