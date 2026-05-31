from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "blackout_predictor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.predict",
        "app.tasks.alert",
        "app.tasks.weather_fetch",
        "app.tasks.instant_alert",
        "app.tasks.whatsapp_alert",
        "app.tasks.telegram_alert",
        "app.tasks.email_digest",
        "app.tasks.analytics_refresh",
        "app.tasks.community_tasks",
    ],
)

celery_app.conf.beat_schedule = {
    "fetch-weather-hourly": {
        "task": "app.tasks.weather_fetch.fetch_all_regions",
        "schedule": crontab(minute=0),
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
        "schedule": crontab(minute=0, hour=3),   # 03:00 UTC daily
    },
    "refresh-rankings-daily": {
        "task": "app.tasks.analytics_refresh.refresh_rankings",
        "schedule": crontab(minute=30, hour=3),
    },
    "reset-weekly-points": {
        "task": "app.tasks.community_tasks.reset_weekly_points",
        "schedule": crontab(minute=1, hour=0, day_of_week="monday"),  # Monday 00:01 UTC
    },
    "expire-community-notes": {
        "task": "app.tasks.community_tasks.expire_community_notes",
        "schedule": crontab(minute=0),   # every hour
    },
}

celery_app.conf.timezone = "UTC"
