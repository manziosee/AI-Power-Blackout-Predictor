"""Celery task — cluster recent outage reports into incidents."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.incident_cluster.cluster_outages_task")
def cluster_outages_task():
    asyncio.run(_cluster())


async def _cluster():
    from app.core.database import AsyncSessionLocal
    from app.services.incident_service import cluster_recent_outages

    async with AsyncSessionLocal() as db:
        incidents = await cluster_recent_outages(db)
        await db.commit()
        if incidents:
            logger.info(f"Created {len(incidents)} outage incidents from clustering")
