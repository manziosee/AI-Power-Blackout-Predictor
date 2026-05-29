"""Poll OpenWeatherMap for every tracked H3 cell and store weather snapshots."""
import asyncio
import logging
import os

import h3
import httpx
import sqlalchemy as sa
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

OWM_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:password@localhost:5432/blackout_predictor")

engine = sa.create_engine(DATABASE_URL)


async def fetch_weather(lat: float, lng: float, session: httpx.AsyncClient) -> dict | None:
    try:
        r = await session.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lng, "appid": OWM_KEY, "units": "metric"},
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning(f"OWM fetch failed ({lat},{lng}): {exc}")
        return None


async def collect():
    with engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT h3_index, center_lat, center_lng FROM h3_cells LIMIT 5000")).fetchall()

    async with httpx.AsyncClient(timeout=10) as client:
        for row in rows:
            data = await fetch_weather(row.center_lat, row.center_lng, client)
            if not data:
                continue
            with engine.begin() as conn:
                conn.execute(
                    sa.text("""
                        INSERT INTO weather_snapshots (h3_index, temperature_c, rainfall_mm, wind_speed_ms, humidity_pct, weather_code)
                        VALUES (:h3, :temp, :rain, :wind, :hum, :code)
                    """),
                    {
                        "h3": row.h3_index,
                        "temp": data["main"]["temp"],
                        "rain": data.get("rain", {}).get("1h", 0.0),
                        "wind": data["wind"]["speed"],
                        "hum": data["main"]["humidity"],
                        "code": data["weather"][0]["id"] if data.get("weather") else None,
                    },
                )
            await asyncio.sleep(0.1)   # respect OWM rate limit


if __name__ == "__main__":
    asyncio.run(collect())
