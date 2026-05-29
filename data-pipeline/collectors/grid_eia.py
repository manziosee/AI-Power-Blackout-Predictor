"""Fetch US grid data from the EIA Open Data API."""
import logging
import os

import httpx

log = logging.getLogger(__name__)

EIA_KEY = os.getenv("EIA_API_KEY", "")
EIA_BASE = "https://api.eia.gov/v2/electricity/rto/region-data/data/"


async def fetch_demand(region: str = "US48") -> list[dict]:
    """Return recent electricity demand for a US region."""
    params = {
        "api_key": EIA_KEY,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": region,
        "facets[type][]": "D",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 48,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(EIA_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", {}).get("data", [])
        except Exception as exc:
            log.warning(f"EIA fetch failed: {exc}")
            return []


if __name__ == "__main__":
    import asyncio
    rows = asyncio.run(fetch_demand("US48"))
    print(f"Fetched {len(rows)} EIA records")
