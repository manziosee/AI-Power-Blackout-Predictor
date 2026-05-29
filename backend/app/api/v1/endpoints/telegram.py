"""Telegram Bot webhook — handles all incoming updates (commands + messages)."""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.notifications import TelegramSubscription
from app.services.telegram_service import (
    main_menu_keyboard,
    send_message,
    send_outage_alert,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])
log = logging.getLogger(__name__)

WELCOME_TEXT = (
    "👋 <b>Welcome to Blackout Predictor!</b>\n\n"
    "I send you <b>AI-powered electricity outage alerts</b> for your area — "
    "before the lights go out.\n\n"
    "📍 <b>Share your location</b> below so I can track your neighborhood, "
    "or use one of the commands:\n\n"
    "/status — current risk for your area\n"
    "/report — report an active outage\n"
    "/stop — unsubscribe from alerts\n"
    "/help — show all commands"
)

HELP_TEXT = (
    "⚡ <b>Blackout Predictor Commands</b>\n\n"
    "/start — register and set your area\n"
    "/status — current outage risk\n"
    "/report — report an outage in your area\n"
    "/stop — stop receiving alerts\n"
    "/help — show this message\n\n"
    "📍 You can also <b>share your location</b> to auto-detect your neighborhood."
)


@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Main entry point for all Telegram updates."""
    body = await request.json()

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = str(message["chat"]["id"])
    username = message["chat"].get("username")
    text = message.get("text", "").strip()
    location = message.get("location")

    # Handle location share — register H3 cell for this chat
    if location:
        await _handle_location(chat_id, username, location["latitude"], location["longitude"], db)
        return {"ok": True}

    # Handle commands
    command = text.split()[0].lower() if text.startswith("/") else None

    if command == "/start":
        await _ensure_subscription(chat_id, username, db)
        await send_message(chat_id, WELCOME_TEXT, reply_markup=main_menu_keyboard())

    elif command == "/stop":
        await _deactivate(chat_id, db)
        await send_message(chat_id, "🔕 You have been unsubscribed. Send /start to reactivate alerts.")

    elif command == "/status":
        await _send_status(chat_id, db)

    elif command == "/report":
        await _handle_report(chat_id, db)

    elif command == "/help":
        await send_message(chat_id, HELP_TEXT)

    # Handle reply keyboard shortcuts
    elif text == "⚡ Check Status":
        await _send_status(chat_id, db)

    elif text == "🚨 Report Outage":
        await _handle_report(chat_id, db)

    elif text == "🔕 Unsubscribe":
        await _deactivate(chat_id, db)
        await send_message(chat_id, "🔕 Unsubscribed. Send /start to reactivate.")

    else:
        await send_message(chat_id, "Use /help to see available commands.", reply_markup=main_menu_keyboard())

    return {"ok": True}


async def _ensure_subscription(chat_id: str, username: str | None, db: AsyncSession) -> TelegramSubscription:
    result = await db.execute(select(TelegramSubscription).where(TelegramSubscription.chat_id == chat_id))
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_active = True
        sub.username = username
    else:
        sub = TelegramSubscription(chat_id=chat_id, username=username)
        db.add(sub)
    await db.flush()
    return sub


async def _deactivate(chat_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(TelegramSubscription).where(TelegramSubscription.chat_id == chat_id))
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_active = False


async def _handle_location(chat_id: str, username: str | None, lat: float, lng: float, db: AsyncSession) -> None:
    import h3
    h3_index = h3.latlng_to_cell(lat, lng, 8)

    sub = await _ensure_subscription(chat_id, username, db)
    sub.h3_index = h3_index

    # Fetch latest prediction for this cell
    from app.models.prediction import Prediction
    from sqlalchemy import select

    pred = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    prediction = pred.scalar_one_or_none()

    if prediction:
        await send_outage_alert(
            chat_id,
            int(prediction.probability * 100),
            prediction.window_start.strftime("%H:%M"),
            prediction.risk_level,
        )
    else:
        await send_message(
            chat_id,
            f"📍 Location registered! (cell: {h3_index[:8]}...)\n\n"
            f"No predictions yet for your area — check back in a few hours.",
            reply_markup=main_menu_keyboard(),
        )


async def _send_status(chat_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(TelegramSubscription).where(TelegramSubscription.chat_id == chat_id))
    sub = result.scalar_one_or_none()

    if not sub or not sub.h3_index:
        await send_message(chat_id, "📍 Share your location first so I can check your area's risk.")
        return

    from app.models.prediction import Prediction

    pred = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == sub.h3_index)
        .order_by(Prediction.predicted_at.desc())
        .limit(1)
    )
    prediction = pred.scalar_one_or_none()

    if not prediction:
        await send_message(chat_id, "No prediction data yet for your area. Try again in a few hours.")
        return

    await send_outage_alert(
        chat_id,
        int(prediction.probability * 100),
        prediction.window_start.strftime("%H:%M"),
        prediction.risk_level,
    )


async def _handle_report(chat_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(TelegramSubscription).where(TelegramSubscription.chat_id == chat_id))
    sub = result.scalar_one_or_none()

    if not sub or not sub.h3_index:
        await send_message(chat_id, "📍 Share your location first so we know where to register the outage.")
        return

    from app.models.outage import OutageReport

    report = OutageReport(h3_index=sub.h3_index, source="telegram")
    db.add(report)
    await db.flush()

    await send_message(
        chat_id,
        "✅ <b>Outage reported!</b>\n\nThank you — your report helps improve predictions for your community.",
        reply_markup=main_menu_keyboard(),
    )
