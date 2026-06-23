"""Celery task — retry failed SMS alerts with exponential backoff."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_MINUTES = [1, 2, 4, 8]


@celery_app.task(name="app.tasks.sms_retry.retry_failed_sms", queue="sms")
def retry_failed_sms():
    asyncio.run(_retry())


async def _retry():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.alert import SmsAlert
    from app.models.user import User
    from app.services.alert_service import send_sms_alert

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        due = (await db.execute(
            select(SmsAlert).where(
                SmsAlert.status == "failed",
                SmsAlert.next_retry_at <= now,
                SmsAlert.retry_count < _MAX_RETRIES,
            ).limit(100)
        )).scalars().all()

        for sms in due:
            if not sms.template_key:
                sms.status = "dropped"
                continue

            user = (await db.execute(select(User).where(User.id == sms.user_id))).scalar_one_or_none()
            if not user:
                sms.status = "dropped"
                continue

            try:
                await send_sms_alert(
                    phone=sms.phone,
                    country_code=user.country_code,
                    language=sms.language,
                    template_key=sms.template_key,
                    template_vars=sms.template_vars or {},
                )
                sms.status = "sent"
                sms.error_message = None
                logger.info(f"SMS retry succeeded for alert {sms.id}")
            except Exception as exc:
                next_count = sms.retry_count + 1
                delay = _BACKOFF_MINUTES[min(next_count, len(_BACKOFF_MINUTES) - 1)]
                sms.retry_count = next_count
                sms.error_message = str(exc)[:500]
                if next_count >= _MAX_RETRIES:
                    sms.status = "dead"
                    sms.next_retry_at = None
                    logger.warning(f"SMS alert {sms.id} moved to dead letter after {next_count} retries")
                else:
                    sms.next_retry_at = now + timedelta(minutes=delay)
                    logger.warning(f"SMS retry {next_count}/{_MAX_RETRIES} failed for alert {sms.id}: {exc}")

        await db.commit()
