"""
SMS inbound endpoint — called by the sms-gateway when Jasmin/SMPP delivers
an incoming message, or by AT/Twilio inbound webhook directly.

Expected JSON body:
  { "from": "+250788123456", "text": "STATUS", "to": "+250800000001" }

The endpoint returns the reply text; the caller is responsible for sending it.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.sms_inbound_service import process_inbound_sms

router = APIRouter(prefix="/sms-inbound", tags=["SMS Inbound"])
logger = logging.getLogger(__name__)


class InboundSmsPayload(BaseModel):
    # "from" is a reserved word — aliased
    phone: str  # sender's E.164 number
    text: str
    to: str = ""

    model_config = {"populate_by_name": True}


class InboundSmsResponse(BaseModel):
    reply: str


def _check_internal_key(x_internal_key: str | None = None) -> None:
    """Light guard so only the sms-gateway can call this endpoint internally."""
    if settings.SMS_GATEWAY_API_KEY and x_internal_key != settings.SMS_GATEWAY_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/receive", response_model=InboundSmsResponse)
async def receive_inbound_sms(
    payload: InboundSmsPayload,
    db: AsyncSession = Depends(get_db),
):
    logger.info("Inbound SMS from=%s text=%r", payload.phone, payload.text)
    reply = await process_inbound_sms(
        phone=payload.phone,
        message=payload.text,
        db=db,
    )
    return InboundSmsResponse(reply=reply)
