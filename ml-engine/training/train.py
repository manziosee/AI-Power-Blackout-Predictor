"""Train XGBoost + Prophet models for a given region."""
import argparse
import logging

import numpy as np

from data.processors.feature_builder import build_training_dataset
from models.xgboost_model import XGBoostOutageModel
from models.prophet_model import ProphetTrendModel
from training.registry import ModelRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_region(region: str, country_codes: list[str]) -> None:
    logger.info(f"Building training dataset for region: {region}")
    X, y, timestamps = build_training_dataset(country_codes=country_codes)

    if len(X) < 100:
        logger.warning(f"Insufficient data for region {region} ({len(X)} samples). Skipping.")
        return

    logger.info(f"Training XGBoost on {len(X)} samples")
    xgb = XGBoostOutageModel(region=region)
    xgb.train(X, y)

    logger.info("Training Prophet trend model")
    prophet = ProphetTrendModel(region=region)
    prophet_X = np.array(timestamps).reshape(-1, 1)
    prophet.train(prophet_X, y)

    registry = ModelRegistry()
    registry.save(region=region, xgb_model=xgb, prophet_model=prophet)
    logger.info(f"Models saved for region: {region}")


REGION_COUNTRIES = {
    "africa_east": ["RW", "KE", "UG", "TZ"],
    "africa_west": ["NG", "GH", "SN", "CI"],
    "europe_central": ["FR", "DE", "GB", "BE", "NL"],
    "north_america_east": ["US", "CA"],
    "latin_america": ["BR", "CO", "AR", "MX"],
    "asia_south": ["IN", "PK", "BD"],
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="all", help="Region to train or 'all'")
    args = parser.parse_args()

    regions = REGION_COUNTRIES.keys() if args.region == "all" else [args.region]
    for region in regions:
        train_region(region, REGION_COUNTRIES.get(region, []))
