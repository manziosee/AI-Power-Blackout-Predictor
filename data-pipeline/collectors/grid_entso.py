"""Fetch European grid load data from ENTSO-E Transparency Platform."""
import logging
import os
from datetime import datetime, timedelta

import httpx

log = logging.getLogger(__name__)

ENTSO_TOKEN = os.getenv("ENTSO_E_API_KEY", "")
ENTSO_BASE = "https://web-api.tp.entsoe.eu/api"


async def fetch_load(country_code: str, start: datetime, end: datetime) -> list[dict]:
    """Return hourly grid load data for a country (e.g. DE, FR, GB)."""
    params = {
        "securityToken": ENTSO_TOKEN,
        "documentType": "A65",
        "processType": "A16",
        "outBiddingZone_Domain": f"10Y{country_code}-{country_code}0--------",
        "periodStart": start.strftime("%Y%m%d%H00"),
        "periodEnd": end.strftime("%Y%m%d%H00"),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(ENTSO_BASE, params=params)
            resp.raise_for_status()
            return _parse_xml(resp.text)
        except Exception as exc:
            log.warning(f"ENTSO-E fetch failed for {country_code}: {exc}")
            return []


def _parse_xml(xml_text: str) -> list[dict]:
    """Minimal XML parse — returns list of {datetime, load_mw} dicts."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
        ns = {"ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}
        results = []
        for point in root.findall(".//ns:Point", ns):
            pos = point.findtext("ns:position", namespaces=ns)
            qty = point.findtext("ns:quantity", namespaces=ns)
            if pos and qty:
                results.append({"position": int(pos), "load_mw": float(qty)})
        return results
    except Exception:
        return []


if __name__ == "__main__":
    import asyncio
    now = datetime.utcnow()
    data = asyncio.run(fetch_load("DE", now - timedelta(hours=24), now))
    print(f"Fetched {len(data)} ENTSO-E records for DE")
