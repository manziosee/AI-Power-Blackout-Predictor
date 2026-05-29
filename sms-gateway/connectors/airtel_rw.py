import os

import httpx

from connectors.base import BaseConnector

JASMIN_HOST = os.getenv("JASMIN_HOST", "localhost")
JASMIN_PORT = os.getenv("JASMIN_HTTP_PORT", "8080")
JASMIN_USERNAME = os.getenv("JASMIN_USERNAME", "jcliadmin")
JASMIN_PASSWORD = os.getenv("JASMIN_PASSWORD", "jclipwd")

AIRTEL_RW_CONNECTOR_ID = os.getenv("AIRTEL_RW_CONNECTOR_ID", "airtel_rw")


class AirtelRwConnector(BaseConnector):
    provider_name = "jasmin_airtel_rw"

    async def send(self, to: str, message: str) -> dict:
        import uuid

        params = {
            "username": JASMIN_USERNAME,
            "password": JASMIN_PASSWORD,
            "to": to,
            "content": message,
            "from": "UMEME",
            "connector": AIRTEL_RW_CONNECTOR_ID,
            "coding": 0,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"http://{JASMIN_HOST}:{JASMIN_PORT}/send", params=params)
            resp.raise_for_status()
            text = resp.text.strip()
            message_id = text.split('"')[1] if '"' in text else str(uuid.uuid4())
            return {"message_id": message_id, "status": "sent"}

    async def get_delivery_status(self, message_id: str) -> str:
        return "unknown"
