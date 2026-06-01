"""Celery task — fire webhooks when predictions cross thresholds."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.webhook_dispatch.dispatch_prediction_webhooks")
def dispatch_prediction_webhooks():
    """Check recent high-probability predictions and fire registered webhooks."""
    asyncio.run(_dispatch_predictions())


@celery_app.task(
    name="app.tasks.webhook_dispatch.fire_confirmed_outage_webhooks",
    bind=True,
    max_retries=2,
)
def fire_confirmed_outage_webhooks(self, h3_index: str, report_id: str):
    """Immediately fire outage_confirmed webhooks when verification count hits 3."""
    try:
        asyncio.run(_fire_confirmed(h3_index, report_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=20)


async def _dispatch_predictions():
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.prediction import Prediction
    from app.services.webhook_service import fire_prediction_webhooks

    async with AsyncSessionLocal() as db:
        since = datetime.now(timezone.utc) - timedelta(hours=4)
        result = await db.execute(
            select(Prediction).where(
                Prediction.predicted_at >= since,
                Prediction.probability >= 0.50,   # fetch all; individual sub thresholds checked in service
            ).order_by(Prediction.probability.desc()).limit(1000)
        )
        predictions = result.scalars().all()

    log.info(f"Checking webhooks for {len(predictions)} predictions")
    for pred in predictions:
        try:
            fired = await fire_prediction_webhooks(
                h3_index=pred.h3_index,
                probability=pred.probability,
                risk_level=pred.risk_level,
                window_start=pred.window_start.isoformat(),
            )
            if fired:
                log.info(f"Fired {fired} webhooks for {pred.h3_index} ({pred.probability:.0%})")
        except Exception as exc:
            log.error(f"Webhook dispatch error for {pred.h3_index}: {exc}")


async def _fire_confirmed(h3_index: str, report_id: str):
    from app.services.webhook_service import fire_outage_confirmed_webhooks
    fired = await fire_outage_confirmed_webhooks(h3_index, report_id)
    log.info(f"Fired {fired} outage_confirmed webhooks for {h3_index}")
