from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.services.openmeteo_service import fetch_forecast, parse_current, parse_hourly

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current/{h3_index}")
async def get_current_weather(
    h3_index: str,
    _: User = Depends(get_current_user),
) -> dict:
    """Fetch current weather for an H3 cell via Open-Meteo (no API key required)."""
    try:
        import h3 as h3lib
        lat, lng = h3lib.cell_to_latlng(h3_index)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid H3 index: {h3_index}")

    try:
        raw = await fetch_forecast(lat, lng, hours=1)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {exc}")

    current = parse_current(raw)
    return {"h3_index": h3_index, "latitude": lat, "longitude": lng, "current": current}


@router.get("/forecast/{h3_index}")
async def get_weather_forecast(
    h3_index: str,
    hours: int = 24,
    _: User = Depends(get_current_user),
) -> dict:
    """Fetch hourly weather forecast for an H3 cell (up to 48h)."""
    hours = min(hours, 48)
    try:
        import h3 as h3lib
        lat, lng = h3lib.cell_to_latlng(h3_index)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid H3 index: {h3_index}")

    try:
        raw = await fetch_forecast(lat, lng, hours=hours)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {exc}")

    hourly = parse_hourly(raw)[:hours]
    return {"h3_index": h3_index, "latitude": lat, "longitude": lng, "hourly": hourly}
