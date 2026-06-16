from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import SmsAlert
from app.models.fraud import FraudFlag
from app.models.outage import OutageReport
from app.models.prediction import Prediction
from app.models.user import User


async def get_platform_stats(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)

    # User growth
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    new_today = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= now - timedelta(days=1))
    )).scalar_one()
    new_week = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= now - timedelta(days=7))
    )).scalar_one()
    new_month = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= now - timedelta(days=30))
    )).scalar_one()

    # SMS delivery rates (last 30 days)
    sms_base = select(func.count()).select_from(SmsAlert).where(SmsAlert.sent_at >= now - timedelta(days=30))
    sms_total = (await db.execute(sms_base)).scalar_one()
    sms_delivered = (await db.execute(sms_base.where(SmsAlert.status == "delivered"))).scalar_one()
    sms_failed = (await db.execute(sms_base.where(SmsAlert.status == "failed"))).scalar_one()
    sms_queued = (await db.execute(sms_base.where(SmsAlert.status == "queued"))).scalar_one()

    # Outage reports
    reports_today = (await db.execute(
        select(func.count()).select_from(OutageReport).where(OutageReport.reported_at >= now - timedelta(days=1))
    )).scalar_one()
    reports_week = (await db.execute(
        select(func.count()).select_from(OutageReport).where(OutageReport.reported_at >= now - timedelta(days=7))
    )).scalar_one()

    # Predictions
    preds_today = (await db.execute(
        select(func.count()).select_from(Prediction).where(Prediction.created_at >= now - timedelta(days=1))
    )).scalar_one()

    # Fraud
    open_flags = (await db.execute(
        select(func.count()).select_from(FraudFlag).where(FraudFlag.resolved == False)
    )).scalar_one()

    return {
        "users": {
            "total": total_users,
            "new_today": new_today,
            "new_week": new_week,
            "new_month": new_month,
        },
        "sms": {
            "total_30d": sms_total,
            "delivered": sms_delivered,
            "failed": sms_failed,
            "queued": sms_queued,
            "delivery_rate": round(sms_delivered / sms_total * 100, 1) if sms_total else None,
        },
        "outages": {
            "reports_today": reports_today,
            "reports_week": reports_week,
        },
        "predictions": {
            "run_today": preds_today,
        },
        "fraud": {
            "open_flags": open_flags,
        },
    }


async def get_accuracy_by_country(db: AsyncSession) -> list[dict]:
    rows = await db.execute(text("""
        SELECT
            n.country_code,
            COUNT(pa.id)                                    AS regions,
            ROUND(AVG(pa.accuracy)::numeric, 3)             AS avg_accuracy,
            ROUND(AVG(pa.precision)::numeric, 3)            AS avg_precision,
            ROUND(AVG(pa.recall)::numeric, 3)               AS avg_recall,
            ROUND(AVG(pa.f1_score)::numeric, 3)             AS avg_f1,
            SUM(pa.total_predictions)                       AS total_predictions
        FROM prediction_accuracy pa
        JOIN neighborhood_stats n ON n.h3_index = pa.h3_index
        WHERE pa.period_end >= NOW() - INTERVAL '30 days'
          AND n.country_code IS NOT NULL
        GROUP BY n.country_code
        ORDER BY avg_f1 DESC NULLS LAST
    """))
    return [dict(r._mapping) for r in rows]


def get_smpp_connectors() -> list[dict]:
    """
    Returns configured SMPP connectors and their status.
    Reads from the generic Jasmin connector env vars — works for any
    global aggregator (Sinch, Infobip, Vonage, local telco SMPP, etc.).
    """
    import os
    connectors = [
        {
            "id": "default",
            "operator": os.getenv("SMPP_OPERATOR_NAME", "Primary SMPP Aggregator"),
            "country": "ALL",
            "host": os.getenv("SMPP_HOST", ""),
            "configured": bool(os.getenv("SMPP_HOST")),
        },
    ]
    # Surface any additional connectors defined via SMPP2_HOST, SMPP3_HOST, etc.
    for i in range(2, 6):
        host = os.getenv(f"SMPP{i}_HOST", "")
        if host:
            connectors.append({
                "id": f"connector{i}",
                "operator": os.getenv(f"SMPP{i}_OPERATOR_NAME", f"Aggregator {i}"),
                "country": os.getenv(f"SMPP{i}_COUNTRY", "ALL"),
                "host": host,
                "configured": True,
            })
    return connectors


def get_celery_health() -> dict:
    try:
        from app.tasks.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=3.0)
        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        stats = inspector.stats() or {}
        workers = list(stats.keys())
        return {
            "status": "ok" if workers else "no_workers",
            "worker_count": len(workers),
            "workers": workers,
            "active_tasks": sum(len(v) for v in active.values()),
            "scheduled_tasks": sum(len(v) for v in scheduled.values()),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc), "worker_count": 0}
