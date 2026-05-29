from fastapi import FastAPI
from pydantic import BaseModel

from features.grid_features import build_grid_features
from features.historical_features import build_historical_features
from features.temporal_features import build_temporal_features
from features.weather_features import build_weather_features
from models.ensemble import EnsemblePredictor
from training.registry import ModelRegistry

import numpy as np
import pandas as pd

app = FastAPI(title="ML Engine — Blackout Predictor", version="1.0.0")

_registry = ModelRegistry()
_predictors: dict[str, EnsemblePredictor] = {}


def _get_predictor(region: str) -> EnsemblePredictor:
    if region not in _predictors:
        predictor = EnsemblePredictor(region=region)
        xgb, prophet = _registry.load(region)
        _predictors[region] = predictor
    return _predictors[region]


class PredictRequest(BaseModel):
    h3_index: str
    features: dict


class PredictResponse(BaseModel):
    h3_index: str
    probability: float
    risk_level: str
    region_model: str
    model_version: str = "v1.0"


class BatchPredictRequest(BaseModel):
    region_model: str
    cells: list[dict]


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    region = req.features.get("region_model", "global")
    predictor = _get_predictor(region)

    feature_row = np.array([[
        req.features.get("rainfall_mm", 0),
        req.features.get("temperature_c", 20),
        req.features.get("wind_speed_ms", 0),
        req.features.get("humidity_pct", 50),
        req.features.get("hour", 12),
        req.features.get("day_of_week", 0),
        req.features.get("month", 6),
        req.features.get("outages_last_7d", 0),
        req.features.get("outages_last_30d", 0),
        req.features.get("is_holiday", 0),
    ]])

    prob = predictor.predict(feature_row, feature_row)
    risk = _classify_risk(prob)

    return PredictResponse(h3_index=req.h3_index, probability=prob, risk_level=risk, region_model=region)


@app.post("/predict/batch")
async def batch_predict(req: BatchPredictRequest):
    predictor = _get_predictor(req.region_model)
    results = []
    for cell in req.cells:
        feature_row = np.array([[
            cell.get("rainfall_mm", 0),
            cell.get("temperature_c", 20),
            cell.get("wind_speed_ms", 0),
            cell.get("humidity_pct", 50),
            cell.get("hour", 12),
            cell.get("day_of_week", 0),
            cell.get("month", 6),
            cell.get("outages_last_7d", 0),
            cell.get("outages_last_30d", 0),
            cell.get("is_holiday", 0),
        ]])
        prob = predictor.predict(feature_row, feature_row)
        results.append({"h3_index": cell["h3_index"], "probability": prob, "risk_level": _classify_risk(prob)})
    return results


@app.get("/health")
async def health():
    return {"status": "ok", "loaded_regions": list(_predictors.keys())}


def _classify_risk(p: float) -> str:
    if p >= 0.85:
        return "critical"
    if p >= 0.65:
        return "high"
    if p >= 0.40:
        return "medium"
    return "low"
