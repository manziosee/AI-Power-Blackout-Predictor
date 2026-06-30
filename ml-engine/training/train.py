"""
Train XGBoost + Prophet models for a given region.

Improvements over v0.1:
  - Stratified 80/20 train/test split (leakage-free)
  - 5-fold stratified cross-validation for XGBoost AUC-PR estimate
  - Full evaluation report saved alongside model weights
  - Minimum sample guard (200 verified samples required)
  - Accepts feature_names from feature_builder and passes to XGBoost
  - Prophet trained on timestamps from training fold only
"""
import argparse
import logging
from datetime import datetime, timezone

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit

from data.processors.feature_builder import build_training_dataset
from models.xgboost_model import XGBoostOutageModel
from models.prophet_model import ProphetTrendModel
from training.evaluate import evaluate_model, cross_val_auc_pr
from training.registry import ModelRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

MIN_SAMPLES = 200  # minimum rows required to train a region


def train_region(region: str, country_codes: list[str]) -> dict | None:
    """
    Train models for one region and save to model_store.
    Returns evaluation dict on success, None on failure.
    """
    logger.info("=== Training region: %s  countries: %s ===", region, country_codes)

    X, y, timestamps, feature_names = build_training_dataset(country_codes=country_codes)

    if len(X) < MIN_SAMPLES:
        logger.warning(
            "Insufficient data for region %s (%d samples, need %d). Skipping.",
            region, len(X), MIN_SAMPLES,
        )
        return None

    # ── Stratified 80/20 split ────────────────────────────────────────────────
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(sss.split(X, y))
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    ts_train = [timestamps[i] for i in train_idx]

    logger.info(
        "Split: train=%d  test=%d  pos_train=%.2f%%  pos_test=%.2f%%",
        len(X_train), len(X_test),
        100 * y_train.mean(), 100 * y_test.mean(),
    )

    # ── XGBoost training ──────────────────────────────────────────────────────
    logger.info("Training XGBoost (region=%s, features=%d)…", region, X_train.shape[1])
    xgb = XGBoostOutageModel(region=region)
    xgb._feature_names = feature_names if len(feature_names) == X_train.shape[1] else xgb._feature_names
    xgb.train(X_train, y_train)

    # ── 5-fold cross-validation AUC-PR ────────────────────────────────────────
    cv_score = cross_val_auc_pr(xgb, X_train, y_train, n_splits=5)
    logger.info("5-fold CV AUC-PR = %.4f", cv_score)

    # ── Test set evaluation ───────────────────────────────────────────────────
    eval_metrics = evaluate_model(xgb, X_test, y_test)
    eval_metrics["cv_auc_pr"] = round(cv_score, 4)
    eval_metrics["region"] = region
    eval_metrics["feature_names"] = feature_names
    eval_metrics["trained_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Test metrics — acc=%.4f  prec=%.4f  rec=%.4f  f1=%.4f  auc=%.4f",
        eval_metrics["accuracy"], eval_metrics["precision"],
        eval_metrics["recall"], eval_metrics["f1"], eval_metrics["roc_auc"],
    )

    # ── Prophet training (on training fold timestamps only) ──────────────────
    logger.info("Training Prophet trend model (region=%s)…", region)
    country_code = country_codes[0] if country_codes else ""
    prophet = ProphetTrendModel(region=region, country_code=country_code)
    prophet_X = np.array(ts_train).reshape(-1, 1)
    prophet.train(prophet_X, y_train)

    # ── Save models + evaluation report ──────────────────────────────────────
    registry = ModelRegistry()
    registry.save(region=region, xgb_model=xgb, prophet_model=prophet, metrics=eval_metrics)
    logger.info("Models saved for region: %s", region)

    return eval_metrics


REGION_COUNTRIES = {
    "africa_east":        ["RW", "KE", "UG", "TZ", "ET"],
    "africa_west":        ["NG", "GH", "SN", "CI"],
    "europe_central":     ["FR", "DE", "GB", "BE", "NL"],
    "north_america_east": ["US", "CA"],
    "latin_america":      ["BR", "CO", "AR", "MX"],
    "asia_south":         ["IN", "PK", "BD"],
    "global":             [],
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train blackout prediction models")
    parser.add_argument("--region", default="all", help="Region key or 'all'")
    parser.add_argument("--min-samples", type=int, default=MIN_SAMPLES,
                        help="Minimum sample count to train a region")
    args = parser.parse_args()

    MIN_SAMPLES = args.min_samples

    regions = list(REGION_COUNTRIES.keys()) if args.region == "all" else [args.region]
    summary = {}
    for region in regions:
        codes = REGION_COUNTRIES.get(region, [])
        result = train_region(region, codes)
        summary[region] = result or {"skipped": True}

    print("\n=== Training Summary ===")
    for r, m in summary.items():
        if m.get("skipped"):
            print(f"  {r}: SKIPPED (insufficient data)")
        else:
            print(
                f"  {r}: acc={m.get('accuracy', 0):.4f}  "
                f"f1={m.get('f1', 0):.4f}  "
                f"auc={m.get('roc_auc', 0):.4f}  "
                f"cv_auc_pr={m.get('cv_auc_pr', 0):.4f}"
            )
