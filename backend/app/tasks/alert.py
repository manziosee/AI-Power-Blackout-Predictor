import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.alert.dispatch_alerts")
def dispatch_alerts():
    asyncio.run(_dispatch())


async def _dispatch():
    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription, SmsAlert
    from app.models.prediction import Prediction
    from app.models.user import User
    from app.services.alert_service import send_sms_alert
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        since = datetime.now(timezone.utc) - timedelta(hours=4)

        subs_result = await db.execute(
            select(AlertSubscription).where(AlertSubscription.is_active == True)
        )
        subscriptions = subs_result.scalars().all()

        for sub in subscriptions:
            pred_result = await db.execute(
                select(Prediction)
                .where(
                    Prediction.h3_index == sub.h3_index,
                    Prediction.predicted_at >= since,
                    Prediction.probability >= sub.threshold_probability,
                )
                .order_by(Prediction.predicted_at.desc())
                .limit(1)
            )
            prediction = pred_result.scalar_one_or_none()
            if not prediction:
                continue

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
                        template_key="outage_warning",
                        template_vars={
                            "prob": f"{int(prediction.probability * 100)}%",
                            "time": prediction.window_start.strftime("%H:%M"),
                        },
                    )
                    sms_log = SmsAlert(
                        user_id=user.id,
                        phone=user.phone,
                        message="alert_sent",
                        language=user.language,
                        prediction_id=prediction.id,
                        status="sent",
                    )
                    db.add(sms_log)
                except Exception as exc:
                    logger.error(f"SMS alert failed for user {user.id}: {exc}")

        await db.commit()


def _is_quiet_hours(sub: "AlertSubscription") -> bool:
    if not sub.quiet_hours_start or not sub.quiet_hours_end:
        return False
    now_time = datetime.now(timezone.utc).time()
    return sub.quiet_hours_start <= now_time <= sub.quiet_hours_end
