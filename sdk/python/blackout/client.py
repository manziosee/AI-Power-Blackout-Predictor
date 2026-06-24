"""Async HTTP client for the AI Power Blackout Predictor API."""
from __future__ import annotations

from typing import Any

import httpx

from .exceptions import (
    BlackoutAPIError,
    BlackoutAuthError,
    BlackoutNotFoundError,
    BlackoutRateLimitError,
)


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = ""
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    if response.status_code == 401 or response.status_code == 403:
        raise BlackoutAuthError(response.status_code, detail)
    if response.status_code == 404:
        raise BlackoutNotFoundError(response.status_code, detail)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise BlackoutRateLimitError(int(retry_after) if retry_after else None)
    raise BlackoutAPIError(response.status_code, detail)


class BlackoutClient:
    """Async client for the AI Power Blackout Predictor Public API.

    Usage::

        async with BlackoutClient(api_key="your-key") as client:
            risk = await client.get_prediction("8a3f00000000000")
            print(risk)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.blackoutpredictor.com",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-API-Key": api_key, "User-Agent": "blackout-python-sdk/0.1.0"},
            timeout=timeout,
        )

    async def __aenter__(self) -> "BlackoutClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._client.aclose()

    async def close(self) -> None:
        await self._client.aclose()

    # ── Predictions ──────────────────────────────────────────────────────────

    async def get_prediction(self, h3_index: str, limit: int = 6) -> list[dict]:
        """Latest ML predictions for an H3 cell."""
        resp = await self._client.get(
            f"/api/v1/predictions/cell/{h3_index}",
            params={"limit": limit},
        )
        _raise_for_status(resp)
        return resp.json()

    async def explain_prediction(self, h3_index: str) -> dict:
        """Feature importance breakdown for the latest prediction in a cell."""
        resp = await self._client.get(f"/api/v1/predictions/cell/{h3_index}/explain")
        _raise_for_status(resp)
        return resp.json()

    async def get_heatmap(self, country_code: str) -> list[dict]:
        """Risk heatmap (all H3 cells) for a country."""
        resp = await self._client.get(
            "/api/v1/predictions/heatmap",
            params={"country_code": country_code},
        )
        _raise_for_status(resp)
        return resp.json()

    # ── Outages ───────────────────────────────────────────────────────────────

    async def get_outages_geojson(
        self,
        country_code: str | None = None,
        hours: int = 24,
        lat_min: float | None = None,
        lat_max: float | None = None,
        lng_min: float | None = None,
        lng_max: float | None = None,
    ) -> dict:
        """GeoJSON FeatureCollection of active outage reports."""
        params: dict[str, Any] = {"hours": hours}
        if country_code:
            params["country_code"] = country_code
        if lat_min is not None:
            params["lat_min"] = lat_min
        if lat_max is not None:
            params["lat_max"] = lat_max
        if lng_min is not None:
            params["lng_min"] = lng_min
        if lng_max is not None:
            params["lng_max"] = lng_max
        resp = await self._client.get("/api/v1/outages/map/geojson", params=params)
        _raise_for_status(resp)
        return resp.json()

    async def get_cell_outages(self, h3_index: str) -> list[dict]:
        """Recent outage reports for an H3 cell."""
        resp = await self._client.get(f"/api/v1/outages/cell/{h3_index}")
        _raise_for_status(resp)
        return resp.json()

    # ── Neighborhoods ─────────────────────────────────────────────────────────

    async def get_neighbor_stats(self, h3_index: str) -> dict:
        """Social-proof stats for a cell and its neighbors."""
        resp = await self._client.get(f"/api/v1/outages/cell/{h3_index}/neighbor-stats")
        _raise_for_status(resp)
        return resp.json()

    # ── Health ────────────────────────────────────────────────────────────────

    async def health(self) -> dict:
        """Check API health."""
        resp = await self._client.get("/health")
        _raise_for_status(resp)
        return resp.json()
