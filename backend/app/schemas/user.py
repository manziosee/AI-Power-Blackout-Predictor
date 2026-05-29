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
    email: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


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
