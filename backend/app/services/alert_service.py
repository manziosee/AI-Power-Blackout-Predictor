import json
import logging

import httpx
from pywebpush import webpush, WebPushException

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_sms_alert(
    phone: str,
    country_code: str,
    language: str,
    template_key: str,
    template_vars: dict,
) -> dict:
    """Send an SMS alert via the SMS Gateway microservice."""
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
    """Send a Web Push notification to all browser subscriptions belonging to a user."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.debug("VAPID keys not configured — skipping push notification")
        return

    import uuid
    from app.core.database import AsyncSessionLocal
    from app.models.push import PushSubscription
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PushSubscription).where(PushSubscription.user_id == uuid.UUID(user_id))
        )
        subscriptions = result.scalars().all()

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            )
        except WebPushException as exc:
            logger.warning(f"Push failed for subscription {sub.id}: {exc}")
        except Exception as exc:
            logger.error(f"Unexpected push error for subscription {sub.id}: {exc}")
