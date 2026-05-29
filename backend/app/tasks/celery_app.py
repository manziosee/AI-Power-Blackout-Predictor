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
        "schedule": crontab(minute=0, hour=8, day_of_week="monday"),   # every Monday 08:00 UTC
    },
}

celery_app.conf.timezone = "UTC"
