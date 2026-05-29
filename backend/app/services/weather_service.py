import httpx

from app.core.config import settings


async def fetch_forecast(lat: float, lng: float) -> dict:
    """Fetch 24h weather forecast from OpenWeatherMap for a coordinate."""
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lng,
        "appid": settings.OPENWEATHERMAP_API_KEY,
        "units": "metric",
        "cnt": 8,   # 8 × 3h slots = 24h
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def parse_forecast(raw: dict) -> list[dict]:
    """Extract relevant weather fields from OWM forecast response."""
    results = []
    for item in raw.get("list", []):
        results.append({
            "dt": item["dt"],
            "temperature_c": item["main"]["temp"],
            "humidity_pct": item["main"]["humidity"],
            "wind_speed_ms": item["wind"]["speed"],
            "rainfall_mm": item.get("rain", {}).get("3h", 0.0),
            "weather_code": item["weather"][0]["id"] if item.get("weather") else None,
        })
    return results
