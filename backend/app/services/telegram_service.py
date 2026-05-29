"""Telegram Bot API integration — outage alerts and user commands."""
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

TG_BASE = "https://api.telegram.org/bot{token}/{method}"


def _url(method: str) -> str:
    return TG_BASE.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML", reply_markup: dict | None = None) -> dict:
    if not settings.TELEGRAM_BOT_TOKEN:
        log.debug("Telegram bot token not configured — skipping")
        return {}

    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(_url("sendMessage"), json=payload)
        if resp.status_code != 200:
            log.error(f"Telegram sendMessage error {resp.status_code}: {resp.text}")
        return resp.json()


async def set_webhook(webhook_url: str) -> dict:
    """Register our webhook URL with Telegram."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(_url("setWebhook"), json={"url": webhook_url})
        return resp.json()


async def send_outage_alert(chat_id: str, probability: int, time_str: str, risk_level: str) -> None:
    RISK_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🟣"}
    emoji = RISK_EMOJI.get(risk_level, "⚡")

    text = (
        f"{emoji} <b>Blackout Predictor Alert</b>\n\n"
        f"⚡ <b>{probability}% chance</b> of outage in your area\n"
        f"🕐 Predicted window: <b>{time_str}</b>\n"
        f"📊 Risk level: <b>{risk_level.upper()}</b>\n\n"
        f"<i>Charge your devices now.</i>\n\n"
        f"Reply /status to check current risk or /report to report an outage."
    )
    await send_message(chat_id, text)


async def send_confirmed_alert(chat_id: str) -> None:
    text = (
        "🔴 <b>Outage Confirmed</b>\n\n"
        "Multiple users in your area have confirmed a power outage.\n\n"
        "Reply /report to add your confirmation or /status for more details."
    )
    await send_message(chat_id, text)


async def send_weekly_digest(chat_id: str, area: str, outages_last_week: int, predictions_this_week: int) -> None:
    if outages_last_week == 0 and predictions_this_week == 0:
        trend = "✅ Great news — no outages last week and none predicted this week!"
    elif predictions_this_week > outages_last_week:
        trend = "⚠️ More outages predicted this week than last — stay prepared."
    else:
        trend = "📉 Fewer outages expected this week compared to last."

    text = (
        f"📊 <b>Weekly Digest — {area}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Last week: <b>{outages_last_week} outages</b>\n"
        f"🔮 This week: <b>{predictions_this_week} predicted</b>\n\n"
        f"{trend}\n\n"
        f"<i>Reply /status anytime for the latest risk level.</i>"
    )
    await send_message(chat_id, text)


def main_menu_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": "⚡ Check Status"}, {"text": "📍 Share Location", "request_location": True}],
            [{"text": "🚨 Report Outage"}, {"text": "🔕 Unsubscribe"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }
