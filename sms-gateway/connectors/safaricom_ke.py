import os

from connectors.base import BaseConnector

SAFARICOM_CONNECTOR_ID = os.getenv("SAFARICOM_KE_CONNECTOR_ID", "safaricom_ke")
JASMIN_HOST = os.getenv("JASMIN_HOST", "localhost")
JASMIN_PORT = os.getenv("JASMIN_HTTP_PORT", "8080")
JASMIN_USERNAME = os.getenv("JASMIN_USERNAME", "jcliadmin")
JASMIN_PASSWORD = os.getenv("JASMIN_PASSWORD", "jclipwd")


class SafaricomKeConnector(BaseConnector):
    provider_name = "jasmin_safaricom_ke"

    async def send(self, to: str, message: str) -> dict:
        import uuid
        import httpx

        params = {
            "username": JASMIN_USERNAME,
            "password": JASMIN_PASSWORD,
            "to": to,
            "content": message,
            "from": "UMEME",
            "connector": SAFARICOM_CONNECTOR_ID,
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
