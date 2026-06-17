"""Celery tasks for resilience score computation."""
import asyncio
import logging

logger = logging.getLogger(__name__)


def recompute_all_resilience_scores() -> None:
    """
    Weekly Celery task: iterate all h3_cells and recompute resilience scores.
    """
    try:
        async def _run():
            from app.core.database import AsyncSessionLocal
            from app.models.neighborhood import H3Cell
            from app.services.resilience_service import compute_score
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(H3Cell.h3_index))
                cells = [r[0] for r in result.all()]
                logger.info("Recomputing resilience scores for %d cells", len(cells))
                for h3_index in cells:
                    try:
                        await compute_score(h3_index, db)
                    except Exception as exc:
                        logger.warning("Failed to compute score for %s: %s", h3_index, exc)
                await db.commit()
                logger.info("Resilience score recomputation complete")

        asyncio.run(_run())
    except Exception as exc:
        logger.error("recompute_all_resilience_scores failed: %s", exc)
        raise
