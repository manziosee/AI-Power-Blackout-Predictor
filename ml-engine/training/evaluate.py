import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from models.xgboost_model import XGBoostOutageModel


def evaluate_model(model: XGBoostOutageModel, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    proba = model.predict_proba(X_test)
    y_pred = (proba >= 0.5).astype(int)

    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4) if len(np.unique(y_test)) > 1 else 0.0,
        "samples": len(y_test),
        "positive_rate": round(float(y_test.mean()), 4),
    }
