import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_parse_forecast_extracts_fields():
    from app.services.weather_service import parse_forecast

    raw = {
        "list": [
            {
                "dt": 1700000000,
                "main": {"temp": 22.5, "humidity": 65},
                "wind": {"speed": 4.2},
                "rain": {"3h": 2.1},
                "weather": [{"id": 500}],
            }
        ]
    }
    result = parse_forecast(raw)
    assert len(result) == 1
    assert result[0]["temperature_c"] == 22.5
    assert result[0]["humidity_pct"] == 65
    assert result[0]["wind_speed_ms"] == 4.2
    assert result[0]["rainfall_mm"] == 2.1
    assert result[0]["weather_code"] == 500


@pytest.mark.asyncio
async def test_parse_forecast_missing_rain():
    from app.services.weather_service import parse_forecast

    raw = {
        "list": [
            {
                "dt": 1700000000,
                "main": {"temp": 18.0, "humidity": 50},
                "wind": {"speed": 2.0},
                "weather": [{"id": 800}],
            }
        ]
    }
    result = parse_forecast(raw)
    assert result[0]["rainfall_mm"] == 0.0


@pytest.mark.asyncio
async def test_fetch_forecast_calls_owm():
    from unittest.mock import MagicMock
    from app.services.weather_service import fetch_forecast

    mock_response = MagicMock()
    mock_response.json.return_value = {"list": []}

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_forecast(lat=-1.95, lng=30.06)

    assert result == {"list": []}
    mock_http_client.get.assert_called_once()
    params = mock_http_client.get.call_args.kwargs.get("params", {})
    assert "lat" in params
