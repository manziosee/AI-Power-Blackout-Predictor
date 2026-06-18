"""Web Push notification service using VAPID keys."""
import json
import os

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CONTACT_EMAIL = os.getenv("VAPID_CONTACT_EMAIL", "admin@poweralert.app")


async def send_push(endpoint: str, p256dh: str, auth: str, title: str, body: str, data: dict | None = None) -> bool:
    """Send a single web push notification. Returns True on success."""
    if not VAPID_PRIVATE_KEY:
        return False
    try:
        from pywebpush import webpush
        payload = json.dumps({"title": title, "body": body, "data": data or {}})
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_CONTACT_EMAIL}"},
        )
        return True
    except Exception:
        return False


async def send_push_to_cell(h3_index: str, title: str, body: str, data: dict, db) -> int:
    """Send push notifications to all subscribers in a cell. Returns count sent."""
    from app.models.alert import AlertSubscription
    from app.models.push import PushSubscription
    from sqlalchemy import select

    subs_result = await db.execute(
        select(PushSubscription)
        .join(AlertSubscription, AlertSubscription.user_id == PushSubscription.user_id)
        .where(AlertSubscription.h3_index == h3_index, AlertSubscription.is_active)
    )
    subs = subs_result.scalars().all()

    sent = 0
    for sub in subs:
        ok = await send_push(sub.endpoint, sub.p256dh, sub.auth, title, body, data)
        if ok:
            sent += 1
    return sent
