from fastapi import APIRouter, HTTPException

from api.services.router import get_connector_by_message_id

router = APIRouter(prefix="/sms", tags=["sms"])


@router.get("/status/{message_id}")
async def get_status(message_id: str):
    connector = get_connector_by_message_id(message_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Message not found")
    status = await connector.get_delivery_status(message_id)
    return {"message_id": message_id, "status": status}
