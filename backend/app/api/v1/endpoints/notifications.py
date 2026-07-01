"""
Notifications API
  GET  /notifications/feed              — chronological inbox (paginated)
  PATCH /notifications/{id}/read        — mark one item read
  POST  /notifications/read-all         — mark all read
  GET  /notifications/preferences       — get global notification prefs
  PUT  /notifications/preferences       — upsert global notification prefs
"""
import uuid
from datetime import time
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.notification_feed import NotificationFeedItem
from app.models.user import User
from app.models.user_preferences import UserNotificationPreferences

router = APIRouter(prefix="/notifications", tags=["Notifications"])

_VALID_CHANNELS = {"sms", "push", "email", "telegram", "whatsapp"}
_VALID_OVERRIDES = {"HIGH", "VERY_HIGH", "CRITICAL"}


# ── Schemas ────────────────────────────────────────────────────────────────────

class FeedItemOut(BaseModel):
    id: uuid.UUID
    channel: str
    title: str
    body: str
    h3_index: str | None
    risk_level: str | None
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_item(cls, item: NotificationFeedItem) -> "FeedItemOut":
        return cls(
            id=item.id,
            channel=item.channel,
            title=item.title,
            body=item.body,
            h3_index=item.h3_index,
            risk_level=item.risk_level,
            is_read=item.is_read,
            created_at=item.created_at.isoformat(),
        )


class PreferencesIn(BaseModel):
    channels: List[str] | None = None
    default_threshold: float | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    quiet_risk_override: str | None = None
    all_notifications_enabled: bool | None = None


class PreferencesOut(BaseModel):
    id: uuid.UUID
    channels: List[str]
    default_threshold: float
    quiet_hours_start: time | None
    quiet_hours_end: time | None
    quiet_risk_override: str | None
    all_notifications_enabled: bool

    model_config = {"from_attributes": True}


# ── Feed ───────────────────────────────────────────────────────────────────────

@router.get("/feed", response_model=List[FeedItemOut], summary="Unified notification inbox")
async def get_feed(
    unread_only: bool = Query(False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(NotificationFeedItem)
        .where(NotificationFeedItem.user_id == current_user.id)
        .order_by(NotificationFeedItem.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if unread_only:
        q = q.where(NotificationFeedItem.is_read.is_(False))
    rows = (await db.execute(q)).scalars().all()
    return [FeedItemOut.from_orm_item(r) for r in rows]


@router.patch("/{item_id}/read", summary="Mark a notification as read")
async def mark_read(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(NotificationFeedItem)
        .where(
            NotificationFeedItem.id == item_id,
            NotificationFeedItem.user_id == current_user.id,
        )
        .values(is_read=True)
    )
    return {"ok": True}


@router.post("/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(NotificationFeedItem)
        .where(
            NotificationFeedItem.user_id == current_user.id,
            NotificationFeedItem.is_read.is_(False),
        )
        .values(is_read=True)
    )
    return {"ok": True}


# ── Preferences ────────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=PreferencesOut, summary="Get global notification preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(current_user.id, db)
    return prefs


@router.put("/preferences", response_model=PreferencesOut, summary="Update global notification preferences")
async def update_preferences(
    payload: PreferencesIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException

    if payload.channels is not None:
        invalid = set(payload.channels) - _VALID_CHANNELS
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid channels: {invalid}. Valid: {_VALID_CHANNELS}")
    if payload.quiet_risk_override is not None and payload.quiet_risk_override not in _VALID_OVERRIDES:
        raise HTTPException(status_code=400, detail=f"quiet_risk_override must be one of {sorted(_VALID_OVERRIDES)}")

    prefs = await _get_or_create_prefs(current_user.id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    await db.flush()
    return prefs


async def _get_or_create_prefs(user_id: uuid.UUID, db: AsyncSession) -> UserNotificationPreferences:
    prefs = (await db.execute(
        select(UserNotificationPreferences).where(UserNotificationPreferences.user_id == user_id)
    )).scalar_one_or_none()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=user_id)
        db.add(prefs)
        await db.flush()
    return prefs
