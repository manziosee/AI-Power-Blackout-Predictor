import uuid
from datetime import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserLocation
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.phone == payload.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone already registered")

    user = User(
        phone=payload.phone,
        country_code=payload.country_code,
        language=payload.language,
        email=payload.email,
        password_hash=hash_password(payload.password) if payload.password else None,
    )
    db.add(user)
    await db.flush()
    return Token(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Locations ──────────────────────────────────────────────────────────────────

_LOCATION_TYPES = {"home", "office", "family", "other"}


class LocationCreate(BaseModel):
    h3_index: str
    label: str | None = None
    is_primary: bool = False
    alert_threshold: float = 0.70
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    notify_channels: list[str] = ["sms", "push"]
    location_type: str | None = None
    display_order: int = 0


class LocationUpdate(BaseModel):
    label: str | None = None
    is_primary: bool | None = None
    is_active: bool | None = None
    alert_threshold: float | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    notify_channels: list[str] | None = None
    location_type: str | None = None
    display_order: int | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    label: str | None
    is_primary: bool
    is_active: bool
    alert_threshold: float
    quiet_hours_start: time | None
    quiet_hours_end: time | None
    notify_channels: list
    location_type: str | None = None
    display_order: int = 0

    model_config = {"from_attributes": True}


@router.get("/me/locations", response_model=list[LocationOut])
async def list_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserLocation)
        .where(UserLocation.user_id == current_user.id)
        .order_by(UserLocation.display_order.asc(), UserLocation.is_primary.desc())
    )
    return result.scalars().all()


async def _get_plan_max_locations(user_id: uuid.UUID, db: AsyncSession) -> int:
    from app.models.billing import SubscriptionPlan, UserSubscription
    sub = (await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
        )
    )).scalar_one_or_none()
    if not sub:
        return 1
    plan = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == sub.plan_id))).scalar_one_or_none()
    return plan.max_locations if plan else 1


@router.post("/me/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def add_location(
    payload: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.location_type and payload.location_type not in _LOCATION_TYPES:
        raise HTTPException(status_code=400, detail=f"location_type must be one of {sorted(_LOCATION_TYPES)}")

    max_locs = await _get_plan_max_locations(current_user.id, db)
    from sqlalchemy import func as sqlfunc
    count = (await db.execute(
        select(sqlfunc.count()).select_from(UserLocation).where(
            UserLocation.user_id == current_user.id, UserLocation.is_active.is_(True)
        )
    )).scalar()
    if count >= max_locs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Location limit reached ({max_locs}). Upgrade your plan to add more locations.",
        )

    if payload.is_primary:
        existing = (await db.execute(
            select(UserLocation).where(UserLocation.user_id == current_user.id, UserLocation.is_primary.is_(True))
        )).scalars().all()
        for loc in existing:
            loc.is_primary = False

    loc = UserLocation(
        user_id=current_user.id,
        h3_index=payload.h3_index,
        label=payload.label,
        is_primary=payload.is_primary,
        alert_threshold=payload.alert_threshold,
        quiet_hours_start=payload.quiet_hours_start,
        quiet_hours_end=payload.quiet_hours_end,
        notify_channels=payload.notify_channels,
        location_type=payload.location_type,
        display_order=payload.display_order,
    )
    db.add(loc)
    await db.flush()
    return loc


@router.patch("/me/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID,
    payload: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserLocation).where(UserLocation.id == location_id, UserLocation.user_id == current_user.id)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if payload.location_type and payload.location_type not in _LOCATION_TYPES:
        raise HTTPException(status_code=400, detail=f"location_type must be one of {sorted(_LOCATION_TYPES)}")

    if payload.is_primary:
        existing = (await db.execute(
            select(UserLocation).where(UserLocation.user_id == current_user.id, UserLocation.is_primary)
        )).scalars().all()
        for other in existing:
            if other.id != location_id:
                other.is_primary = False

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(loc, field, value)

    await db.flush()
    return loc


@router.delete("/me/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserLocation).where(UserLocation.id == location_id, UserLocation.user_id == current_user.id)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.delete(loc)
