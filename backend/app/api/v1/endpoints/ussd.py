"""
USSD webhook endpoint — compatible with Africa's Talking aggregator format.

Africa's Talking POST fields:
  sessionId   – unique session identifier
  phoneNumber – caller's E.164 number
  networkCode – operator code
  serviceCode – the USSD short code dialled
  text        – accumulated input separated by * (empty on first dial)

Response must be plain text starting with:
  CON <menu>   → keep session open
  END <text>   → close session
"""
import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.ussd_service import handle_ussd
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/ussd", tags=["ussd"])
logger = logging.getLogger(__name__)


def _verify_at_signature(body: bytes, signature: str | None) -> bool:
    """Validate Africa's Talking HMAC-SHA256 signature (optional — only if secret configured)."""
    if not settings.USSD_AT_SECRET:
        return True
    if not signature:
        return False
    expected = hmac.new(settings.USSD_AT_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/session", response_class=PlainTextResponse)
async def ussd_session(
    request: Request,
    sessionId: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    networkCode: str = Form(default=""),
    serviceCode: str = Form(default=""),
    x_africastalking_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    if not _verify_at_signature(raw_body, x_africastalking_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    logger.info("USSD session=%s phone=%s text=%r", sessionId, phoneNumber, text)

    response_text = await handle_ussd(
        session_id=sessionId,
        phone=phoneNumber,
        text=text,
        db=db,
    )
    return PlainTextResponse(content=response_text)
