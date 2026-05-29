from abc import ABC, abstractmethod

import numpy as np


class BaseModel(ABC):
    version: str = "0.1"
    region: str = "global"

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability of outage for each row in X."""

    @abstractmethod
    def save(self, path: str) -> None:
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        pass
