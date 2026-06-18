"""Grid load integration — ENTSO-E (Europe) and EIA (US)."""
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.grid_load import GridLoadSnapshot

ENTSO_E_URL = "https://web-api.tp.entsoe.eu/api"
EIA_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"


async def fetch_entso_e_load(region: str, db: AsyncSession) -> GridLoadSnapshot | None:
    """Fetch EU grid load from ENTSO-E Transparency Platform."""
    api_key = os.getenv("ENTSO_E_API_KEY", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                ENTSO_E_URL,
                params={
                    "securityToken": api_key,
                    "documentType": "A65",  # actual total load
                    "processType": "A16",
                    "outBiddingZone_Domain": f"10Y{region}-A",
                    "periodStart": datetime.now(timezone.utc).strftime("%Y%m%d%H00"),
                    "periodEnd": datetime.now(timezone.utc).strftime("%Y%m%d%H00"),
                },
            )
        if resp.status_code != 200:
            return None
        # Parse XML — simplified, real implementation would parse full response
        snapshot = GridLoadSnapshot(
            region=region,
            source="entso-e",
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(snapshot)
        await db.flush()
        return snapshot
    except Exception:
        return None


async def fetch_eia_load(region: str, db: AsyncSession) -> GridLoadSnapshot | None:
    """Fetch US grid load from EIA API v2."""
    api_key = os.getenv("EIA_API_KEY", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                EIA_URL,
                params={
                    "api_key": api_key,
                    "frequency": "hourly",
                    "data[0]": "value",
                    "facets[respondent][]": region,
                    "facets[type][]": "D",  # demand
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 1,
                },
            )
        if resp.status_code != 200:
            return None
        data = resp.json().get("response", {}).get("data", [])
        if not data:
            return None
        row = data[0]
        load_mw = float(row.get("value", 0))
        snapshot = GridLoadSnapshot(
            region=region,
            source="eia",
            load_mw=load_mw,
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(snapshot)
        await db.flush()
        return snapshot
    except Exception:
        return None


async def get_latest_load(region: str, db: AsyncSession) -> GridLoadSnapshot | None:
    result = await db.execute(
        select(GridLoadSnapshot)
        .where(GridLoadSnapshot.region == region)
        .order_by(GridLoadSnapshot.recorded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_history(region: str, db: AsyncSession, limit: int = 24) -> list[GridLoadSnapshot]:
    result = await db.execute(
        select(GridLoadSnapshot)
        .where(GridLoadSnapshot.region == region)
        .order_by(GridLoadSnapshot.recorded_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
