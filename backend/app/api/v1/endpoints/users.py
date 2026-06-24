import hashlib
import random
import string
import uuid
from datetime import time, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import enforce_auth_rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserLocation
from app.schemas.user import Token, UserCreate, UserLogin, UserOut, UserUpdate

_OTP_TTL_MINUTES = 10


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()

router = APIRouter(prefix="/users", tags=["Auth / Users"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED,
             summary="Register a new user account",
             description="Creates an account via phone number. Returns a JWT Bearer token for subsequent authenticated requests. Rate-limited to 10 attempts/minute per IP.")
async def register(payload: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(_client_ip(request))
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


@router.post("/login", response_model=Token, summary="Authenticate and get a JWT token",
             description="Authenticate with phone + password. Rate-limited to 10 attempts/minute per IP to prevent brute force.")
async def login(payload: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    await enforce_auth_rate_limit(_client_ip(request))
    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut, summary="Get the authenticated user's profile")
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut,
              summary="Update profile",
              description="Update display_name, preferred language, or email. Partial updates — omit fields to leave them unchanged.")
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip() or None
    if payload.language is not None:
        current_user.language = payload.language
    if payload.email is not None:
        # Check email uniqueness
        existing = (await db.execute(
            select(User).where(User.email == payload.email, User.id != current_user.id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = payload.email
    await db.flush()
    return current_user


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Change password",
             description="Requires the current password for verification. New password must be at least 8 characters.")
async def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    await db.flush()


# ── SMS OTP Password Reset ─────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    phone: str


class ResetPasswordRequest(BaseModel):
    phone: str
    otp: str
    new_password: str


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED,
             summary="Request a password-reset OTP via SMS",
             description="Sends a 6-digit OTP to the registered phone number. Valid for 10 minutes. Rate-limited to prevent abuse.")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(_client_ip(request))

    user = (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none()
    # Always return 202 to avoid phone enumeration
    if not user or not user.is_active:
        return {"message": "If that phone number is registered you will receive an OTP."}

    otp = _generate_otp()
    user.otp_code_hash = _hash_otp(otp)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES)
    await db.flush()

    from app.services.alert_service import send_sms_alert
    await send_sms_alert(
        phone=user.phone,
        country_code=user.country_code,
        language=user.language,
        template_key="password_reset_otp",
        template_vars={"otp": otp, "ttl_minutes": _OTP_TTL_MINUTES},
    )

    return {"message": "If that phone number is registered you will receive an OTP."}


@router.post("/reset-password", response_model=Token,
             summary="Reset password using SMS OTP",
             description="Exchange a valid OTP for a new password. The OTP is single-use and expires after 10 minutes.")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(_client_ip(request))

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none()
    if not user or not user.otp_code_hash or not user.otp_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    now = datetime.now(timezone.utc)
    otp_exp = user.otp_expires_at if user.otp_expires_at.tzinfo else user.otp_expires_at.replace(tzinfo=timezone.utc)
    if now > otp_exp:
        raise HTTPException(status_code=400, detail="OTP has expired — request a new one")
    if not _hash_otp(payload.otp) == user.otp_code_hash:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.password_hash = hash_password(payload.new_password)
    user.otp_code_hash = None
    user.otp_expires_at = None
    await db.flush()

    return Token(access_token=create_access_token(str(user.id)))


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


@router.get("/me/locations", response_model=list[LocationOut],
            summary="List the current user's monitored locations")
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


@router.post("/me/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED,
             summary="Add a monitored location",
             description="Adds an H3 cell to the user's monitored locations. Enforces plan-tier limits (Free=1, Pro=5, Business=25, Enterprise=unlimited).")
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
