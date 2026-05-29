from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.router import get_connector
from api.services.templates import render_template

router = APIRouter(prefix="/sms", tags=["sms"])


class SmsSendRequest(BaseModel):
    to: str                   # E.164 phone number e.g. +250788123456
    country: str              # ISO country code e.g. RW
    lang: str = "en"
    template: str             # template key e.g. outage_warning
    vars: dict = {}


class SmsSendResponse(BaseModel):
    message_id: str
    status: str
    provider: str


@router.post("/send", response_model=SmsSendResponse)
async def send_sms(payload: SmsSendRequest):
    message = render_template(payload.template, payload.lang, payload.vars)
    if not message:
        raise HTTPException(status_code=400, detail=f"Template '{payload.template}' not found for lang '{payload.lang}'")

    connector = get_connector(payload.country)
    result = await connector.send(to=payload.to, message=message)

    return SmsSendResponse(
        message_id=result["message_id"],
        status=result["status"],
        provider=connector.provider_name,
    )
