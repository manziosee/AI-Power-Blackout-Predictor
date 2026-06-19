"""Train XGBoost regressor for outage duration prediction.

Predicts duration_minutes given weather, time, and grid features.
Complements train_xgboost.py (classification) with a separate regression model.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd


def load_data(db_url: str) -> pd.DataFrame:
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    query = text("""
        SELECT
            o.h3_index,
            o.reported_at,
            o.duration_minutes,
            o.source,
            s.avg_outage_hours_monthly,
            s.reliability_score,
            w.rainfall_mm,
            w.temperature_c,
            w.wind_speed_ms,
            w.humidity_pct,
            n.country_code
        FROM outage_reports o
        LEFT JOIN seasonal_stats s ON s.h3_index = o.h3_index
            AND EXTRACT(month FROM o.reported_at) = s.month
        LEFT JOIN (
            SELECT DISTINCT ON (h3_index) h3_index, rainfall_mm, temperature_c, wind_speed_ms, humidity_pct
            FROM weather_snapshots ORDER BY h3_index, recorded_at DESC
        ) w ON w.h3_index = o.h3_index
        LEFT JOIN h3_cells n ON n.h3_index = o.h3_index
        WHERE o.verified = true AND o.duration_minutes IS NOT NULL AND o.duration_minutes > 0
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df["hour"] = pd.to_datetime(df["reported_at"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["reported_at"]).dt.dayofweek
    df["month"] = pd.to_datetime(df["reported_at"]).dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_night"] = df["hour"].between(22, 6).astype(int)

    source_map = {"app": 0, "sms": 1, "ussd": 2, "api": 3}
    df["source_code"] = df["source"].map(source_map).fillna(0)

    features = [
        "hour", "day_of_week", "month", "is_weekend", "is_night", "source_code",
        "rainfall_mm", "temperature_c", "wind_speed_ms", "humidity_pct",
        "avg_outage_hours_monthly", "reliability_score",
    ]
    X = df[features].fillna(0)
    y = np.log1p(df["duration_minutes"])  # log-transform for skewed distribution
    return X, y


def train(db_url: str, output_dir: str) -> None:
    from xgboost import XGBRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error

    print("Loading duration training data...")
    df = load_data(db_url)
    if len(df) < 30:
        print(f"Insufficient data ({len(df)} rows). Need ≥30 verified reports with duration.")
        return

    X, y = engineer_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    y_pred = model.predict(X_test)
    # Convert from log space back to minutes for MAE
    mae_minutes = mean_absolute_error(np.expm1(y_test), np.expm1(y_pred))
    print(f"Test MAE: {mae_minutes:.1f} minutes")

    os.makedirs(output_dir, exist_ok=True)
    model.save_model(os.path.join(output_dir, "xgboost_duration.json"))
    meta = {
        "mae_minutes": round(mae_minutes, 1),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "features": list(X.columns),
        "target": "log1p(duration_minutes)",
    }
    with open(os.path.join(output_dir, "xgboost_duration_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Model saved to {output_dir}/xgboost_duration.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--output-dir", default="models/")
    args = parser.parse_args()
    train(args.db_url, args.output_dir)
