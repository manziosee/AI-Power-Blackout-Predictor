"""Celery task — send WhatsApp alerts when outage probability crosses threshold."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.whatsapp_alert.dispatch_whatsapp_alerts")
def dispatch_whatsapp_alerts():
    asyncio.run(_dispatch())


async def _dispatch():
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription
    from app.models.notifications import WhatsAppSubscription
    from app.models.prediction import Prediction
    from app.models.user import User
    from app.services.whatsapp_service import (
        build_outage_warning_components,
        send_whatsapp_message,
    )

    async with AsyncSessionLocal() as db:
        since = datetime.now(timezone.utc) - timedelta(hours=4)

        # Get all active WhatsApp subscribers
        wa_subs = await db.execute(
            select(WhatsAppSubscription).where(WhatsAppSubscription.is_active)
        )
        wa_map = {s.user_id: s for s in wa_subs.scalars().all()}

        if not wa_map:
            return

        # Get alert subscriptions for those users that include "whatsapp" channel
        alert_subs = await db.execute(
            select(AlertSubscription).where(
                AlertSubscription.user_id.in_(wa_map.keys()),
                AlertSubscription.is_active,
            )
        )

        for alert_sub in alert_subs.scalars().all():
            wa_sub = wa_map.get(alert_sub.user_id)
            if not wa_sub:
                continue

            channels = alert_sub.channels or []
            if "whatsapp" not in channels:
                continue

            pred_result = await db.execute(
                select(Prediction).where(
                    Prediction.h3_index == alert_sub.h3_index,
                    Prediction.predicted_at >= since,
                    Prediction.probability >= alert_sub.threshold_probability,
                ).order_by(Prediction.predicted_at.desc()).limit(1)
            )
            prediction = pred_result.scalar_one_or_none()
            if not prediction:
                continue

            user_result = await db.execute(select(User).where(User.id == alert_sub.user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            time_str = prediction.window_start.strftime("%H:%M")
            probability = int(prediction.probability * 100)

            try:
                await send_whatsapp_message(
                    to=wa_sub.phone,
                    template_key="outage_warning",
                    language=user.language,
                    components=build_outage_warning_components(probability, time_str),
                )
                log.info(f"WhatsApp alert sent to {wa_sub.phone} for {alert_sub.h3_index}")
            except Exception as exc:
                log.error(f"WhatsApp alert failed for {wa_sub.phone}: {exc}")


@celery_app.task(name="app.tasks.whatsapp_alert.send_confirmed_outage_whatsapp", bind=True, max_retries=3)
def send_confirmed_outage_whatsapp(self, h3_index: str):
    """Instant WhatsApp alert when an outage is confirmed by 3 users."""
    try:
        asyncio.run(_send_confirmed(h3_index))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


async def _send_confirmed(h3_index: str):
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription
    from app.models.notifications import WhatsAppSubscription
    from app.models.user import User
    from app.services.whatsapp_service import send_whatsapp_message

    async with AsyncSessionLocal() as db:
        alert_subs = await db.execute(
            select(AlertSubscription).where(
                AlertSubscription.h3_index == h3_index,
                AlertSubscription.is_active,
            )
        )

        for alert_sub in alert_subs.scalars().all():
            if "whatsapp" not in (alert_sub.channels or []):
                continue

            wa_result = await db.execute(
                select(WhatsAppSubscription).where(
                    WhatsAppSubscription.user_id == alert_sub.user_id,
                    WhatsAppSubscription.is_active,
                )
            )
            wa_sub = wa_result.scalar_one_or_none()
            if not wa_sub:
                continue

            user_result = await db.execute(select(User).where(User.id == alert_sub.user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            try:
                await send_whatsapp_message(
                    to=wa_sub.phone,
                    template_key="outage_confirmed",
                    language=user.language,
                )
            except Exception as exc:
                log.error(f"WhatsApp confirmed alert failed for {wa_sub.phone}: {exc}")
