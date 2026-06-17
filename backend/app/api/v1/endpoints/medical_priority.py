"""Medical Priority Registry endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.medical_priority import MedicalPriorityUser
from app.models.user import User
from app.services.medical_priority_service import get_cells_with_priority_users

router = APIRouter()


class MedicalPriorityCreate(BaseModel):
    condition: str
    contact_phone: str | None = None
    alert_hours_before: int = 6
    notes: str | None = None


class MedicalPriorityUpdate(BaseModel):
    condition: str | None = None
    contact_phone: str | None = None
    alert_hours_before: int | None = None
    notes: str | None = None


class MedicalPriorityOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    condition: str
    contact_phone: str | None
    alert_hours_before: int
    notes: str | None
    is_verified: bool

    model_config = {"from_attributes": True}


@router.post("/register", response_model=MedicalPriorityOut, status_code=201)
async def register(
    payload: MedicalPriorityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(MedicalPriorityUser).where(MedicalPriorityUser.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered")

    entry = MedicalPriorityUser(
        user_id=current_user.id,
        condition=payload.condition,
        contact_phone=payload.contact_phone,
        alert_hours_before=payload.alert_hours_before,
        notes=payload.notes,
    )
    db.add(entry)
    await db.flush()
    return entry


@router.get("/my-profile", response_model=MedicalPriorityOut)
async def my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalPriorityUser).where(MedicalPriorityUser.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not registered")
    return entry


@router.put("/my-profile", response_model=MedicalPriorityOut)
async def update_profile(
    payload: MedicalPriorityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalPriorityUser).where(MedicalPriorityUser.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not registered")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    await db.flush()
    return entry


@router.delete("/my-profile", status_code=204)
async def unregister(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalPriorityUser).where(MedicalPriorityUser.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not registered")
    await db.delete(entry)
    await db.flush()


@router.get("/heatmap")
async def heatmap(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_cells_with_priority_users(db)


@router.put("/{entry_id}/verify", response_model=MedicalPriorityOut)
async def verify_entry(
    entry_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalPriorityUser).where(MedicalPriorityUser.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.is_verified = True
    await db.flush()
    return entry
