"""
Weather fetch Celery task.

Runs every hour. Fetches OWM current weather for every H3 cell that has:
  - at least one active AlertSubscription, OR
  - a recent outage report (last 30 days), OR
  - a user location

OWM free tier: 60 calls/min → throttle to 55/min to stay safe.
Cells with no OWM data (e.g. ocean cells) are skipped silently.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5/weather"
CALLS_PER_MINUTE = 55   # stay under OWM free tier limit
SLEEP_BETWEEN_CALLS = 60.0 / CALLS_PER_MINUTE   # ~1.09 s


@celery_app.task(name="app.tasks.weather_fetch.fetch_all_regions")
def fetch_all_regions():
    asyncio.run(_fetch())


async def _fetch():
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription
    from app.models.neighborhood import H3Cell
    from app.models.outage import OutageReport
    from app.models.user import UserLocation
    from app.models.weather import WeatherSnapshot
    from sqlalchemy import select, union

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)

        # H3 cells with subscriptions
        sub_q = select(AlertSubscription.h3_index).where(AlertSubscription.is_active == True).distinct()
        # H3 cells with recent outages
        out_q = select(OutageReport.h3_index).where(OutageReport.reported_at >= month_ago).distinct()
        # H3 cells with user locations
        loc_q = select(UserLocation.h3_index).where(UserLocation.is_active == True).distinct()

        active_idx_res = await db.execute(union(sub_q, out_q, loc_q))
        active_h3_set = {row[0] for row in active_idx_res.all()}

        if not active_h3_set:
            logger.info("No active H3 cells — skipping weather fetch")
            return

        # Fetch H3Cell coords for active cells
        cells_res = await db.execute(
            select(H3Cell).where(H3Cell.h3_index.in_(active_h3_set))
        )
        cells = cells_res.scalars().all()
        logger.info("Fetching weather for %d active H3 cells", len(cells))

        async with httpx.AsyncClient(timeout=10) as client:
            for cell in cells:
                if not cell.center_lat or not cell.center_lng:
                    continue
                try:
                    resp = await client.get(OWM_BASE, params={
                        "lat":   cell.center_lat,
                        "lon":   cell.center_lng,
                        "appid": settings.OPENWEATHERMAP_API_KEY,
                        "units": "metric",
                    })
                    if resp.status_code == 401:
                        logger.error("OWM API key invalid — aborting weather fetch")
                        return
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    snap = WeatherSnapshot(
                        h3_index=cell.h3_index,
                        temperature_c=data["main"]["temp"],
                        rainfall_mm=data.get("rain", {}).get("1h", 0.0),
                        wind_speed_ms=data["wind"]["speed"],
                        humidity_pct=data["main"]["humidity"],
                        weather_code=data["weather"][0]["id"] if data.get("weather") else None,
                        is_forecast=False,
                    )
                    db.add(snap)
                except Exception as exc:
                    logger.warning("OWM fetch failed for %s: %s", cell.h3_index, exc)

                await asyncio.sleep(SLEEP_BETWEEN_CALLS)

        await db.commit()
        logger.info("Weather fetch complete for %d cells", len(cells))
