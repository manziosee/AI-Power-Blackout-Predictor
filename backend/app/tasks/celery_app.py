from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "blackout_predictor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        # ML queue
        "app.tasks.predict",
        "app.tasks.incident_cluster",
        "app.tasks.maintenance_score",
        # SMS queue
        "app.tasks.alert",
        "app.tasks.instant_alert",
        "app.tasks.whatsapp_alert",
        "app.tasks.telegram_alert",
        "app.tasks.sms_retry",
        "app.tasks.prepaid_prediction_alert",
        "app.tasks.restoration_broadcast",
        # Analytics queue
        "app.tasks.analytics_refresh",
        "app.tasks.weather_fetch",
        "app.tasks.fraud_scan",
        "app.tasks.community_tasks",
        "app.tasks.auto_claim",
        "app.tasks.model_monitor",
        # Default queue
        "app.tasks.email_digest",
        "app.tasks.webhook_dispatch",
        "app.tasks.feedback_followup",
        "app.tasks.resilience_compute",
        "app.tasks.grid_load_fetch",
        "app.tasks.push_alert",
        "app.tasks.weather_sync",
    ],
)

# ── Queue routing — 3 specialised queues + default ───────────────────────────
# Start workers with: celery -A app.tasks.celery_app worker -Q ml -c 2
#                     celery -A app.tasks.celery_app worker -Q sms -c 4
#                     celery -A app.tasks.celery_app worker -Q analytics -c 2
#                     celery -A app.tasks.celery_app worker -Q celery -c 2  (default)
celery_app.conf.task_routes = {
    # ML — CPU-intensive inference
    "app.tasks.predict.*": {"queue": "ml"},
    "app.tasks.incident_cluster.*": {"queue": "ml"},
    "app.tasks.maintenance_score.*": {"queue": "ml"},
    # SMS — low-latency delivery
    "app.tasks.alert.*": {"queue": "sms"},
    "app.tasks.instant_alert.*": {"queue": "sms"},
    "app.tasks.whatsapp_alert.*": {"queue": "sms"},
    "app.tasks.telegram_alert.*": {"queue": "sms"},
    "app.tasks.sms_retry.*": {"queue": "sms"},
    "app.tasks.prepaid_prediction_alert.*": {"queue": "sms"},
    "app.tasks.restoration_broadcast.*": {"queue": "sms"},
    # Analytics — low-priority batch work
    "app.tasks.analytics_refresh.*": {"queue": "analytics"},
    "app.tasks.weather_fetch.*": {"queue": "analytics"},
    "app.tasks.weather_sync.*": {"queue": "analytics"},
    "app.tasks.fraud_scan.*": {"queue": "analytics"},
    "app.tasks.community_tasks.*": {"queue": "analytics"},
    "app.tasks.auto_claim.*": {"queue": "analytics"},
    "app.tasks.model_monitor.*": {"queue": "analytics"},
}

celery_app.conf.beat_schedule = {
    "fetch-weather-hourly": {
        "task": "app.tasks.weather_fetch.fetch_all_regions",
        "schedule": crontab(minute=0),
    },
    "sync-openmeteo-every-3h": {
        "task": "app.tasks.weather_sync.sync_all_cells",
        "schedule": crontab(minute=30, hour="*/3"),
    },
    "run-predictions-every-4h": {
        "task": "app.tasks.predict.run_all_predictions",
        "schedule": crontab(minute=5, hour="*/4"),
    },
    "check-and-send-sms-alerts": {
        "task": "app.tasks.alert.dispatch_alerts",
        "schedule": crontab(minute=15, hour="*/4"),
    },
    "check-and-send-whatsapp-alerts": {
        "task": "app.tasks.whatsapp_alert.dispatch_whatsapp_alerts",
        "schedule": crontab(minute=20, hour="*/4"),
    },
    "check-and-send-telegram-alerts": {
        "task": "app.tasks.telegram_alert.dispatch_telegram_alerts",
        "schedule": crontab(minute=25, hour="*/4"),
    },
    "send-weekly-email-digest": {
        "task": "app.tasks.email_digest.send_weekly_digests",
        "schedule": crontab(minute=0, hour=8, day_of_week="monday"),
    },
    "refresh-accuracy-daily": {
        "task": "app.tasks.analytics_refresh.refresh_all_accuracy",
        "schedule": crontab(minute=0, hour=3),
    },
    "refresh-rankings-daily": {
        "task": "app.tasks.analytics_refresh.refresh_rankings",
        "schedule": crontab(minute=30, hour=3),
    },
    "reset-weekly-points": {
        "task": "app.tasks.community_tasks.reset_weekly_points",
        "schedule": crontab(minute=1, hour=0, day_of_week="monday"),
    },
    "expire-community-notes": {
        "task": "app.tasks.community_tasks.expire_community_notes",
        "schedule": crontab(minute=0),
    },
    "dispatch-prediction-webhooks": {
        "task": "app.tasks.webhook_dispatch.dispatch_prediction_webhooks",
        "schedule": crontab(minute=30, hour="*/4"),
    },
    "fraud-scan-daily": {
        "task": "app.tasks.fraud_scan.run_fraud_scan",
        "schedule": crontab(minute=0, hour=2),
    },
    # New beat tasks
    "retry-failed-sms-every-5m": {
        "task": "app.tasks.sms_retry.retry_failed_sms",
        "schedule": crontab(minute="*/5"),
    },
    "check-model-drift-daily": {
        "task": "app.tasks.model_monitor.check_model_drift",
        "schedule": crontab(minute=45, hour=3),  # after accuracy refresh (03:00+)
    },
    "auto-initiate-insurance-claims-hourly": {
        "task": "app.tasks.auto_claim.auto_initiate_claims_task",
        "schedule": crontab(minute=10, hour="*/1"),
    },
    "prepaid-prediction-alerts-every-30m": {
        "task": "app.tasks.prepaid_prediction_alert.prepaid_prediction_alert_task",
        "schedule": crontab(minute="*/30"),
    },
    "cluster-outage-incidents-every-15m": {
        "task": "app.tasks.incident_cluster.cluster_outages_task",
        "schedule": crontab(minute="*/15"),
    },
}

celery_app.conf.timezone = "UTC"
