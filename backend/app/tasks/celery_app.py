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
    ],
)

celery_app.conf.beat_schedule = {
    "fetch-weather-hourly": {
        "task": "app.tasks.weather_fetch.fetch_all_regions",
        "schedule": crontab(minute=0),   # every hour
    },
    "run-predictions-every-4h": {
        "task": "app.tasks.predict.run_all_predictions",
        "schedule": crontab(minute=5, hour="*/4"),
    },
    "check-and-send-alerts": {
        "task": "app.tasks.alert.dispatch_alerts",
        "schedule": crontab(minute=15, hour="*/4"),
    },
}

celery_app.conf.timezone = "UTC"
