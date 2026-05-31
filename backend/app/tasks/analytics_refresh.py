"""Celery tasks — refresh accuracy metrics and neighborhood rankings daily."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.analytics_refresh.refresh_all_accuracy")
def refresh_all_accuracy():
    asyncio.run(_refresh_accuracy())


async def _refresh_accuracy():
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.neighborhood import H3Cell
    from app.services.accuracy_service import persist_accuracy

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(H3Cell.h3_index).limit(5000))
        indices = [r[0] for r in result.fetchall()]

    log.info(f"Refreshing accuracy for {len(indices)} cells")
    for h3_index in indices:
        try:
            await persist_accuracy(h3_index, days=30)
        except Exception as exc:
            log.error(f"Accuracy refresh failed for {h3_index}: {exc}")


@celery_app.task(name="app.tasks.analytics_refresh.refresh_rankings")
def refresh_rankings():
    asyncio.run(_refresh_rankings())


async def _refresh_rankings():
    from app.services.ranking_service import refresh_neighborhood_stats

    count = await refresh_neighborhood_stats()
    log.info(f"Refreshed neighborhood stats for {count} cells")
