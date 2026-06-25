"""Isolation Forest anomaly detection on grid load snapshots."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def detect_anomalies(snapshots: list[dict[str, Any]], contamination: float = 0.1) -> list[dict]:
    """Run Isolation Forest over grid load snapshot dicts.

    Each snapshot should have numeric fields: load_mw, voltage_kv, frequency_hz, etc.
    Returns the same list with an 'is_anomaly' boolean and 'anomaly_score' float added.
    """
    if not snapshots:
        return []

    try:
        from sklearn.ensemble import IsolationForest
        import numpy as np
    except ImportError:
        logger.warning("scikit-learn not installed — skipping anomaly detection")
        for s in snapshots:
            s["is_anomaly"] = False
            s["anomaly_score"] = 0.0
        return snapshots

    feature_keys = ["load_mw", "capacity_mw", "load_pct"]
    X = []
    for snap in snapshots:
        row = [float(snap.get(k) or 0.0) for k in feature_keys]
        X.append(row)

    X_arr = np.array(X)
    model = IsolationForest(contamination=contamination, random_state=42)
    preds = model.fit_predict(X_arr)
    scores = model.score_samples(X_arr)

    for i, snap in enumerate(snapshots):
        snap["is_anomaly"] = bool(preds[i] == -1)
        snap["anomaly_score"] = float(-scores[i])

    return snapshots


def summarize(snapshots: list[dict]) -> dict:
    anomalies = [s for s in snapshots if s.get("is_anomaly")]
    return {
        "total": len(snapshots),
        "anomaly_count": len(anomalies),
        "anomaly_rate": len(anomalies) / len(snapshots) if snapshots else 0.0,
        "anomalies": anomalies,
    }
