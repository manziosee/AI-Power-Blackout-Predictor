"""iCal calendar subscription feed for planned outages in a user's subscribed cells."""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.alert import AlertSubscription
from app.models.planned_outage import PlannedOutage
from app.models.user import User

router = APIRouter(tags=["Calendar"])

_HMAC_LEN = 24


def _make_token(user_id: uuid.UUID) -> str:
    uid_hex = user_id.hex
    sig = hmac.new(settings.SECRET_KEY.encode(), uid_hex.encode(), hashlib.sha256).hexdigest()[:_HMAC_LEN]
    return f"{uid_hex}.{sig}"


def _verify_token(token: str) -> uuid.UUID | None:
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    uid_hex, sig = parts
    try:
        user_id = uuid.UUID(uid_hex)
    except ValueError:
        return None
    expected = hmac.new(settings.SECRET_KEY.encode(), uid_hex.encode(), hashlib.sha256).hexdigest()[:_HMAC_LEN]
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id


def _dt_to_ical(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _build_ical(events: list[PlannedOutage]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Power Blackout Predictor//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Planned Outages",
        "X-WR-TIMEZONE:UTC",
    ]
    for ev in events:
        uid_val = f"{ev.id}@blackoutpredictor"
        summary = ev.title.replace("\n", " ")
        desc = (ev.description or "").replace("\n", "\\n")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid_val}",
            f"DTSTAMP:{_dt_to_ical(datetime.now(timezone.utc))}",
            f"DTSTART:{_dt_to_ical(ev.starts_at)}",
            f"DTEND:{_dt_to_ical(ev.ends_at)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:H3:{ev.h3_index}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("/users/me/calendar-token")
async def get_calendar_token(current_user: User = Depends(get_current_user)):
    token = _make_token(current_user.id)
    return {
        "token": token,
        "url": f"{settings.APP_URL}/api/v1/calendar/{token}.ics",
    }


@router.get("/calendar/{token}.ics")
async def calendar_feed(token: str, db: AsyncSession = Depends(get_db)):
    user_id = _verify_token(token)
    if not user_id:
        raise HTTPException(status_code=404, detail="Calendar not found")

    subs = (await db.execute(
        select(AlertSubscription).where(
            AlertSubscription.user_id == user_id,
            AlertSubscription.is_active.is_(True),
        )
    )).scalars().all()

    if not subs:
        ical = _build_ical([])
        return Response(content=ical, media_type="text/calendar; charset=utf-8")

    h3_cells = [s.h3_index for s in subs]
    now = datetime.now(timezone.utc)

    planned = (await db.execute(
        select(PlannedOutage)
        .where(
            PlannedOutage.h3_index.in_(h3_cells),
            PlannedOutage.ends_at >= now,
            PlannedOutage.status != "cancelled",
        )
        .order_by(PlannedOutage.starts_at.asc())
        .limit(200)
    )).scalars().all()

    ical = _build_ical(list(planned))
    return Response(content=ical, media_type="text/calendar; charset=utf-8")
