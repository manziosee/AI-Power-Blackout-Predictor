import uuid
from datetime import datetime
from typing import Any

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
    features_snapshot: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class HeatmapCell(BaseModel):
    h3_index: str
    probability: float
    risk_level: str
    center_lat: float
    center_lng: float


class PredictionAccuracyOut(BaseModel):
    h3_index: str
    period_days: int
    total_predictions: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1_score: float | None
    accuracy_pct: float | None
    grade: str
    verdict: str


class PredictionCompareOut(BaseModel):
    cell_a: PredictionOut | None
    cell_b: PredictionOut | None
    delta_probability: float | None
    higher_risk: str | None  # "a" | "b" | "equal"


class ExplainOut(BaseModel):
    h3_index: str
    prediction_id: str
    probability: float
    risk_level: str
    feature_weights: dict[str, float]
    top_factor: str
    model_version: str
    explanation_method: str
