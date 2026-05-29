import pickle

import numpy as np
import pandas as pd
from prophet import Prophet

from models.base_model import BaseModel


class ProphetTrendModel(BaseModel):
    """7-day outage trend forecaster per H3 cell using Facebook Prophet."""

    def __init__(self, region: str = "global"):
        self.region = region
        self.version = "0.1"
        self._model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
        )
        self._model.add_seasonality(name="monthly", period=30.5, fourier_order=5)

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        df = pd.DataFrame({"ds": X[:, 0], "y": y.astype(float)})
        self._model.fit(df)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        future = pd.DataFrame({"ds": X[:, 0]})
        forecast = self._model.predict(future)
        raw = forecast["yhat"].clip(0, 1).values
        return raw

    def forecast_7d(self, from_date: pd.Timestamp) -> pd.DataFrame:
        future = self._model.make_future_dataframe(periods=7 * 24, freq="h")
        future = future[future["ds"] >= from_date]
        forecast = self._model.predict(future)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
            columns={"ds": "datetime", "yhat": "probability"}
        )

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self._model, f)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            self._model = pickle.load(f)
