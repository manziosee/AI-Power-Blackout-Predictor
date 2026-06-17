import uuid
from datetime import datetime

from pydantic import BaseModel


class PlannedOutageCreate(BaseModel):
    h3_index: str
    title: str
    starts_at: datetime
    ends_at: datetime
    description: str | None = None
    source: str = "manual"


class PlannedOutageStatusUpdate(BaseModel):
    status: str


class PlannedOutageOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    utility_id: uuid.UUID | None
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    source: str
    external_id: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
