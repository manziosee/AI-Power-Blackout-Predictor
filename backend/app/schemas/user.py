import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    phone: str
    country_code: str
    language: str = "en"
    email: EmailStr | None = None
    password: str | None = None


class UserLogin(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    phone: str
    country_code: str
    language: str
    display_name: str | None = None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: str | None = None
    language: str | None = None
    email: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLocationCreate(BaseModel):
    h3_index: str
    label: str | None = None
    is_primary: bool = False


class UserLocationOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    label: str | None
    is_primary: bool

    model_config = {"from_attributes": True}
