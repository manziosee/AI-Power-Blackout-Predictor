import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.alert import AlertSubscription, SmsAlert
from app.models.user import User
from app.schemas.alert import AlertSubscriptionCreate, AlertSubscriptionOut, SmsAlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/subscriptions", response_model=AlertSubscriptionOut, status_code=201)
async def create_subscription(
    payload: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = AlertSubscription(user_id=current_user.id, **payload.model_dump())
    db.add(sub)
    await db.flush()
    return sub


@router.get("/subscriptions", response_model=List[AlertSubscriptionOut])
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


@router.get("/history", response_model=List[SmsAlertOut])
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
