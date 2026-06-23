"""Celery task — alert prepaid meter users to top up before predicted outages."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.prepaid_prediction_alert.prepaid_prediction_alert_task")
def prepaid_prediction_alert_task():
    asyncio.run(_run())


async def _run():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.prepaid import PrepaidMeter, PrepaidTopupReminder
    from app.models.prediction import Prediction
    from app.models.user import User
    from app.services.alert_service import send_sms_alert

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        meters = (await db.execute(
            select(PrepaidMeter).where(
                PrepaidMeter.is_active.is_(True),
                PrepaidMeter.last_balance_kwh.isnot(None),
            )
        )).scalars().all()

        for meter in meters:
            if (meter.last_balance_kwh or 0) > meter.low_balance_threshold_kwh:
                continue

            window_end = now + timedelta(hours=meter.alert_before_hours)
            prediction = (await db.execute(
                select(Prediction).where(
                    Prediction.h3_index == meter.h3_index,
                    Prediction.window_start >= now,
                    Prediction.window_start <= window_end,
                    Prediction.probability >= 0.60,
                ).order_by(Prediction.probability.desc()).limit(1)
            )).scalar_one_or_none()
            if not prediction:
                continue

            # Avoid duplicate alerts within alert_before_hours window
            cutoff = now - timedelta(hours=meter.alert_before_hours)
            recent = (await db.execute(
                select(PrepaidTopupReminder).where(
                    PrepaidTopupReminder.meter_id == meter.id,
                    PrepaidTopupReminder.message_sent_at >= cutoff,
                )
            )).scalar_one_or_none()
            if recent:
                continue

            user = (await db.execute(select(User).where(User.id == meter.user_id))).scalar_one_or_none()
            if not user:
                continue

            try:
                await send_sms_alert(
                    phone=user.phone,
                    country_code=user.country_code,
                    language=user.language,
                    template_key="prepaid_topup_warning",
                    template_vars={
                        "balance": f"{meter.last_balance_kwh:.1f}",
                        "threshold": f"{meter.low_balance_threshold_kwh:.1f}",
                        "hours": str(meter.alert_before_hours),
                        "prob": f"{int(prediction.probability * 100)}%",
                    },
                )
                reminder = PrepaidTopupReminder(
                    user_id=meter.user_id,
                    meter_id=meter.id,
                    prediction_id=prediction.id,
                    balance_at_send=meter.last_balance_kwh,
                )
                db.add(reminder)
                logger.info(f"Sent prepaid topup alert to user {meter.user_id}")
            except Exception as exc:
                logger.error(f"Failed prepaid alert for meter {meter.id}: {exc}")

        await db.commit()
