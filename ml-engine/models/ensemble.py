"""
Ensemble predictor — combines XGBoost + Prophet into a final outage probability.

Improvements over v0.1:
  - Dynamic weight fallback: if Prophet is not loaded, full weight goes to XGBoost
  - Temperature scaling: adjustable softening of XGBoost probabilities
  - Confidence output: returns both probability and model confidence label
  - Loads v0.3 serialization format (backward-compatible with legacy pickles)
"""
import logging

import numpy as np

from models.xgboost_model import XGBoostOutageModel
from models.prophet_model import ProphetTrendModel

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    XGB_WEIGHT = 0.70
    PROPHET_WEIGHT = 0.30

    # Temperature scaling — values > 1.0 soften extreme probabilities
    TEMPERATURE = 1.05

    def __init__(self, region: str):
        self.region = region
        self.xgb = XGBoostOutageModel(region=region)
        self.prophet = ProphetTrendModel(region=region)
        self._xgb_loaded = False
        self._prophet_loaded = False

    def load(self, xgb_path: str, prophet_path: str) -> None:
        try:
            self.xgb.load(xgb_path)
            self._xgb_loaded = self.xgb._is_fitted
        except Exception as exc:
            logger.warning("XGBoost load failed for %s: %s", self.region, exc)
            self._xgb_loaded = False

        try:
            self.prophet.load(prophet_path)
            self._prophet_loaded = self.prophet._fitted
        except Exception as exc:
            logger.warning("Prophet load failed for %s: %s", self.region, exc)
            self._prophet_loaded = False

    def predict(self, xgb_features: np.ndarray, prophet_features: np.ndarray) -> float:
        """Return combined outage probability in [0, 1]."""
        xgb_prob = 0.0
        prophet_prob = 0.0

        if self._xgb_loaded:
            try:
                raw = float(self.xgb.predict_proba(xgb_features)[0])
                # Temperature scaling
                xgb_prob = float(np.clip(self._temperature_scale(raw), 0.0, 1.0))
            except Exception as exc:
                logger.warning("XGBoost predict failed for %s: %s", self.region, exc)

        if self._prophet_loaded:
            try:
                prophet_prob = float(np.clip(self.prophet.predict_proba(prophet_features)[0], 0.0, 1.0))
            except Exception as exc:
                logger.warning("Prophet predict failed for %s: %s", self.region, exc)

        # Dynamic weighting — if one model is unavailable, use the other fully
        if self._xgb_loaded and self._prophet_loaded:
            combined = self.XGB_WEIGHT * xgb_prob + self.PROPHET_WEIGHT * prophet_prob
        elif self._xgb_loaded:
            combined = xgb_prob
        elif self._prophet_loaded:
            combined = prophet_prob
        else:
            combined = 0.05  # baseline when no model loaded

        return round(float(np.clip(combined, 0.0, 1.0)), 4)

    def predict_with_confidence(
        self, xgb_features: np.ndarray, prophet_features: np.ndarray
    ) -> dict:
        prob = self.predict(xgb_features, prophet_features)
        if self._xgb_loaded and self._prophet_loaded:
            confidence = "high"
            model_version = f"ensemble-{self.region}-v3"
        elif self._xgb_loaded:
            confidence = "medium"
            model_version = f"xgboost-{self.region}-v3"
        elif self._prophet_loaded:
            confidence = "low"
            model_version = f"prophet-{self.region}-v3"
        else:
            confidence = "none"
            model_version = "rule-based-v0"
        return {"probability": prob, "confidence": confidence, "model_version": model_version}

    def _temperature_scale(self, p: float) -> float:
        """Soften extreme probabilities slightly to reduce overconfidence."""
        if self.TEMPERATURE == 1.0 or p <= 0 or p >= 1:
            return p
        import math
        log_odds = math.log(p / (1 - p)) / self.TEMPERATURE
        return 1.0 / (1.0 + math.exp(-log_odds))
