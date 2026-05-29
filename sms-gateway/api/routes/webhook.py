import logging

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)


@router.post("/delivery-receipt")
async def delivery_receipt(request: Request):
    """Receive delivery receipt callbacks from telecom operators via Jasmin."""
    body = await request.json()
    logger.info(f"Delivery receipt: {body}")
    # Update sms_alerts status in backend DB via internal API call (Phase 2)
    return {"received": True}
