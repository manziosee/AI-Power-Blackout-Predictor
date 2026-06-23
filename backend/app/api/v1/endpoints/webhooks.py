"""Webhook subscription management — IoT / Home Assistant / IFTTT / Zapier integration."""
import uuid as _uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enterprise import WebhookEvent, WebhookSubscription
from app.models.user import User

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

SUPPORTED_EVENTS = ["prediction_threshold", "outage_confirmed", "outage_resolved"]


class WebhookCreate(BaseModel):
    h3_index: str
    url: HttpUrl
    threshold_probability: float = 0.70
    events: List[str] = ["prediction_threshold", "outage_confirmed"]


class WebhookOut(BaseModel):
    id: _uuid.UUID
    h3_index: str
    url: str
    secret: str
    threshold_probability: float
    events: list
    is_active: bool
    last_triggered_at: str | None = None

    model_config = {"from_attributes": True}


class WebhookTestResult(BaseModel):
    success: bool
    status_code: int | None
    message: str


@router.post("/", response_model=WebhookOut, status_code=201)
async def create_webhook(
    payload: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a webhook endpoint. Returns the secret — store it securely."""
    invalid = [e for e in payload.events if e not in SUPPORTED_EVENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unsupported events: {invalid}. Supported: {SUPPORTED_EVENTS}")

    sub = WebhookSubscription(
        user_id=current_user.id,
        h3_index=payload.h3_index,
        url=str(payload.url),
        threshold_probability=payload.threshold_probability,
        events=payload.events,
    )
    db.add(sub)
    await db.flush()
    return sub


@router.get("/", response_model=List[WebhookOut])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.user_id == current_user.id)
    )
    return result.scalars().all()


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: _uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    sub.is_active = False


@router.post("/{webhook_id}/test", response_model=WebhookTestResult)
async def test_webhook(
    webhook_id: _uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test payload to verify your webhook endpoint is reachable."""
    result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")

    from app.services.webhook_service import dispatch

    test_payload = {
        "h3_index": sub.h3_index,
        "probability": 0.85,
        "risk_level": "high",
        "window_start": "2026-01-01T18:00:00Z",
        "test": True,
    }
    delivery = await dispatch(str(sub.id), "test", test_payload, sub.secret, sub.url)

    return WebhookTestResult(
        success=delivery["success"],
        status_code=delivery["status_code"],
        message="Webhook delivered successfully" if delivery["success"] else f"Delivery failed after {delivery['attempt']} attempt(s)",
    )


@router.get("/{webhook_id}/events")
async def webhook_events(
    webhook_id: _uuid.UUID,
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return delivery log for a webhook subscription."""
    sub_result = await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.id == webhook_id,
            WebhookSubscription.user_id == current_user.id,
        )
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook not found")

    events_result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.subscription_id == webhook_id)
        .order_by(WebhookEvent.fired_at.desc())
        .limit(limit)
    )
    events = events_result.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "success": e.success,
            "response_status": e.response_status,
            "attempt": e.attempt,
            "fired_at": e.fired_at.isoformat(),
            "error": e.error_message,
        }
        for e in events
    ]
