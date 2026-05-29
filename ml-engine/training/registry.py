import os

from models.prophet_model import ProphetTrendModel
from models.xgboost_model import XGBoostOutageModel

MODEL_STORE = os.path.join(os.path.dirname(__file__), "../model_store")


class ModelRegistry:
    def save(self, region: str, xgb_model: XGBoostOutageModel, prophet_model: ProphetTrendModel) -> None:
        region_dir = os.path.join(MODEL_STORE, region)
        os.makedirs(region_dir, exist_ok=True)
        xgb_model.save(os.path.join(region_dir, "xgboost_v1.pkl"))
        prophet_model.save(os.path.join(region_dir, "prophet_v1.pkl"))

    def load(self, region: str) -> tuple[XGBoostOutageModel, ProphetTrendModel]:
        region_dir = os.path.join(MODEL_STORE, region)
        xgb = XGBoostOutageModel(region=region)
        prophet = ProphetTrendModel(region=region)

        xgb_path = os.path.join(region_dir, "xgboost_v1.pkl")
        prophet_path = os.path.join(region_dir, "prophet_v1.pkl")

        if os.path.exists(xgb_path):
            xgb.load(xgb_path)
        if os.path.exists(prophet_path):
            prophet.load(prophet_path)

        return xgb, prophet

    def list_regions(self) -> list[str]:
        if not os.path.exists(MODEL_STORE):
            return []
        return [d for d in os.listdir(MODEL_STORE) if os.path.isdir(os.path.join(MODEL_STORE, d))]
