"""
ML Engine unit tests — run without a database.
Tests feature engineering, model training on synthetic data,
ensemble prediction, evaluation metrics, and registry I/O.
"""
import os
import sys
import tempfile

import numpy as np
import pytest  # noqa: F401 — used by pytest.approx and pytest.mark.asyncio

# Add ml-engine root to path so imports work in CI
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from features.weather_features import build_weather_features
from features.temporal_features import build_temporal_features
from models.xgboost_model import XGBoostOutageModel  # noqa: F401
from models.prophet_model import ProphetTrendModel
from models.ensemble import EnsemblePredictor
from training.evaluate import evaluate_model, cross_val_auc_pr
from training.registry import ModelRegistry


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _synthetic_dataset(n: int = 400, positive_rate: float = 0.20):
    """
    Build a synthetic training dataset without hitting the database.
    Features match the 19-dim weather+temporal vector expected by the model.
    """
    rng = np.random.default_rng(42)
    X = rng.random((n, 19)).astype(np.float32)
    # Make positive class loosely correlated with rainfall (feature 0)
    y = (X[:, 0] > (1 - positive_rate)).astype(np.int32)
    return X, y


def _prophet_dataset(n: int = 200):
    """Synthetic timestamps + labels for Prophet."""
    import pandas as pd
    timestamps = pd.date_range("2023-01-01", periods=n, freq="4h")
    rng = np.random.default_rng(7)
    y = (rng.random(n) > 0.80).astype(np.int32)
    return np.array(timestamps).reshape(-1, 1), y


# ── Feature engineering ────────────────────────────────────────────────────────

def test_weather_features_shape():
    import pandas as pd
    df = pd.DataFrame({
        "rainfall_mm":   [10.0, 25.0, 0.0],
        "temperature_c": [22.0, 18.0, 35.0],
        "wind_speed_ms": [5.0, 18.0, 2.0],
        "humidity_pct":  [60.0, 85.0, 40.0],
        "weather_code":  [800, 230, 0],
    })
    feats = build_weather_features(df)
    assert feats.shape == (3, 9)
    assert "is_heavy_rain" in feats.columns
    assert "is_storm" in feats.columns
    assert int(feats.loc[1, "is_heavy_rain"]) == 1   # 25mm > 20
    assert int(feats.loc[1, "is_storm"]) == 1         # code 230 in 200-299


def test_weather_features_handles_missing():
    import pandas as pd
    df = pd.DataFrame({
        "rainfall_mm":   [None],
        "temperature_c": [None],
        "wind_speed_ms": [None],
        "humidity_pct":  [None],
    })
    feats = build_weather_features(df)
    assert feats.shape[0] == 1
    assert feats.isnull().sum().sum() == 0


def test_temporal_features_cyclical_encoding():
    import pandas as pd
    df = pd.DataFrame({"recorded_at": ["2023-06-15 08:00:00", "2023-12-31 23:00:00"]})
    feats = build_temporal_features(df, country_code="RW")
    # Cyclical: hour_sin and hour_cos must be in [-1, 1]
    assert feats["hour_sin"].between(-1, 1).all()
    assert feats["hour_cos"].between(-1, 1).all()
    # Peak hour at 08:00 → is_peak_hour=1
    assert int(feats.loc[0, "is_peak_hour"]) == 1


def test_temporal_features_holiday_flag():
    import pandas as pd
    # 2023-07-04 is Rwanda Liberation Day (07-04 in RW holidays)
    df = pd.DataFrame({"recorded_at": ["2023-07-04 12:00:00", "2023-06-01 12:00:00"]})
    feats = build_temporal_features(df, country_code="RW")
    assert int(feats.loc[0, "is_holiday"]) == 1
    assert int(feats.loc[1, "is_holiday"]) == 0


# ── XGBoost model ─────────────────────────────────────────────────────────────

def test_xgboost_train_predict():
    X, y = _synthetic_dataset(500)
    model = XGBoostOutageModel(region="test")
    model.train(X, y)
    assert model._is_fitted
    proba = model.predict_proba(X[:10])
    assert proba.shape == (10,)
    assert ((proba >= 0) & (proba <= 1)).all()


def test_xgboost_feature_importance_returns_named_keys():
    X, y = _synthetic_dataset(400)
    model = XGBoostOutageModel(region="test")
    model._feature_names = [f"feat_{i}" for i in range(X.shape[1])]
    model.train(X, y)
    fi = model.feature_importance
    assert isinstance(fi, dict)
    assert len(fi) == X.shape[1]
    assert all(isinstance(v, float) for v in fi.values())


def test_xgboost_predict_before_train_returns_baseline():
    model = XGBoostOutageModel(region="test")
    proba = model.predict_proba(np.zeros((3, 19), dtype=np.float32))
    assert (proba == 0.05).all()


def test_xgboost_save_load_roundtrip():
    X, y = _synthetic_dataset(400)
    model = XGBoostOutageModel(region="test")
    model.train(X, y)
    proba_before = model.predict_proba(X[:5])

    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        path = f.name

    try:
        model.save(path)
        loaded = XGBoostOutageModel(region="test")
        loaded.load(path)
        assert loaded._is_fitted
        proba_after = loaded.predict_proba(X[:5])
        np.testing.assert_allclose(proba_before, proba_after, atol=1e-5)
    finally:
        os.unlink(path)


# ── Prophet model ─────────────────────────────────────────────────────────────

def test_prophet_train_predict():
    X, y = _prophet_dataset(300)
    model = ProphetTrendModel(region="test", country_code="RW")
    model.train(X, y)
    assert model._fitted
    proba = model.predict_proba(X[:5])
    assert proba.shape == (5,)
    assert ((proba >= 0) & (proba <= 1)).all()


def test_prophet_predict_before_train_returns_baseline():
    import pandas as pd
    model = ProphetTrendModel(region="test")
    X = np.array(pd.date_range("2024-01-01", periods=3, freq="4h")).reshape(-1, 1)
    proba = model.predict_proba(X)
    assert (proba == 0.05).all()


def test_prophet_save_load_roundtrip():
    X, y = _prophet_dataset(300)
    model = ProphetTrendModel(region="test", country_code="KE")
    model.train(X, y)

    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        path = f.name

    try:
        model.save(path)
        loaded = ProphetTrendModel(region="test")
        loaded.load(path)
        assert loaded._fitted
        assert loaded.country_code == "KE"
    finally:
        os.unlink(path)


# ── Ensemble ──────────────────────────────────────────────────────────────────

def test_ensemble_no_model_returns_baseline():
    ens = EnsemblePredictor(region="test")
    fv = np.zeros((1, 19), dtype=np.float32)
    assert ens.predict(fv, fv) == 0.05


def test_ensemble_xgb_only():
    X, y = _synthetic_dataset(400)
    ens = EnsemblePredictor(region="test")
    ens.xgb.train(X, y)
    ens._xgb_loaded = True
    fv = X[:1]
    prob = ens.predict(fv, fv)
    assert 0.0 <= prob <= 1.0


def test_ensemble_predict_with_confidence_fields():
    ens = EnsemblePredictor(region="test")
    fv = np.zeros((1, 19), dtype=np.float32)
    result = ens.predict_with_confidence(fv, fv)
    assert "probability" in result
    assert "confidence" in result
    assert "model_version" in result
    assert result["confidence"] == "none"
    assert result["probability"] == 0.05


def test_ensemble_full_both_models():
    X_xgb, y = _synthetic_dataset(400)
    X_prophet, _ = _prophet_dataset(400)

    ens = EnsemblePredictor(region="test")
    ens.xgb.train(X_xgb, y)
    ens._xgb_loaded = True
    ens.prophet.train(X_prophet, y)
    ens._prophet_loaded = True

    fv_xgb    = X_xgb[:1]
    fv_prophet = X_prophet[:1]
    result = ens.predict_with_confidence(fv_xgb, fv_prophet)
    assert result["confidence"] == "high"
    assert 0.0 <= result["probability"] <= 1.0


def test_ensemble_temperature_scaling_softens_extremes():
    ens = EnsemblePredictor(region="test")
    ens.TEMPERATURE = 1.5
    # p=0.99 should be softened toward 0.5
    scaled = ens._temperature_scale(0.99)
    assert scaled < 0.99
    assert scaled > 0.5


# ── Evaluation ────────────────────────────────────────────────────────────────

def test_evaluate_model_metrics():
    X, y = _synthetic_dataset(400)
    model = XGBoostOutageModel(region="test")
    model.train(X, y)
    metrics = evaluate_model(model, X, y)
    assert 0 <= metrics["accuracy"] <= 1
    assert 0 <= metrics["f1"] <= 1
    assert 0 <= metrics["roc_auc"] <= 1
    assert 0 <= metrics["auc_pr"] <= 1
    assert 0 <= metrics["brier"] <= 1
    assert metrics["samples"] == len(y)


def test_evaluate_model_empty_returns_zeros():
    model = XGBoostOutageModel(region="test")
    metrics = evaluate_model(model, np.array([]), np.array([]))
    assert metrics["accuracy"] == 0.0
    assert metrics["samples"] == 0


def test_cross_val_auc_pr_returns_float():
    X, y = _synthetic_dataset(600)
    model = XGBoostOutageModel(region="test")
    # No need to pre-train — cross_val_auc_pr trains internally per fold
    score = cross_val_auc_pr(model, X, y, n_splits=3)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


# ── Registry ──────────────────────────────────────────────────────────────────

def test_registry_save_and_load():
    X, y = _synthetic_dataset(400)
    X_p, _ = _prophet_dataset(300)

    xgb = XGBoostOutageModel(region="ci_test")
    xgb.train(X, y)

    prophet = ProphetTrendModel(region="ci_test", country_code="US")
    prophet.train(X_p, y[:300])

    metrics = {"accuracy": 0.85, "f1": 0.72}

    with tempfile.TemporaryDirectory() as tmpdir:
        import training.registry as reg_module
        original = reg_module.MODEL_STORE
        reg_module.MODEL_STORE = tmpdir

        try:
            registry = ModelRegistry()
            registry.save("ci_test", xgb, prophet, metrics)

            loaded_xgb, loaded_prophet = registry.load("ci_test")
            assert loaded_xgb._is_fitted
            assert loaded_prophet._fitted

            meta = registry.get_metadata("ci_test")
            assert meta is not None
            assert meta["region"] == "ci_test"
            assert meta["metrics"]["accuracy"] == 0.85

            regions = registry.list_regions()
            assert "ci_test" in regions
        finally:
            reg_module.MODEL_STORE = original
