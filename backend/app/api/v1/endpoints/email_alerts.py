"""Email digest subscription management."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.notifications import EmailSubscription
from app.models.user import User

router = APIRouter(prefix="/email", tags=["Email Alerts"])


class EmailSubscribeRequest(BaseModel):
    email: EmailStr
    h3_index: str


@router.post("/subscribe", status_code=201)
async def subscribe(
    payload: EmailSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(EmailSubscription).where(
            EmailSubscription.user_id == current_user.id,
            EmailSubscription.h3_index == payload.h3_index,
        )
    )
    sub = existing.scalar_one_or_none()
    if sub:
        sub.email = str(payload.email)
        sub.is_active = True
    else:
        sub = EmailSubscription(
            user_id=current_user.id,
            email=str(payload.email),
            h3_index=payload.h3_index,
        )
        db.add(sub)
    await db.flush()
    return {"status": "subscribed", "email": str(payload.email), "digest": "every Monday at 08:00 UTC"}


@router.get("/unsubscribe/{sub_id}", status_code=200)
async def unsubscribe_by_link(sub_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """One-click unsubscribe from email link (no auth required)."""
    result = await db.execute(select(EmailSubscription).where(EmailSubscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.is_active = False
    return {"status": "unsubscribed"}


@router.delete("/unsubscribe", status_code=204)
async def unsubscribe_auth(
    h3_index: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe from email digest for a specific area (authenticated)."""
    result = await db.execute(
        select(EmailSubscription).where(
            EmailSubscription.user_id == current_user.id,
            EmailSubscription.h3_index == h3_index,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_active = False
