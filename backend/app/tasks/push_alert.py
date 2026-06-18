"""Celery task — send web push notifications for outage alerts."""
from celery import shared_task


@shared_task(name="tasks.send_push_alert")
def send_push_alert(h3_index: str, title: str, body: str, data: dict | None = None) -> dict:
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.services.push_service import send_push_to_cell

    async def _run():
        async with AsyncSessionLocal() as db:
            sent = await send_push_to_cell(h3_index, title, body, data or {}, db)
            return {"h3_index": h3_index, "notifications_sent": sent}

    return asyncio.run(_run())
