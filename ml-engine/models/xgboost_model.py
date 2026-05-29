import pickle

import numpy as np
from xgboost import XGBClassifier

from models.base_model import BaseModel


class XGBoostOutageModel(BaseModel):
    def __init__(self, region: str = "global"):
        self.region = region
        self.version = "0.1"
        self._model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y, eval_set=[(X, y)], verbose=False)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict_proba(X)[:, 1]

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self._model, f)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            self._model = pickle.load(f)

    @property
    def feature_importance(self) -> dict:
        return dict(zip(self._model.feature_names_in_ or [], self._model.feature_importances_))
