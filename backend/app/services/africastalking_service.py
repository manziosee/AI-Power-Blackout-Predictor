"""Africa's Talking HTTP SMS API — no SMPP required.

Used when the Jasmin SMPP gateway is unavailable or not configured.
AT free sandbox: username="sandbox", apiKey from dashboard.
Production: set AFRICASTALKING_USERNAME to your AT account username.
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_AT_SMS_URL = "https://api.africastalking.com/version1/messaging"
_AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


def _base_url() -> str:
    return _AT_SANDBOX_URL if settings.AFRICASTALKING_USERNAME == "sandbox" else _AT_SMS_URL


async def send_sms(phone: str, message: str) -> dict:
    """Send a single SMS via Africa's Talking HTTP API.

    Returns AT response dict with recipients list and status.
    Raises httpx.HTTPStatusError on 4xx/5xx.
    """
    if not settings.AFRICASTALKING_API_KEY:
        logger.warning("AFRICASTALKING_API_KEY not set — SMS not sent to %s", phone)
        return {"error": "AT API key not configured"}

    headers = {
        "apiKey": settings.AFRICASTALKING_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "username": settings.AFRICASTALKING_USERNAME,
        "to": phone,
        "message": message,
    }
    if settings.AFRICASTALKING_SENDER_ID:
        data["from"] = settings.AFRICASTALKING_SENDER_ID

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(_base_url(), headers=headers, data=data)
        resp.raise_for_status()
        result = resp.json()
        logger.info("AT SMS sent to %s: %s", phone, result)
        return result


async def send_bulk_sms(recipients: list[str], message: str) -> dict:
    """Send the same message to multiple recipients in one AT API call."""
    if not recipients:
        return {}
    return await send_sms(",".join(recipients), message)
