"""Train XGBoost outage probability model on collected outage reports."""
import argparse
import json
import os

import numpy as np
import pandas as pd


def load_training_data(db_url: str) -> pd.DataFrame:
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    query = text("""
        SELECT
            o.h3_index,
            o.reported_at,
            o.duration_minutes,
            o.verified,
            o.weather_condition,
            s.avg_outage_hours_monthly,
            s.reliability_score
        FROM outage_reports o
        LEFT JOIN seasonal_stats s ON s.h3_index = o.h3_index
            AND EXTRACT(month FROM o.reported_at) = s.month
        WHERE o.verified = true
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df["hour"] = pd.to_datetime(df["reported_at"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["reported_at"]).dt.dayofweek
    df["month"] = pd.to_datetime(df["reported_at"]).dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["log_duration"] = np.log1p(df["duration_minutes"].fillna(0))

    weather_map = {"clear": 0, "rain": 1, "storm": 2, "wind": 3, "unknown": 0}
    df["weather_code"] = df["weather_condition"].map(weather_map).fillna(0)

    features = ["hour", "day_of_week", "month", "is_weekend", "log_duration",
                "weather_code", "avg_outage_hours_monthly", "reliability_score"]
    X = df[features].fillna(0)
    y = df["verified"].astype(int)
    return X, y


def train(db_url: str, output_dir: str) -> None:
    from xgboost import XGBClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score

    print("Loading training data...")
    df = load_training_data(db_url)
    if len(df) < 50:
        print(f"Insufficient data ({len(df)} rows). Need ≥50 verified reports.")
        return

    X, y = engineer_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"Test AUC: {auc:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    model.save_model(os.path.join(output_dir, "xgboost_outage.json"))
    meta = {"auc": round(auc, 4), "n_train": len(X_train), "n_test": len(X_test), "features": list(X.columns)}
    with open(os.path.join(output_dir, "xgboost_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Model saved to {output_dir}/xgboost_outage.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection string")
    parser.add_argument("--output-dir", default="models/", help="Directory to save model files")
    args = parser.parse_args()
    train(args.db_url, args.output_dir)
