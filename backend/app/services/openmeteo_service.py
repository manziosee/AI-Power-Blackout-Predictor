"""Open-Meteo weather service — free, no API key required."""
import httpx

_BASE_URL = "https://api.open-meteo.com/v1/forecast"

_HOURLY_VARS = (
    "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,"
    "wind_gusts_10m,cloud_cover,weather_code"
)


async def fetch_forecast(lat: float, lng: float, hours: int = 24) -> dict:
    """Fetch hourly forecast from Open-Meteo (no API key needed)."""
    params: dict = {
        "latitude": lat,
        "longitude": lng,
        "hourly": _HOURLY_VARS,
        "forecast_days": max(1, hours // 24 + 1),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


def parse_current(raw: dict) -> dict:
    """Extract the current-hour values from an Open-Meteo forecast response."""
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {}
    return {
        "time": times[0],
        "temperature_c": (hourly.get("temperature_2m") or [None])[0],
        "humidity_pct": (hourly.get("relative_humidity_2m") or [None])[0],
        "precipitation_mm": (hourly.get("precipitation") or [0])[0],
        "wind_speed_ms": (hourly.get("wind_speed_10m") or [None])[0],
        "wind_gusts_ms": (hourly.get("wind_gusts_10m") or [None])[0],
        "cloud_cover_pct": (hourly.get("cloud_cover") or [None])[0],
        "weather_code": (hourly.get("weather_code") or [None])[0],
    }


def parse_hourly(raw: dict) -> list[dict]:
    """Return a list of per-hour dicts from an Open-Meteo forecast response."""
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    results = []
    for i, t in enumerate(times):
        results.append({
            "time": t,
            "temperature_c": _idx(hourly.get("temperature_2m"), i),
            "humidity_pct": _idx(hourly.get("relative_humidity_2m"), i),
            "precipitation_mm": _idx(hourly.get("precipitation"), i),
            "wind_speed_ms": _idx(hourly.get("wind_speed_10m"), i),
            "wind_gusts_ms": _idx(hourly.get("wind_gusts_10m"), i),
            "cloud_cover_pct": _idx(hourly.get("cloud_cover"), i),
            "weather_code": _idx(hourly.get("weather_code"), i),
        })
    return results


def _idx(lst: list | None, i: int):
    if lst and i < len(lst):
        return lst[i]
    return None
