"""White-Label for Utilities endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.user import User
from app.models.white_label import WhiteLabelConfig
from app.services.white_label_service import get_brand_for_utility

router = APIRouter()


class WhiteLabelCreate(BaseModel):
    utility_id: uuid.UUID
    brand_name: str
    logo_url: str | None = None
    primary_color: str = "#2563EB"
    secondary_color: str = "#1E40AF"
    sms_sender_id: str | None = None
    email_from_name: str | None = None
    email_from_address: str | None = None
    custom_domain: str | None = None
    support_phone: str | None = None
    support_email: str | None = None


class WhiteLabelUpdate(BaseModel):
    brand_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    sms_sender_id: str | None = None
    email_from_name: str | None = None
    email_from_address: str | None = None
    custom_domain: str | None = None
    support_phone: str | None = None
    support_email: str | None = None
    is_active: bool | None = None


class WhiteLabelOut(BaseModel):
    id: uuid.UUID
    utility_id: uuid.UUID
    brand_name: str
    logo_url: str | None
    primary_color: str
    secondary_color: str
    sms_sender_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/", response_model=WhiteLabelOut, status_code=201)
async def create_config(
    payload: WhiteLabelCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(WhiteLabelConfig).where(WhiteLabelConfig.utility_id == payload.utility_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Config already exists for this utility")

    config = WhiteLabelConfig(**payload.model_dump())
    db.add(config)
    await db.flush()
    await db.commit()
    return config


@router.get("/", response_model=List[WhiteLabelOut])
async def list_configs(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WhiteLabelConfig))
    return result.scalars().all()


@router.get("/{utility_id}", response_model=WhiteLabelOut)
async def get_config(
    utility_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WhiteLabelConfig).where(WhiteLabelConfig.utility_id == utility_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.put("/{utility_id}", response_model=WhiteLabelOut)
async def update_config(
    utility_id: uuid.UUID,
    payload: WhiteLabelUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WhiteLabelConfig).where(WhiteLabelConfig.utility_id == utility_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    await db.flush()
    await db.commit()
    return config


@router.get("/brand/{utility_api_key}")
async def get_brand(
    utility_api_key: str,
    db: AsyncSession = Depends(get_db),
):
    brand = await get_brand_for_utility(utility_api_key, db)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand
