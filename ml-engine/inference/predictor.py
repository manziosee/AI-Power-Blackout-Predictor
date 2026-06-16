"""
ML Engine — prediction service.

Startup: loads trained models from model_store/ (if present).
Fallback: rule-based estimate when no trained model exists for a region.

Feature vector (19 features, must match training pipeline):
  weather (9):  rainfall_mm, temperature_c, wind_speed_ms, humidity_pct,
                is_heavy_rain, is_high_wind, heat_index, is_storm, is_extreme
  temporal (10): hour, day_of_week, month, is_weekend, is_peak_hour, is_night,
                 hour_sin, hour_cos, month_sin, month_cos
"""
import logging
import math
import os
from datetime import datetime, timezone

import numpy as np
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from models.ensemble import EnsemblePredictor
from training.registry import ModelRegistry

logger = logging.getLogger(__name__)

app = FastAPI(title="ML Engine — Blackout Predictor", version="1.0.0")

MODEL_STORE = os.path.join(os.path.dirname(__file__), "../model_store")
_registry = ModelRegistry()
_predictors: dict[str, EnsemblePredictor] = {}


# ── Model loader ───────────────────────────────────────────────────────────────

def _get_predictor(region: str) -> EnsemblePredictor:
    if region not in _predictors:
        predictor = EnsemblePredictor(region=region)
        region_dir = os.path.join(MODEL_STORE, region)
        xgb_path = os.path.join(region_dir, "xgboost_v1.pkl")
        prophet_path = os.path.join(region_dir, "prophet_v1.pkl")
        if os.path.exists(xgb_path) and os.path.exists(prophet_path):
            try:
                predictor.load(xgb_path, prophet_path)
                logger.info("Loaded models for region: %s", region)
            except Exception as exc:
                logger.warning("Failed to load models for %s: %s", region, exc)
        else:
            logger.info("No trained model for region %s — using rule-based fallback", region)
        _predictors[region] = predictor
    return _predictors[region]


# Pre-load all regions present in model_store at startup
@app.on_event("startup")
def _preload_models():
    regions = _registry.list_regions()
    logger.info("Pre-loading %d region model(s): %s", len(regions), regions)
    for region in regions:
        _get_predictor(region)


# ── Feature engineering ────────────────────────────────────────────────────────

def _build_feature_vector(f: dict) -> np.ndarray:
    """
    Build the 19-feature vector from raw features dict.
    Matches the feature order produced by feature_builder during training.
    """
    rain   = float(f.get("rainfall_mm", 0))
    temp   = float(f.get("temperature_c", 20))
    wind   = float(f.get("wind_speed_ms", 0))
    hum    = float(f.get("humidity_pct", 50))
    code   = int(f.get("weather_code", 0) or 0)

    # Weather derived
    is_heavy_rain = int(rain > 20)
    is_high_wind  = int(wind > 15)
    heat_index    = temp * (hum / 100)
    is_storm      = int(200 <= code <= 299)
    is_extreme    = int(900 <= code <= 999)

    # Temporal
    now = datetime.now(timezone.utc)
    hour = int(f.get("hour", now.hour))
    dow  = int(f.get("day_of_week", now.weekday()))
    mon  = int(f.get("month", now.month))
    is_weekend   = int(dow >= 5)
    is_peak_hour = int(hour in (7, 8, 17, 18, 19, 20))
    is_night     = int(0 <= hour <= 5)
    hour_sin  = math.sin(2 * math.pi * hour / 24)
    hour_cos  = math.cos(2 * math.pi * hour / 24)
    month_sin = math.sin(2 * math.pi * mon / 12)
    month_cos = math.cos(2 * math.pi * mon / 12)

    return np.array([[
        rain, temp, wind, hum,
        is_heavy_rain, is_high_wind, heat_index, is_storm, is_extreme,
        hour, dow, mon, is_weekend, is_peak_hour, is_night,
        hour_sin, hour_cos, month_sin, month_cos,
    ]], dtype=np.float32)


def _rule_based_probability(f: dict) -> float:
    """Simple deterministic estimate used when no trained model exists."""
    rain   = float(f.get("rainfall_mm", 0))
    wind   = float(f.get("wind_speed_ms", 0))
    hour   = int(f.get("hour", 12))
    history_7d = int(f.get("outages_last_7d", 0))

    rain_score    = min(rain / 50.0, 1.0) * 0.35
    wind_score    = min(wind / 20.0, 1.0) * 0.25
    peak_score    = 0.15 if hour in (7, 8, 17, 18, 19, 20) else 0.0
    history_score = min(history_7d / 5.0, 1.0) * 0.25

    return round(rain_score + wind_score + peak_score + history_score, 4)


def _classify_risk(p: float) -> str:
    if p >= 0.80:
        return "VERY_HIGH"
    if p >= 0.60:
        return "HIGH"
    if p >= 0.35:
        return "MEDIUM"
    return "LOW"


# ── Schemas ────────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    h3_index: str
    features: dict


class PredictResponse(BaseModel):
    h3_index: str
    probability: float
    risk_level: str
    region_model: str
    model_version: str
    used_ml_model: bool


class BatchPredictRequest(BaseModel):
    region_model: str
    cells: list[dict]   # each dict has h3_index + feature keys


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    region = req.features.get("region_model", "global")
    predictor = _get_predictor(region)
    fv = _build_feature_vector(req.features)

    if predictor._xgb_loaded:
        prob = predictor.predict(fv, fv)
        used_ml = True
        version = f"ensemble-{region}-v1"
    else:
        prob = _rule_based_probability(req.features)
        used_ml = False
        version = "rule-based-v0"

    return PredictResponse(
        h3_index=req.h3_index,
        probability=prob,
        risk_level=_classify_risk(prob),
        region_model=region,
        model_version=version,
        used_ml_model=used_ml,
    )


@app.post("/predict/batch")
async def batch_predict(req: BatchPredictRequest):
    predictor = _get_predictor(req.region_model)
    results = []
    for cell in req.cells:
        fv = _build_feature_vector(cell)
        if predictor._xgb_loaded:
            prob = predictor.predict(fv, fv)
            version = f"ensemble-{req.region_model}-v1"
        else:
            prob = _rule_based_probability(cell)
            version = "rule-based-v0"
        results.append({
            "h3_index": cell["h3_index"],
            "probability": prob,
            "risk_level": _classify_risk(prob),
            "model_version": version,
        })
    return results


@app.post("/train/{region}", status_code=202)
async def trigger_training(region: str, background_tasks: BackgroundTasks):
    """Trigger async model training for a region. Returns 202 immediately."""
    background_tasks.add_task(_train_region_bg, region)
    return {"status": "training_started", "region": region}


@app.get("/health")
async def health():
    loaded = {r: _predictors[r]._xgb_loaded for r in _predictors}
    return {
        "status": "ok",
        "regions_loaded": loaded,
        "total_regions": len(_predictors),
    }


# ── Background training ────────────────────────────────────────────────────────

REGION_COUNTRIES = {
    "africa_east":        ["RW", "KE", "UG", "TZ"],
    "africa_west":        ["NG", "GH", "SN", "CI"],
    "europe_central":     ["FR", "DE", "GB", "BE", "NL"],
    "north_america_east": ["US", "CA"],
    "latin_america":      ["BR", "CO", "AR", "MX"],
    "asia_south":         ["IN", "PK", "BD"],
    "global":             [],
}


def _train_region_bg(region: str):
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__) + "/..")
        from training.train import train_region
        country_codes = REGION_COUNTRIES.get(region, [])
        train_region(region, country_codes)
        # Reload after training
        if region in _predictors:
            del _predictors[region]
        _get_predictor(region)
        logger.info("Training completed and model reloaded for region: %s", region)
    except Exception as exc:
        logger.error("Training failed for region %s: %s", region, exc)
