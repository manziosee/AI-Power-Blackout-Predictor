"""Celery tasks — neighbor alerts, weekly points reset."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.community_tasks.send_neighbor_alerts", bind=True, max_retries=2)
def send_neighbor_alerts(self, report_id: str, h3_index: str, user_id: str):
    """Fire asynchronously after an outage report is created."""
    try:
        asyncio.run(_notify(report_id, h3_index, user_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15)


async def _notify(report_id: str, h3_index: str, user_id: str):
    from app.services.neighbor_alert_service import notify_neighbors
    await notify_neighbors(report_id, h3_index, user_id)


@celery_app.task(name="app.tasks.community_tasks.reset_weekly_points")
def reset_weekly_points():
    """Run every Monday at 00:01 UTC to reset weekly leaderboard."""
    asyncio.run(_reset())


async def _reset():
    from app.services.gamification_service import reset_weekly_points as _do_reset
    await _do_reset()
    log.info("Weekly points reset complete")


@celery_app.task(name="app.tasks.community_tasks.expire_community_notes")
def expire_community_notes():
    """Mark expired community notes as inactive every hour."""
    asyncio.run(_expire())


async def _expire():
    from datetime import datetime, timezone

    from app.core.database import AsyncSessionLocal
    from app.models.community import CommunityNote
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CommunityNote).where(
                CommunityNote.is_active,
                CommunityNote.expires_at <= datetime.now(timezone.utc),
            )
        )
        expired = result.scalars().all()
        for note in expired:
            note.is_active = False
        await db.commit()
        log.info(f"Expired {len(expired)} community notes")
