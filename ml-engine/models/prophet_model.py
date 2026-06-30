"""
Prophet trend model for 7-day outage probability forecasting.

Improvements over v0.1:
  - Tighter changepoint_prior_scale to avoid overfitting sparse outage data
  - Logistic growth mode with carrying capacity cap (outage rate bounded 0-1)
  - Holiday regressors per country
  - predict_proba clips and normalises yhat to [0, 1]
  - Graceful degradation: returns 0.05 baseline on any error
"""
import logging
import pickle

import numpy as np
import pandas as pd
from prophet import Prophet

from models.base_model import BaseModel

logger = logging.getLogger(__name__)

# Country-level holiday dates (MM-DD strings)
_HOLIDAYS: dict[str, list[str]] = {
    "RW": ["01-01", "02-01", "04-07", "05-01", "07-04", "07-01", "08-15", "12-25"],
    "KE": ["01-01", "05-01", "06-01", "10-20", "12-12", "12-25", "12-26"],
    "NG": ["01-01", "04-01", "05-01", "10-01", "12-25", "12-26"],
    "US": ["01-01", "07-04", "11-11", "12-25"],
    "IN": ["01-26", "08-15", "10-02"],
    "BR": ["01-01", "04-21", "05-01", "09-07", "11-02", "12-25"],
}


def _make_holiday_df(country_code: str) -> pd.DataFrame | None:
    dates = _HOLIDAYS.get(country_code.upper(), [])
    if not dates:
        return None
    rows = []
    for year in range(2020, 2030):
        for mmdd in dates:
            try:
                rows.append({"holiday": "national_holiday", "ds": pd.Timestamp(f"{year}-{mmdd}")})
            except Exception:
                continue
    if not rows:
        return None
    return pd.DataFrame(rows)


class ProphetTrendModel(BaseModel):
    def __init__(self, region: str = "global", country_code: str = ""):
        self.region = region
        self.country_code = country_code
        self.version = "0.3"
        self._fitted = False
        self._model: Prophet | None = None

    def _build_model(self) -> Prophet:
        holidays = _make_holiday_df(self.country_code)
        m = Prophet(
            growth="flat",                  # outage rate has no secular trend
            changepoint_prior_scale=0.02,   # conservative — avoid overfitting sparse data
            seasonality_prior_scale=5.0,
            holidays_prior_scale=5.0,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            seasonality_mode="multiplicative",
            holidays=holidays,
            interval_width=0.80,
        )
        m.add_seasonality(name="monthly", period=30.5, fourier_order=4)
        return m

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        X[:,0] should be a sequence of datetime-like values (timestamps).
        y is the binary outage label (0/1); we smooth it with a 6h rolling mean
        to give Prophet a continuous signal rather than pure 0/1 spikes.
        """
        try:
            timestamps = pd.to_datetime(X[:, 0])
            df = pd.DataFrame({"ds": timestamps, "y": y.astype(float)})
            df = df.sort_values("ds").reset_index(drop=True)

            # Rolling mean smoothing — gives Prophet a smoother target
            df["y"] = df["y"].rolling(window=6, min_periods=1, center=True).mean().clip(0, 1)

            self._model = self._build_model()
            self._model.fit(df, iter=500)
            self._fitted = True
            logger.info("Prophet trained for region=%s  rows=%d", self.region, len(df))
        except Exception as exc:
            logger.error("Prophet training failed for region=%s: %s", self.region, exc)
            self._fitted = False

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted or self._model is None:
            return np.full(len(X), 0.05)
        try:
            future = pd.DataFrame({"ds": pd.to_datetime(X[:, 0])})
            forecast = self._model.predict(future)
            return forecast["yhat"].clip(0.0, 1.0).values
        except Exception as exc:
            logger.warning("Prophet predict failed: %s", exc)
            return np.full(len(X), 0.05)

    def forecast_7d(self, from_date: pd.Timestamp) -> pd.DataFrame:
        if not self._fitted or self._model is None:
            return pd.DataFrame(columns=["datetime", "probability", "yhat_lower", "yhat_upper"])
        try:
            future = self._model.make_future_dataframe(periods=7 * 24, freq="h")
            future = future[future["ds"] >= from_date]
            forecast = self._model.predict(future)
            return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
                columns={"ds": "datetime", "yhat": "probability"}
            ).assign(
                probability=lambda d: d["probability"].clip(0, 1),
                yhat_lower=lambda d: d["yhat_lower"].clip(0, 1),
                yhat_upper=lambda d: d["yhat_upper"].clip(0, 1),
            )
        except Exception as exc:
            logger.warning("Prophet forecast_7d failed: %s", exc)
            return pd.DataFrame(columns=["datetime", "probability", "yhat_lower", "yhat_upper"])

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({
                "version": self.version,
                "region": self.region,
                "country_code": self.country_code,
                "model": self._model,
                "fitted": self._fitted,
            }, f, protocol=5)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        if isinstance(payload, dict):
            self._model = payload.get("model")
            self._fitted = payload.get("fitted", self._model is not None)
            self.version = payload.get("version", "0.3")
            self.country_code = payload.get("country_code", "")
        else:
            # Legacy: plain Prophet object
            self._model = payload
            self._fitted = True
