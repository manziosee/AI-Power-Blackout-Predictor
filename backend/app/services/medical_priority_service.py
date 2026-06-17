"""Service for medical priority registry."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_priority import MedicalPriorityUser
from app.models.user import UserLocation


async def get_priority_users_in_cell(h3_index: str, db: AsyncSession) -> list[dict]:
    """Return medical priority users whose primary location is the given cell."""
    loc_result = await db.execute(
        select(UserLocation.user_id).where(
            UserLocation.h3_index == h3_index, UserLocation.is_active
        )
    )
    user_ids = [r[0] for r in loc_result.all()]
    if not user_ids:
        return []

    result = await db.execute(
        select(MedicalPriorityUser).where(MedicalPriorityUser.user_id.in_(user_ids))
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "user_id": str(u.user_id),
            "condition": u.condition,
            "contact_phone": u.contact_phone,
            "alert_hours_before": u.alert_hours_before,
            "is_verified": u.is_verified,
        }
        for u in users
    ]


async def get_cells_with_priority_users(db: AsyncSession) -> dict[str, int]:
    """Return {h3_index: count} of cells with medical priority users."""
    result = await db.execute(
        select(UserLocation.h3_index, func.count(MedicalPriorityUser.id))
        .join(MedicalPriorityUser, MedicalPriorityUser.user_id == UserLocation.user_id)
        .where(UserLocation.is_active)
        .group_by(UserLocation.h3_index)
    )
    return {row[0]: row[1] for row in result.all()}
