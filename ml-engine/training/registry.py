"""
Model registry — saves and loads trained models with versioning.

Improvements over v0.1:
  - Saves a metadata.json alongside each model for observability
  - Versioned filenames (xgboost_v{N}.pkl) with symlink to latest
  - Keeps last 3 versions for rollback
  - list_regions() filters out non-model directories
"""
import json
import logging
import os
import shutil
from datetime import datetime, timezone

from models.prophet_model import ProphetTrendModel
from models.xgboost_model import XGBoostOutageModel

logger = logging.getLogger(__name__)

MODEL_STORE = os.path.join(os.path.dirname(__file__), "../model_store")
MAX_VERSIONS = 3


class ModelRegistry:

    def save(
        self,
        region: str,
        xgb_model: XGBoostOutageModel,
        prophet_model: ProphetTrendModel,
        metrics: dict | None = None,
    ) -> None:
        region_dir = os.path.join(MODEL_STORE, region)
        os.makedirs(region_dir, exist_ok=True)

        version = self._next_version(region_dir)

        xgb_path     = os.path.join(region_dir, f"xgboost_v{version}.pkl")
        prophet_path = os.path.join(region_dir, f"prophet_v{version}.pkl")
        meta_path    = os.path.join(region_dir, f"metadata_v{version}.json")

        xgb_model.save(xgb_path)
        prophet_model.save(prophet_path)

        meta = {
            "region": region,
            "version": version,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "xgb_path": xgb_path,
            "prophet_path": prophet_path,
            "metrics": metrics or {},
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Overwrite stable "v1" files so existing loader code keeps working
        shutil.copy2(xgb_path, os.path.join(region_dir, "xgboost_v1.pkl"))
        shutil.copy2(prophet_path, os.path.join(region_dir, "prophet_v1.pkl"))

        # Prune old versions
        self._prune(region_dir, keep=MAX_VERSIONS)

        logger.info(
            "Saved models for region=%s  version=%d  metrics=%s",
            region, version, metrics or {},
        )

    def load(self, region: str) -> tuple[XGBoostOutageModel, ProphetTrendModel]:
        region_dir = os.path.join(MODEL_STORE, region)
        xgb = XGBoostOutageModel(region=region)
        prophet = ProphetTrendModel(region=region)

        xgb_path     = os.path.join(region_dir, "xgboost_v1.pkl")
        prophet_path = os.path.join(region_dir, "prophet_v1.pkl")

        if os.path.exists(xgb_path):
            try:
                xgb.load(xgb_path)
            except Exception as exc:
                logger.error("Failed to load XGBoost for %s: %s", region, exc)

        if os.path.exists(prophet_path):
            try:
                prophet.load(prophet_path)
            except Exception as exc:
                logger.error("Failed to load Prophet for %s: %s", region, exc)

        return xgb, prophet

    def get_metadata(self, region: str) -> dict | None:
        region_dir = os.path.join(MODEL_STORE, region)
        metas = sorted(
            [f for f in os.listdir(region_dir) if f.startswith("metadata_v") and f.endswith(".json")]
        ) if os.path.isdir(region_dir) else []
        if not metas:
            return None
        with open(os.path.join(region_dir, metas[-1])) as f:
            return json.load(f)

    def list_regions(self) -> list[str]:
        if not os.path.exists(MODEL_STORE):
            return []
        return [
            d for d in os.listdir(MODEL_STORE)
            if os.path.isdir(os.path.join(MODEL_STORE, d))
            and not d.startswith(".")
            and os.path.exists(os.path.join(MODEL_STORE, d, "xgboost_v1.pkl"))
        ]

    # ── helpers ───────────────────────────────────────────────────────────────

    def _next_version(self, region_dir: str) -> int:
        existing = [
            f for f in os.listdir(region_dir)
            if f.startswith("xgboost_v") and f.endswith(".pkl")
            and f != "xgboost_v1.pkl"
        ]
        if not existing:
            return 2
        versions = []
        for fname in existing:
            try:
                v = int(fname.replace("xgboost_v", "").replace(".pkl", ""))
                versions.append(v)
            except ValueError:
                pass
        return max(versions, default=1) + 1

    def _prune(self, region_dir: str, keep: int) -> None:
        for prefix in ("xgboost_v", "prophet_v", "metadata_v"):
            files = sorted(
                [
                    f for f in os.listdir(region_dir)
                    if f.startswith(prefix) and f != f"{prefix}1.pkl" and f != f"{prefix}1.json"
                ],
                key=lambda x: int("".join(filter(str.isdigit, x)) or "0"),
            )
            for old in files[:-keep]:
                try:
                    os.remove(os.path.join(region_dir, old))
                    logger.debug("Pruned old model file: %s", old)
                except OSError:
                    pass
