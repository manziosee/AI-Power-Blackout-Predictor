import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.predict.run_all_predictions")
def run_all_predictions():
    asyncio.run(_run_predictions())


async def _run_predictions():
    from app.core.database import AsyncSessionLocal
    from app.models.neighborhood import H3Cell
    from app.models.prediction import Prediction
    from app.models.weather import WeatherSnapshot
    from app.services.outage_service import classify_risk
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        cells_result = await db.execute(select(H3Cell).limit(10000))
        cells = cells_result.scalars().all()

        now = datetime.now(timezone.utc)
        window_start = now
        window_end = now + timedelta(hours=4)

        for cell in cells:
            try:
                weather_result = await db.execute(
                    select(WeatherSnapshot)
                    .where(WeatherSnapshot.h3_index == cell.h3_index)
                    .order_by(WeatherSnapshot.recorded_at.desc())
                    .limit(1)
                )
                latest_weather = weather_result.scalar_one_or_none()

                # Placeholder probability — ML engine will override via batch endpoint
                probability = 0.10
                if latest_weather:
                    rain_factor = min((latest_weather.rainfall_mm or 0) / 50.0, 1.0) * 0.4
                    wind_factor = min((latest_weather.wind_speed_ms or 0) / 20.0, 1.0) * 0.3
                    probability = round(rain_factor + wind_factor, 4)

                prediction = Prediction(
                    h3_index=cell.h3_index,
                    window_start=window_start,
                    window_end=window_end,
                    probability=probability,
                    confidence=0.60,
                    risk_level=classify_risk(probability),
                    model_version="v0.1-rule-based",
                    region_model=_resolve_region(cell.country_code),
                )
                db.add(prediction)
            except Exception as exc:
                logger.error(f"Prediction failed for {cell.h3_index}: {exc}")

        await db.commit()


def _resolve_region(country_code: str | None) -> str:
    mapping = {
        "RW": "africa_east", "KE": "africa_east", "UG": "africa_east", "TZ": "africa_east",
        "NG": "africa_west", "GH": "africa_west", "SN": "africa_west",
        "FR": "europe_central", "DE": "europe_central", "GB": "europe_central",
        "US": "north_america_east", "CA": "north_america_east",
        "BR": "latin_america", "CO": "latin_america",
        "IN": "asia_south", "PK": "asia_south",
    }
    return mapping.get(country_code or "", "global")
