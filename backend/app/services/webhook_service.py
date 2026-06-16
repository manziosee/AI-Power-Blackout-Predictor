"""Webhook dispatch — HMAC-signed payloads, delivery, retry logic."""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)

MAX_RETRIES = 3
TIMEOUT_SECONDS = 10


def sign_payload(secret: str, payload: dict) -> str:
    """Return HMAC-SHA256 hex signature over JSON-serialised payload."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def dispatch(subscription_id: str, event_type: str, payload: dict, secret: str, url: str) -> dict:
    """Send a signed webhook and log the result. Returns delivery status dict."""
    payload["event_type"] = event_type
    payload["webhook_id"] = str(uuid.uuid4())
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    signature = sign_payload(secret, payload)
    headers = {
        "Content-Type": "application/json",
        "X-Blackout-Signature": f"sha256={signature}",
        "X-Blackout-Event": event_type,
        "User-Agent": "BlackoutPredictor-Webhooks/1.0",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload, headers=headers)
            success = 200 <= resp.status_code < 300
            await _log_event(subscription_id, event_type, payload, resp.status_code, attempt, success, None)
            if success:
                log.info(f"Webhook delivered: {event_type} → {url} [{resp.status_code}]")
                return {"success": True, "status_code": resp.status_code, "attempt": attempt}
            log.warning(f"Webhook non-2xx attempt {attempt}: {resp.status_code}")
        except httpx.TimeoutException:
            await _log_event(subscription_id, event_type, payload, None, attempt, False, "timeout")
            log.warning(f"Webhook timeout attempt {attempt}: {url}")
        except Exception as exc:
            await _log_event(subscription_id, event_type, payload, None, attempt, False, str(exc))
            log.error(f"Webhook error attempt {attempt}: {exc}")

    return {"success": False, "status_code": None, "attempt": MAX_RETRIES}


async def _log_event(
    subscription_id: str,
    event_type: str,
    payload: dict,
    status: int | None,
    attempt: int,
    success: bool,
    error: str | None,
) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.enterprise import WebhookEvent

    async with AsyncSessionLocal() as db:
        db.add(WebhookEvent(
            subscription_id=uuid.UUID(subscription_id),
            event_type=event_type,
            payload=payload,
            response_status=status,
            attempt=attempt,
            success=success,
            error_message=error,
        ))
        await db.commit()


async def fire_prediction_webhooks(h3_index: str, probability: float, risk_level: str, window_start: str) -> int:
    """Find all active webhook subscriptions for an H3 cell and fire them."""
    from app.core.database import AsyncSessionLocal
    from app.models.enterprise import WebhookSubscription
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.h3_index == h3_index,
                WebhookSubscription.is_active,
                WebhookSubscription.threshold_probability <= probability,
            )
        )
        subs = result.scalars().all()

    fired = 0
    for sub in subs:
        if "prediction_threshold" not in (sub.events or []):
            continue

        payload = {
            "h3_index": h3_index,
            "probability": probability,
            "risk_level": risk_level,
            "window_start": window_start,
        }

        result = await dispatch(str(sub.id), "prediction_threshold", payload, sub.secret, sub.url)
        if result["success"]:
            fired += 1
            # Update last_triggered_at
            from app.core.database import AsyncSessionLocal
            from app.models.enterprise import WebhookSubscription
            from sqlalchemy import select, update

            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(WebhookSubscription)
                    .where(WebhookSubscription.id == sub.id)
                    .values(last_triggered_at=datetime.now(timezone.utc))
                )
                await db.commit()

    return fired


async def fire_outage_confirmed_webhooks(h3_index: str, report_id: str) -> int:
    """Fire webhooks for the outage_confirmed event."""
    from app.core.database import AsyncSessionLocal
    from app.models.enterprise import WebhookSubscription
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.h3_index == h3_index,
                WebhookSubscription.is_active,
            )
        )
        subs = result.scalars().all()

    fired = 0
    for sub in subs:
        if "outage_confirmed" not in (sub.events or []):
            continue
        payload = {"h3_index": h3_index, "report_id": report_id}
        result = await dispatch(str(sub.id), "outage_confirmed", payload, sub.secret, sub.url)
        if result["success"]:
            fired += 1
    return fired
