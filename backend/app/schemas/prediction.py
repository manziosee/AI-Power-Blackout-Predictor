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

    model_config = {"from_attributes": True}


class HeatmapCell(BaseModel):
    h3_index: str
    probability: float
    risk_level: str
    center_lat: float
    center_lng: float
