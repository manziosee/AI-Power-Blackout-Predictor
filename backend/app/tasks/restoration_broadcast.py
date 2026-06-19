"""Broadcast restoration ETA updates via push notifications and SMS."""
from celery import shared_task


@shared_task(name="tasks.broadcast_restoration_update")
def broadcast_restoration_update(event_id: str, h3_index: str, status: str, eta_minutes: int | None) -> dict:
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.services.restoration_service import eta_label

    STATUS_MESSAGES = {
        "acknowledged": "Your area outage has been acknowledged by the utility.",
        "crew_assigned": "A crew has been assigned to restore power in your area.",
        "crew_en_route": "Crew is en route to your area.",
        "crew_on_site": "Crew is on site working to restore power.",
        "restored": "Power has been restored in your area.",
        "cancelled": "Restoration update: status changed.",
    }

    title = "Power Restoration Update"
    body = STATUS_MESSAGES.get(status, f"Status: {status}")
    if eta_minutes and status not in ("restored", "cancelled"):
        body += f" ETA: {eta_label(eta_minutes)}."

    async def _run():
        from app.services.push_service import send_push_to_cell
        async with AsyncSessionLocal() as db:
            sent = await send_push_to_cell(
                h3_index, title, body,
                {"event_id": event_id, "status": status, "eta_minutes": eta_minutes},
                db,
            )
            return {"push_sent": sent, "h3_index": h3_index, "status": status}

    return asyncio.run(_run())
