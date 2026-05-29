"""Celery task — send Telegram alerts when outage probability crosses threshold."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.telegram_alert.dispatch_telegram_alerts")
def dispatch_telegram_alerts():
    asyncio.run(_dispatch())


async def _dispatch():
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription
    from app.models.notifications import TelegramSubscription
    from app.models.prediction import Prediction
    from app.models.user import User
    from app.services.telegram_service import send_outage_alert

    async with AsyncSessionLocal() as db:
        since = datetime.now(timezone.utc) - timedelta(hours=4)

        tg_subs = await db.execute(
            select(TelegramSubscription).where(
                TelegramSubscription.is_active == True,
                TelegramSubscription.h3_index.isnot(None),
            )
        )
        tg_list = tg_subs.scalars().all()

        for tg_sub in tg_list:
            pred_result = await db.execute(
                select(Prediction).where(
                    Prediction.h3_index == tg_sub.h3_index,
                    Prediction.predicted_at >= since,
                ).order_by(Prediction.probability.desc()).limit(1)
            )
            prediction = pred_result.scalar_one_or_none()
            if not prediction:
                continue

            # Check if this user has an alert subscription threshold
            threshold = 0.70
            if tg_sub.user_id:
                alert_result = await db.execute(
                    select(AlertSubscription).where(
                        AlertSubscription.user_id == tg_sub.user_id,
                        AlertSubscription.h3_index == tg_sub.h3_index,
                        AlertSubscription.is_active == True,
                    )
                )
                alert_sub = alert_result.scalar_one_or_none()
                if alert_sub:
                    if "telegram" not in (alert_sub.channels or []):
                        continue
                    threshold = float(alert_sub.threshold_probability)

            if prediction.probability < threshold:
                continue

            try:
                await send_outage_alert(
                    chat_id=tg_sub.chat_id,
                    probability=int(prediction.probability * 100),
                    time_str=prediction.window_start.strftime("%H:%M"),
                    risk_level=prediction.risk_level,
                )
                log.info(f"Telegram alert sent to {tg_sub.chat_id}")
            except Exception as exc:
                log.error(f"Telegram alert failed for {tg_sub.chat_id}: {exc}")


@celery_app.task(name="app.tasks.telegram_alert.send_confirmed_outage_telegram", bind=True, max_retries=3)
def send_confirmed_outage_telegram(self, h3_index: str):
    """Instant Telegram alert when outage is confirmed by 3 users."""
    try:
        asyncio.run(_send_confirmed(h3_index))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


async def _send_confirmed(h3_index: str):
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.notifications import TelegramSubscription
    from app.services.telegram_service import send_confirmed_alert

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramSubscription).where(
                TelegramSubscription.h3_index == h3_index,
                TelegramSubscription.is_active == True,
            )
        )
        for sub in result.scalars().all():
            try:
                await send_confirmed_alert(sub.chat_id)
            except Exception as exc:
                log.error(f"Telegram confirmed alert failed for {sub.chat_id}: {exc}")
