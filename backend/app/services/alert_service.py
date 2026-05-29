import httpx

from app.core.config import settings


async def send_sms_alert(
    phone: str,
    country_code: str,
    language: str,
    template_key: str,
    template_vars: dict,
) -> dict:
    """Send an SMS alert via our SMS Gateway microservice."""
    payload = {
        "to": phone,
        "country": country_code,
        "lang": language,
        "template": template_key,
        "vars": template_vars,
    }
    headers = {"X-API-Key": settings.SMS_GATEWAY_API_KEY}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{settings.SMS_GATEWAY_URL}/sms/send", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def send_push_notification(user_id: str, title: str, body: str) -> None:
    """Placeholder — integrate with Web Push or FCM."""
    pass
