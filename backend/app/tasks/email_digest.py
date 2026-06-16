"""Celery task — send weekly outage digest every Monday at 8:00 AM UTC."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.email_digest.send_weekly_digests")
def send_weekly_digests():
    asyncio.run(_send_all())


async def _send_all():
    from sqlalchemy import select

    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.neighborhood import H3Cell
    from app.models.notifications import EmailSubscription
    from app.models.outage import OutageReport
    from app.models.prediction import Prediction
    from app.services.email_service import send_weekly_digest_email

    async with AsyncSessionLocal() as db:
        subs_result = await db.execute(
            select(EmailSubscription).where(EmailSubscription.is_active)
        )
        subscriptions = subs_result.scalars().all()

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        week_end = now + timedelta(days=7)

        for sub in subscriptions:
            try:
                # ── Outages last 7 days ───────────────────────────────────────
                outage_result = await db.execute(
                    select(OutageReport).where(
                        OutageReport.h3_index == sub.h3_index,
                        OutageReport.reported_at >= week_ago,
                        OutageReport.verified,
                    )
                )
                outages = outage_result.scalars().all()
                outages_last_week = len(outages)

                # Daily breakdown (Mon–Sun)
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_counts = [0] * 7
                for o in outages:
                    day_counts[o.reported_at.weekday()] += 1
                outages_by_day = [{"name": day_names[i], "count": day_counts[i]} for i in range(7)]

                # ── Predictions this week ─────────────────────────────────────
                pred_result = await db.execute(
                    select(Prediction).where(
                        Prediction.h3_index == sub.h3_index,
                        Prediction.window_start >= now,
                        Prediction.window_end <= week_end,
                        Prediction.probability >= 0.50,
                    ).order_by(Prediction.probability.desc())
                )
                predictions = pred_result.scalars().all()
                predictions_this_week = len(predictions)

                high_risk_windows = [
                    {
                        "label": p.window_start.strftime("%a %d %b, %H:%M"),
                        "probability": int(p.probability * 100),
                        "risk_level": p.risk_level,
                    }
                    for p in predictions[:5]   # top 5 only
                ]

                # ── Area name ─────────────────────────────────────────────────
                cell_result = await db.execute(
                    select(H3Cell).where(H3Cell.h3_index == sub.h3_index)
                )
                cell = cell_result.scalar_one_or_none()
                area = cell.city if cell and cell.city else sub.h3_index[:10] + "..."

                unsubscribe_url = f"{settings.APP_URL}/api/v1/email/unsubscribe/{sub.id}"

                ok = send_weekly_digest_email(
                    to=sub.email,
                    area=area,
                    outages_last_week=outages_last_week,
                    outages_by_day=outages_by_day,
                    predictions_this_week=predictions_this_week,
                    high_risk_windows=high_risk_windows,
                    unsubscribe_url=unsubscribe_url,
                )

                if ok:
                    sub.last_digest_at = now
                    log.info(f"Weekly digest sent to {sub.email}")

            except Exception as exc:
                log.error(f"Digest failed for {sub.email}: {exc}")

        await db.commit()
