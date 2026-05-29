import numpy as np

from models.xgboost_model import XGBoostOutageModel
from models.prophet_model import ProphetTrendModel


class EnsemblePredictor:
    """Combines XGBoost (short-term) and Prophet (long-term trend) into a final score."""

    XGB_WEIGHT = 0.70
    PROPHET_WEIGHT = 0.30

    def __init__(self, region: str):
        self.region = region
        self.xgb = XGBoostOutageModel(region=region)
        self.prophet = ProphetTrendModel(region=region)
        self._xgb_loaded = False
        self._prophet_loaded = False

    def load(self, xgb_path: str, prophet_path: str) -> None:
        self.xgb.load(xgb_path)
        self.prophet.load(prophet_path)
        self._xgb_loaded = True
        self._prophet_loaded = True

    def predict(self, xgb_features: np.ndarray, prophet_features: np.ndarray) -> float:
        xgb_prob = float(self.xgb.predict_proba(xgb_features)[0]) if self._xgb_loaded else 0.0
        prophet_prob = float(self.prophet.predict_proba(prophet_features)[0]) if self._prophet_loaded else 0.0

        combined = self.XGB_WEIGHT * xgb_prob + self.PROPHET_WEIGHT * prophet_prob
        return round(float(np.clip(combined, 0.0, 1.0)), 4)
