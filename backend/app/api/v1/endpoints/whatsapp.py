"""WhatsApp Cloud API webhook — handles incoming messages and opt-in/out."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.notifications import WhatsAppSubscription
from app.models.user import User
from app.services.whatsapp_service import send_whatsapp_text

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
log = logging.getLogger(__name__)

# ── Webhook verification (GET) ────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Meta calls this GET endpoint to verify the webhook URL."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


# ── Webhook events (POST) ─────────────────────────────────────────────────────

@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive incoming WhatsApp messages — handle STOP/START opt-in/out."""
    body = await request.json()

    try:
        entry = body["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])

        for msg in messages:
            from_number = f"+{msg['from']}"
            text = msg.get("text", {}).get("body", "").strip().upper()

            if text in ("STOP", "UNSUBSCRIBE", "OPT OUT"):
                await _opt_out(from_number, db)
                await send_whatsapp_text(from_number, "You have been unsubscribed from Blackout Predictor alerts. Reply START to resubscribe.")

            elif text in ("START", "SUBSCRIBE", "OPT IN"):
                await _opt_in(from_number, db)
                await send_whatsapp_text(from_number, "Welcome back! You will receive outage alerts for your registered area.")

            elif text == "STATUS":
                await send_whatsapp_text(from_number, "Reply with your area name or share your location to check the current risk.")

            elif text == "HELP":
                await send_whatsapp_text(
                    from_number,
                    "Blackout Predictor commands:\n"
                    "• STATUS — check your area's risk\n"
                    "• STOP — unsubscribe from alerts\n"
                    "• START — resubscribe to alerts\n"
                    "• REPORT — report an outage now",
                )

            elif text == "REPORT":
                await send_whatsapp_text(from_number, "Please share your location so we can register the outage for your area.")

    except (KeyError, IndexError):
        pass

    return {"status": "ok"}


# ── Subscription management ───────────────────────────────────────────────────

@router.post("/subscribe", status_code=201)
async def subscribe(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opt the current user's phone into WhatsApp alerts."""
    existing = await db.execute(
        select(WhatsAppSubscription).where(WhatsAppSubscription.phone == current_user.phone)
    )
    sub = existing.scalar_one_or_none()

    if sub:
        sub.is_active = True
    else:
        sub = WhatsAppSubscription(user_id=current_user.id, phone=current_user.phone)
        db.add(sub)

    await db.flush()

    await send_whatsapp_text(
        current_user.phone,
        "You are now subscribed to Blackout Predictor WhatsApp alerts! "
        "Reply STOP at any time to unsubscribe.",
    )
    return {"status": "subscribed", "phone": current_user.phone}


@router.delete("/unsubscribe", status_code=204)
async def unsubscribe(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opt the current user out of WhatsApp alerts."""
    await _opt_out(current_user.phone, db)


async def _opt_out(phone: str, db: AsyncSession) -> None:
    result = await db.execute(select(WhatsAppSubscription).where(WhatsAppSubscription.phone == phone))
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_active = False


async def _opt_in(phone: str, db: AsyncSession) -> None:
    result = await db.execute(select(WhatsAppSubscription).where(WhatsAppSubscription.phone == phone))
    sub = result.scalar_one_or_none()
    if sub:
        sub.is_active = True
