"""
Inbound SMS route — receives messages from Jasmin SMPP / AT / operator webhook,
parses the payload into a normalised schema, forwards to the backend for keyword
processing, then sends the reply back to the originating number.
"""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(prefix="/sms", tags=["sms-inbound"])
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
INTERNAL_KEY = os.getenv("SMS_GATEWAY_API_KEY", "")


# ── Normalised inbound payload ────────────────────────────────────────────────

class NormalisedInbound(BaseModel):
    phone: str   # sender E.164
    text: str
    to: str = ""


def _parse_jasmin(body: dict) -> NormalisedInbound:
    """Jasmin delivers: id, from, to, content, date"""
    return NormalisedInbound(
        phone=body.get("from", ""),
        text=body.get("content", ""),
        to=body.get("to", ""),
    )


def _parse_at(body: dict) -> NormalisedInbound:
    """Africa's Talking inbound: from, to, text, id, date, networkCode"""
    return NormalisedInbound(
        phone=body.get("from", ""),
        text=body.get("text", ""),
        to=body.get("to", ""),
    )


def _parse_generic(body: dict) -> NormalisedInbound:
    phone = body.get("from") or body.get("phone") or body.get("msisdn") or ""
    text  = body.get("text") or body.get("content") or body.get("message") or ""
    return NormalisedInbound(phone=phone, text=text)


async def _forward_to_backend(payload: NormalisedInbound) -> str:
    """Send to backend /api/v1/sms-inbound/receive and return the reply text."""
    headers = {"X-Internal-Key": INTERNAL_KEY} if INTERNAL_KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/sms-inbound/receive",
            json=payload.model_dump(),
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json().get("reply", "")


async def _send_reply(to: str, country: str, reply: str) -> None:
    """Fire-and-forget: send the reply SMS via the existing /sms/send route."""
    if not reply or not to:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "http://localhost:8001/sms/send",
                json={
                    "to": to,
                    "country": country,
                    "lang": "en",
                    "template": "_raw",
                    "vars": {"message": reply},
                },
            )
    except Exception as exc:
        logger.warning("Reply send failed: %s", exc)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/inbound/jasmin")
async def inbound_jasmin(request: Request):
    """Jasmin HTTP connector callback."""
    body = await request.json()
    logger.info("Jasmin inbound: %s", body)
    payload = _parse_jasmin(body)
    if not payload.phone:
        return {"status": "ignored"}
    try:
        reply = await _forward_to_backend(payload)
        await _send_reply(payload.phone, _detect_country(payload.phone), reply)
    except Exception as exc:
        logger.error("Inbound processing error: %s", exc)
    return {"status": "ok"}


@router.post("/inbound/africastalking", response_class=PlainTextResponse)
async def inbound_at(request: Request):
    """Africa's Talking inbound SMS webhook."""
    form = await request.form()
    body = dict(form)
    logger.info("AT inbound: %s", body)
    payload = _parse_at(body)
    if not payload.phone:
        return PlainTextResponse("")
    try:
        reply = await _forward_to_backend(payload)
        # AT reads the response body as the reply message
        return PlainTextResponse(reply)
    except Exception as exc:
        logger.error("AT inbound error: %s", exc)
        return PlainTextResponse("")


@router.post("/inbound/generic")
async def inbound_generic(request: Request):
    """Generic JSON inbound for any other aggregator."""
    body = await request.json()
    payload = _parse_generic(body)
    if not payload.phone:
        raise HTTPException(status_code=400, detail="Missing phone number")
    try:
        reply = await _forward_to_backend(payload)
        await _send_reply(payload.phone, _detect_country(payload.phone), reply)
    except Exception as exc:
        logger.error("Generic inbound error: %s", exc)
    return {"status": "ok"}


def _detect_country(phone: str) -> str:
    """Best-effort country code from E.164 prefix."""
    prefixes = {
        "+250": "RW", "+254": "KE", "+255": "TZ", "+256": "UG",
        "+234": "NG", "+233": "GH", "+221": "SN", "+212": "MA",
        "+213": "DZ", "+27":  "ZA", "+1":   "US", "+44":  "GB",
    }
    for prefix, code in sorted(prefixes.items(), key=lambda x: -len(x[0])):
        if phone.startswith(prefix):
            return code
    return "RW"
