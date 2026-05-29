import numpy as np
import pandas as pd


def build_training_dataset(country_codes: list[str]) -> tuple[np.ndarray, np.ndarray, list]:
    """
    Query PostgreSQL for outage + weather data and build feature matrix.
    Returns (X, y, timestamps).
    """
    import os
    import sqlalchemy as sa

    DATABASE_URL = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/blackout_predictor",
    )
    engine = sa.create_engine(DATABASE_URL)

    query = """
        SELECT
            w.h3_index,
            w.recorded_at,
            w.temperature_c,
            w.rainfall_mm,
            w.wind_speed_ms,
            w.humidity_pct,
            w.weather_code,
            h.country_code,
            CASE WHEN o.id IS NOT NULL THEN 1 ELSE 0 END AS had_outage
        FROM weather_snapshots w
        LEFT JOIN h3_cells h ON h.h3_index = w.h3_index
        LEFT JOIN outage_reports o
            ON o.h3_index = w.h3_index
            AND o.reported_at BETWEEN w.recorded_at AND w.recorded_at + INTERVAL '4 hours'
        WHERE h.country_code = ANY(:codes)
        ORDER BY w.recorded_at
    """

    with engine.connect() as conn:
        df = pd.read_sql(sa.text(query), conn, params={"codes": country_codes})

    if df.empty:
        return np.array([]), np.array([]), []

    from features.weather_features import build_weather_features
    from features.temporal_features import build_temporal_features
    from features.historical_features import build_historical_features

    weather_feats = build_weather_features(df)
    temporal_feats = build_temporal_features(df, country_codes[0] if country_codes else "US")

    X = pd.concat([weather_feats, temporal_feats], axis=1).fillna(0).values.astype(np.float32)
    y = df["had_outage"].values.astype(np.int32)
    timestamps = df["recorded_at"].tolist()

    return X, y, timestamps
