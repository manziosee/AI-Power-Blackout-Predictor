"""
Open-Meteo weather sync Celery task.

Runs every 3 hours. Fetches current weather from Open-Meteo (free, no API key)
for every active H3 cell and persists it as a WeatherSnapshot with
forecast_source="open-meteo".

Open-Meteo has no hard rate limit on the free tier — we still add a small
sleep between calls to be a polite client.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_SLEEP_BETWEEN_CALLS = 0.2   # seconds — gentle pacing, no strict rate limit


@celery_app.task(name="app.tasks.weather_sync.sync_all_cells")
def sync_all_cells() -> None:
    asyncio.run(_sync())


async def _sync() -> None:
    from sqlalchemy import select, union

    from app.core.database import AsyncSessionLocal
    from app.models.alert import AlertSubscription
    from app.models.neighborhood import H3Cell
    from app.models.outage import OutageReport
    from app.models.user import UserLocation
    from app.models.weather import WeatherSnapshot
    from app.services.openmeteo_service import fetch_forecast, parse_current

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)

        # Collect active H3 indexes from three sources
        sub_q = select(AlertSubscription.h3_index).where(AlertSubscription.is_active).distinct()
        out_q = select(OutageReport.h3_index).where(OutageReport.reported_at >= month_ago).distinct()
        loc_q = select(UserLocation.h3_index).where(UserLocation.is_active).distinct()

        result = await db.execute(union(sub_q, out_q, loc_q))
        active_h3s = {row[0] for row in result.all()}

        if not active_h3s:
            logger.info("weather_sync: no active H3 cells — skipping")
            return

        # Prefer DB-stored coordinates; fall back to h3 library
        cells_res = await db.execute(select(H3Cell).where(H3Cell.h3_index.in_(active_h3s)))
        db_cells: dict[str, tuple[float, float]] = {
            c.h3_index: (c.center_lat, c.center_lng)
            for c in cells_res.scalars().all()
            if c.center_lat and c.center_lng
        }

        # For any H3 index not in the DB table, derive coords from the h3 library
        try:
            import h3 as h3lib
            for idx in active_h3s - db_cells.keys():
                lat, lng = h3lib.cell_to_latlng(idx)
                db_cells[idx] = (lat, lng)
        except Exception:
            pass  # h3 library not available; only DB cells will be synced

        logger.info("weather_sync: fetching Open-Meteo data for %d cells", len(db_cells))
        saved = 0

        for h3_index, (lat, lng) in db_cells.items():
            try:
                raw = await fetch_forecast(lat, lng, hours=1)
                current = parse_current(raw)
                if not current:
                    continue

                snap = WeatherSnapshot(
                    h3_index=h3_index,
                    temperature_c=current.get("temperature_c"),
                    rainfall_mm=current.get("precipitation_mm"),
                    wind_speed_ms=current.get("wind_speed_ms"),
                    humidity_pct=int(current["humidity_pct"]) if current.get("humidity_pct") is not None else None,
                    weather_code=current.get("weather_code"),
                    is_forecast=False,
                    forecast_source="open-meteo",
                )
                db.add(snap)
                saved += 1
            except Exception as exc:
                logger.warning("weather_sync: failed for %s: %s", h3_index, exc)

            await asyncio.sleep(_SLEEP_BETWEEN_CALLS)

        await db.commit()
        logger.info("weather_sync: saved %d snapshots", saved)
