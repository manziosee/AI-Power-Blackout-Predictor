import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

REGION_COORDS = {
    "africa_east": [(-1.95, 30.06), (-1.28, 36.82), (0.34, 32.58)],   # Kigali, Nairobi, Kampala
    "europe_central": [(48.86, 2.35), (52.52, 13.40), (51.51, -0.13)], # Paris, Berlin, London
    "north_america_east": [(40.71, -74.01), (43.65, -79.38)],           # NYC, Toronto
    "latin_america": [(-23.55, -46.63), (4.71, -74.07)],               # São Paulo, Bogotá
    "asia_south": [(28.61, 77.21), (19.08, 72.88)],                    # Delhi, Mumbai
}


@celery_app.task(name="app.tasks.weather_fetch.fetch_all_regions")
def fetch_all_regions():
    asyncio.run(_fetch_all())


async def _fetch_all():
    from app.core.database import AsyncSessionLocal
    from app.models.weather import WeatherSnapshot
    from app.services.weather_service import fetch_forecast, parse_forecast
    import h3

    async with AsyncSessionLocal() as db:
        for region, coords in REGION_COORDS.items():
            for lat, lng in coords:
                try:
                    raw = await fetch_forecast(lat, lng)
                    items = parse_forecast(raw)
                    h3_index = h3.latlng_to_cell(lat, lng, 8)
                    for item in items:
                        snap = WeatherSnapshot(
                            h3_index=h3_index,
                            temperature_c=item["temperature_c"],
                            rainfall_mm=item["rainfall_mm"],
                            wind_speed_ms=item["wind_speed_ms"],
                            humidity_pct=item["humidity_pct"],
                            weather_code=item["weather_code"],
                            is_forecast=True,
                        )
                        db.add(snap)
                except Exception as exc:
                    logger.error(f"Weather fetch failed for {lat},{lng}: {exc}")
        await db.commit()
