from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserLocation
from app.schemas.user import Token, UserCreate, UserLocationCreate, UserLocationOut, UserLogin, UserOut

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


@router.post("/me/locations", response_model=UserLocationOut, status_code=status.HTTP_201_CREATED)
async def add_location(
    payload: UserLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    loc = UserLocation(user_id=current_user.id, **payload.model_dump())
    db.add(loc)
    await db.flush()
    return loc


@router.get("/me/locations", response_model=list[UserLocationOut])
async def list_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserLocation).where(UserLocation.user_id == current_user.id))
    return result.scalars().all()
