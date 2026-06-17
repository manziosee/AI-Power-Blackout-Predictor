"""Service for white-label utility branding."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import UtilityCompany
from app.models.white_label import WhiteLabelConfig


async def get_brand_for_utility(utility_api_key: str, db: AsyncSession) -> dict | None:
    utility_result = await db.execute(
        select(UtilityCompany).where(UtilityCompany.api_key == utility_api_key)
    )
    utility = utility_result.scalar_one_or_none()
    if not utility:
        return None

    config_result = await db.execute(
        select(WhiteLabelConfig).where(WhiteLabelConfig.utility_id == utility.id)
    )
    config = config_result.scalar_one_or_none()
    if not config or not config.is_active:
        return None

    return {
        "brand_name": config.brand_name,
        "logo_url": config.logo_url,
        "primary_color": config.primary_color,
        "secondary_color": config.secondary_color,
    }


async def get_sms_sender_id(utility_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(WhiteLabelConfig).where(
            WhiteLabelConfig.utility_id == utility_id,
            WhiteLabelConfig.is_active.is_(True),
        )
    )
    config = result.scalar_one_or_none()
    if config and config.sms_sender_id:
        return config.sms_sender_id
    return "PowerAlert"
