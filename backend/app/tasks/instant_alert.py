"""Fire SMS + push alerts immediately when an outage is confirmed by 3+ users."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.instant_alert.confirmed_outage_alert", bind=True, max_retries=3)
def confirmed_outage_alert(self, h3_index: str, report_id: str):
    try:
        asyncio.run(_fire_alerts(h3_index, report_id))
    except Exception as exc:
        logger.error(f"Instant alert failed for {h3_index}: {exc}")
        raise self.retry(exc=exc, countdown=30)


async def _fire_alerts(h3_index: str, report_id: str):
    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription, SmsAlert
    from app.models.user import User
    from app.services.alert_service import send_sms_alert, send_push_notification
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        subs_result = await db.execute(
            select(AlertSubscription).where(
                AlertSubscription.h3_index == h3_index,
                AlertSubscription.is_active,
            )
        )
        subscriptions = subs_result.scalars().all()

        if not subscriptions:
            logger.info(f"No subscribers for confirmed outage in {h3_index}")
            return

        for sub in subscriptions:
            user_result = await db.execute(select(User).where(User.id == sub.user_id))
            user = user_result.scalar_one_or_none()
            if not user or not user.is_active:
                continue

            if _is_quiet_hours(sub):
                continue

            if "sms" in (sub.channels or []):
                try:
                    await send_sms_alert(
                        phone=user.phone,
                        country_code=user.country_code,
                        language=user.language,
                        template_key="outage_confirmed",
                        template_vars={},
                    )
                    db.add(SmsAlert(
                        user_id=user.id,
                        phone=user.phone,
                        message="outage_confirmed",
                        language=user.language,
                        status="sent",
                        provider="instant_trigger",
                    ))
                    logger.info(f"Instant SMS sent to {user.phone} for {h3_index}")
                except Exception as exc:
                    logger.error(f"SMS failed for {user.phone}: {exc}")

            if "push" in (sub.channels or []):
                try:
                    await send_push_notification(
                        user_id=str(user.id),
                        title="Outage Confirmed",
                        body="Power outage confirmed in your area by multiple users.",
                    )
                except Exception as exc:
                    logger.error(f"Push failed for {user.id}: {exc}")

        await db.commit()


def _is_quiet_hours(sub) -> bool:
    if not sub.quiet_hours_start or not sub.quiet_hours_end:
        return False
    from datetime import datetime, timezone
    now_time = datetime.now(timezone.utc).time()
    return sub.quiet_hours_start <= now_time <= sub.quiet_hours_end
