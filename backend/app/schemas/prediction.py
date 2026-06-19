import uuid
from datetime import datetime

from pydantic import BaseModel


class PredictionOut(BaseModel):
    id: uuid.UUID
    h3_index: str
    predicted_at: datetime
    window_start: datetime
    window_end: datetime
    probability: float
    confidence: float
    risk_level: str
    model_version: str
    region_model: str
    predicted_duration_min: int | None = None
    predicted_duration_median: int | None = None
    predicted_duration_max: int | None = None

    model_config = {"from_attributes": True}


class HeatmapCell(BaseModel):
    h3_index: str
    probability: float
    risk_level: str
    center_lat: float
    center_lng: float
