import uuid
from datetime import datetime

from pydantic import BaseModel


class OutageReportCreate(BaseModel):
    h3_index: str | None = None
    lat: float | None = None
    lng: float | None = None
    source: str = "app"
    notes: str | None = None


class OutageResolve(BaseModel):
    duration_minutes: int | None = None


class OutageReportOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    reported_at: datetime
    confirmed_at: datetime | None = None
    resolved_at: datetime | None
    duration_minutes: int | None
    source: str
    verified: bool
    verification_count: int

    model_config = {"from_attributes": True}
