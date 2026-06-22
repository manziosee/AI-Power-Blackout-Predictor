import uuid
from datetime import datetime, time
from typing import List

from pydantic import BaseModel


class AlertSubscriptionCreate(BaseModel):
    h3_index: str
    threshold_probability: float = 0.70
    channels: List[str] = ["sms", "push"]
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    quiet_risk_override: str | None = None  # HIGH / VERY_HIGH / CRITICAL


class AlertSubscriptionOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    threshold_probability: float
    channels: List[str]
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    quiet_risk_override: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class SmsAlertOut(BaseModel):
    id: uuid.UUID
    phone: str
    message: str
    sent_at: datetime
    status: str
    provider: str | None

    model_config = {"from_attributes": True}
