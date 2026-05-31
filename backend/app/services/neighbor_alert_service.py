"""Notify registered users in neighboring H3 cells when an outage is reported."""
import logging
from datetime import datetime, timedelta, timezone

import h3

log = logging.getLogger(__name__)

RATE_LIMIT_MINUTES = 60   # max one neighbor alert per H3 cell per hour
RING_SIZE = 1              # H3 ring-1 = the 6 immediately adjacent cells


async def notify_neighbors(report_id: str, h3_index: str, reporter_user_id: str) -> int:
    """Find users in neighboring cells and send them a confirmation request.

    Returns the number of users notified.
    """
    if not await _can_send(h3_index):
        log.info(f"Neighbor alert rate-limited for {h3_index}")
        return 0

    neighbor_cells = list(h3.grid_disk(h3_index, RING_SIZE))
    neighbor_cells = [c for c in neighbor_cells if c != h3_index]

    recipients = await _find_recipients(h3_index, neighbor_cells, reporter_user_id)
    if not recipients:
        return 0

    sent = 0
    for user_id, phone, push_subs, language in recipients:
        try:
            await _send_neighbor_push(push_subs, h3_index)
            sent += 1
        except Exception as exc:
            log.error(f"Neighbor push failed for {user_id}: {exc}")

    await _log_alert(h3_index, report_id, sent)
    log.info(f"Neighbor alert sent to {sent} users for {h3_index}")
    return sent


async def _can_send(h3_index: str) -> bool:
    """True if no alert was sent for this cell in the last RATE_LIMIT_MINUTES."""
    from app.core.database import AsyncSessionLocal
    from app.models.community import NeighborAlertLog
    from sqlalchemy import select

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=RATE_LIMIT_MINUTES)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NeighborAlertLog).where(
                NeighborAlertLog.h3_index == h3_index,
                NeighborAlertLog.sent_at >= cutoff,
            ).limit(1)
        )
        return result.scalar_one_or_none() is None


async def _find_recipients(h3_index: str, neighbor_cells: list[str], exclude_user_id: str) -> list[tuple]:
    """Find users in the cell + neighbors who haven't reported yet and have push enabled."""
    import uuid
    from app.core.database import AsyncSessionLocal
    from app.models.push import PushSubscription
    from app.models.user import User, UserLocation
    from sqlalchemy import select

    target_cells = [h3_index] + neighbor_cells
    exclude_id = uuid.UUID(exclude_user_id)

    async with AsyncSessionLocal() as db:
        # Users with locations in target cells
        loc_result = await db.execute(
            select(UserLocation.user_id).where(
                UserLocation.h3_index.in_(target_cells),
                UserLocation.user_id != exclude_id,
            ).distinct()
        )
        user_ids = [r[0] for r in loc_result.fetchall()]

        if not user_ids:
            return []

        recipients = []
        for uid in user_ids:
            user_result = await db.execute(select(User).where(User.id == uid, User.is_active == True))
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            push_result = await db.execute(
                select(PushSubscription).where(PushSubscription.user_id == uid)
            )
            push_subs = push_result.scalars().all()

            recipients.append((str(uid), user.phone, push_subs, user.language))

    return recipients


async def _send_neighbor_push(push_subs: list, h3_index: str) -> None:
    from app.services.alert_service import send_push_notification
    if push_subs:
        user_id = str(push_subs[0].user_id)
        await send_push_notification(
            user_id=user_id,
            title="Neighbor Outage Report",
            body="Your neighbor just reported a power outage nearby. Is yours out too? Tap to confirm.",
        )


async def _log_alert(h3_index: str, report_id: str, recipients: int) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.community import NeighborAlertLog

    async with AsyncSessionLocal() as db:
        db.add(NeighborAlertLog(
            h3_index=h3_index,
            triggered_by_report_id=report_id,
            recipients_count=recipients,
        ))
        await db.commit()
