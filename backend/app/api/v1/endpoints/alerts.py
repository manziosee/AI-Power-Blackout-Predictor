import uuid
from datetime import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.alert import AlertSubscription, SmsAlert
from app.models.user import User
from app.schemas.alert import AlertSubscriptionCreate, AlertSubscriptionOut, SmsAlertOut

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/subscriptions", response_model=AlertSubscriptionOut, status_code=201,
             summary="Subscribe to alerts for an H3 cell",
             description="Create an alert subscription for a location. Alerts fire via SMS/Push/WhatsApp/Telegram when prediction probability exceeds the threshold.")
async def create_subscription(
    payload: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = AlertSubscription(user_id=current_user.id, **payload.model_dump())
    db.add(sub)
    await db.flush()
    return sub


@router.get("/subscriptions", response_model=List[AlertSubscriptionOut],
            summary="List the current user's alert subscriptions")
async def list_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertSubscription).where(AlertSubscription.user_id == current_user.id)
    )
    return result.scalars().all()


@router.delete("/subscriptions/{sub_id}", status_code=204)
async def delete_subscription(
    sub_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertSubscription).where(
            AlertSubscription.id == sub_id, AlertSubscription.user_id == current_user.id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.delete(sub)


@router.get("/history", response_model=List[SmsAlertOut],
            summary="Recent SMS alert delivery history")
async def alert_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SmsAlert)
        .where(SmsAlert.user_id == current_user.id)
        .order_by(SmsAlert.sent_at.desc())
        .limit(50)
    )
    return result.scalars().all()


# ── Quiet hours ─────────────────────────────────────────────────────────────

_VALID_OVERRIDES = {"HIGH", "VERY_HIGH", "CRITICAL"}


class QuietHoursUpdate(BaseModel):
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    quiet_risk_override: str | None = None  # HIGH / VERY_HIGH / CRITICAL / null to clear


@router.patch("/subscriptions/{sub_id}/quiet-hours", response_model=AlertSubscriptionOut,
              summary="Configure quiet hours and risk-level override",
              description="Suppress alerts during sleeping hours. Set `quiet_risk_override` to HIGH/VERY_HIGH/CRITICAL to still receive critical-risk alerts even during quiet hours.")
async def update_quiet_hours(
    sub_id: uuid.UUID,
    payload: QuietHoursUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertSubscription).where(
            AlertSubscription.id == sub_id, AlertSubscription.user_id == current_user.id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if payload.quiet_risk_override is not None and payload.quiet_risk_override not in _VALID_OVERRIDES:
        raise HTTPException(status_code=400, detail=f"quiet_risk_override must be one of {sorted(_VALID_OVERRIDES)}")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)

    await db.flush()
    return sub
