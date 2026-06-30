"""
Model evaluation utilities.

Improvements over v0.1:
  - Added cross_val_auc_pr for stratified k-fold AUC-PR estimation
  - Added average_precision_score (AUC-PR) to evaluate_model output
  - Uses zero_division=0 on all classification metrics
  - Handles edge cases (no positives in fold) gracefully
"""
import logging

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold

from models.xgboost_model import XGBoostOutageModel

logger = logging.getLogger(__name__)


def evaluate_model(model: XGBoostOutageModel, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """Full evaluation on a held-out test set."""
    if len(X_test) == 0:
        return _empty_metrics()

    proba = model.predict_proba(X_test)
    y_pred = (proba >= 0.5).astype(int)

    metrics = {
        "accuracy":  round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1":        round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "brier":     round(float(brier_score_loss(y_test, proba)), 4),
        "samples":   int(len(y_test)),
        "positive_rate": round(float(y_test.mean()), 4),
    }

    if len(np.unique(y_test)) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_test, proba)), 4)
        metrics["auc_pr"]  = round(float(average_precision_score(y_test, proba)), 4)
    else:
        metrics["roc_auc"] = 0.0
        metrics["auc_pr"]  = 0.0

    return metrics


def cross_val_auc_pr(
    model: XGBoostOutageModel,
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = 5,
) -> float:
    """
    Stratified k-fold AUC-PR estimate.
    A fresh XGBoostOutageModel is trained on each fold to avoid data leakage.
    Returns mean AUC-PR across folds (0.0 on error).
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores: list[float] = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        if len(np.unique(y_val)) < 2:
            logger.debug("Fold %d skipped — no positives in val set", fold)
            continue

        try:
            fold_model = XGBoostOutageModel(region=model.region)
            fold_model._feature_names = model._feature_names
            fold_model.train(X_tr, y_tr, X_val, y_val)
            proba = fold_model.predict_proba(X_val)
            score = float(average_precision_score(y_val, proba))
            scores.append(score)
            logger.debug("Fold %d  AUC-PR=%.4f", fold, score)
        except Exception as exc:
            logger.warning("Cross-val fold %d failed: %s", fold, exc)

    if not scores:
        return 0.0
    mean_score = float(np.mean(scores))
    std_score  = float(np.std(scores))
    logger.info(
        "CV AUC-PR: %.4f ± %.4f  (n_folds=%d)",
        mean_score, std_score, len(scores),
    )
    return mean_score


def _empty_metrics() -> dict:
    return {
        "accuracy": 0.0, "precision": 0.0, "recall": 0.0,
        "f1": 0.0, "brier": 1.0, "roc_auc": 0.0, "auc_pr": 0.0,
        "samples": 0, "positive_rate": 0.0,
    }
