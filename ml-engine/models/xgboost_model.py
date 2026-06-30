"""
XGBoost outage classifier.

Improvements over v0.1:
  - More estimators with early stopping on a held-out eval set
  - Lower learning rate with deeper trees for better generalisation
  - Class-weight balancing via scale_pos_weight (outages are rare events)
  - Probability calibration with CalibratedClassifierCV (isotonic)
  - Feature names stored at fit-time so feature_importance returns named keys
  - Train/eval split handled externally; this class accepts eval_set directly
"""
import pickle
import logging
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier

from models.base_model import BaseModel

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    # Weather (9)
    "rainfall_mm", "temperature_c", "wind_speed_ms", "humidity_pct",
    "is_heavy_rain", "is_high_wind", "heat_index", "is_storm", "is_extreme",
    # Temporal (10)
    "hour", "day_of_week", "month", "is_weekend", "is_peak_hour", "is_night",
    "hour_sin", "hour_cos", "month_sin", "month_cos",
]


class XGBoostOutageModel(BaseModel):
    def __init__(self, region: str = "global"):
        self.region = region
        self.version = "0.3"
        self._feature_names: list[str] = FEATURE_NAMES
        self._calibrated: CalibratedClassifierCV | None = None
        self._raw: XGBClassifier | None = None
        self._is_fitted = False

    def _build_xgb(self, scale_pos_weight: float = 1.0) -> XGBClassifier:
        return XGBClassifier(
            n_estimators=600,
            max_depth=7,
            learning_rate=0.03,
            subsample=0.80,
            colsample_bytree=0.75,
            min_child_weight=5,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.5,
            scale_pos_weight=scale_pos_weight,
            eval_metric="aucpr",       # area under precision-recall — better for imbalanced
            early_stopping_rounds=40,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> None:
        """
        Train with optional validation set for early stopping.
        If no val set is provided, a 15% stratified split is used.
        """
        from sklearn.model_selection import StratifiedShuffleSplit

        # Handle imbalanced classes — outages are rare
        pos = int(y.sum())
        neg = len(y) - pos
        spw = (neg / pos) if pos > 0 else 1.0
        logger.info(
            "Region=%s  samples=%d  positive_rate=%.3f  scale_pos_weight=%.2f",
            self.region, len(y), pos / len(y) if len(y) else 0, spw,
        )

        if X_val is None or y_val is None:
            sss = StratifiedShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
            train_idx, val_idx = next(sss.split(X, y))
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]
        else:
            X_tr, y_tr = X, y

        raw = self._build_xgb(scale_pos_weight=spw)
        raw.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        # Store named features
        raw.feature_names_in_ = np.array(self._feature_names[:X_tr.shape[1]])
        self._raw = raw

        # Isotonic calibration improves probability reliability
        try:
            cal = CalibratedClassifierCV(raw, cv="prefit", method="isotonic")
            cal.fit(X_val, y_val)
            self._calibrated = cal
            logger.info("Calibration fitted for region=%s", self.region)
        except Exception as exc:
            logger.warning("Calibration failed for region=%s: %s — using raw probabilities", self.region, exc)
            self._calibrated = None

        self._is_fitted = True
        logger.info(
            "XGBoost trained for region=%s  best_iteration=%s",
            self.region,
            getattr(raw, "best_iteration", "n/a"),
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._is_fitted or self._raw is None:
            return np.full(len(X), 0.05)
        estimator = self._calibrated if self._calibrated is not None else self._raw
        return estimator.predict_proba(X)[:, 1]

    @property
    def feature_importance(self) -> dict[str, float]:
        if self._raw is None:
            return {}
        names = (
            list(self._raw.feature_names_in_)
            if hasattr(self._raw, "feature_names_in_") and self._raw.feature_names_in_ is not None
            else self._feature_names
        )
        importances = self._raw.feature_importances_
        return {str(n): float(v) for n, v in zip(names, importances)}

    def save(self, path: str) -> None:
        payload: dict[str, Any] = {
            "version": self.version,
            "region": self.region,
            "feature_names": self._feature_names,
            "raw": self._raw,
            "calibrated": self._calibrated,
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f, protocol=5)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        if isinstance(payload, dict):
            self._raw = payload.get("raw")
            self._calibrated = payload.get("calibrated")
            self._feature_names = payload.get("feature_names", FEATURE_NAMES)
            self.version = payload.get("version", "0.3")
        else:
            # Legacy format — plain XGBClassifier pickle
            self._raw = payload
            self._calibrated = None
        self._is_fitted = self._raw is not None
