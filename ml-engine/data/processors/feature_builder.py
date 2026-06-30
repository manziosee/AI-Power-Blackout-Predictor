"""
Feature builder for ML training dataset.

Improvements over v0.1:
  - Includes historical outage frequency features (7d, 30d rolling counts)
  - Includes grid type one-hot encoding
  - Deduplicates weather+outage joins (aggregates multiple reports per window)
  - Handles empty DataFrames gracefully
  - Returns feature names alongside arrays
"""
import logging
import os

import numpy as np
import pandas as pd
import sqlalchemy as sa

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/blackout_predictor",
)

# Grid type encoding map — must match grid_features.py
GRID_TYPE_MAP = {
    "RW": "hydro", "UG": "hydro", "ET": "hydro", "KE": "hydro", "BR": "hydro",
    "NG": "gas",   "GH": "gas",   "SN": "gas",   "CI": "gas",
    "ZA": "coal",  "IN": "coal",
    "FR": "nuclear",
    "DE": "mixed", "US": "mixed", "GB": "mixed", "CA": "mixed",
    "PK": "mixed", "BD": "mixed", "CO": "mixed", "AR": "mixed", "MX": "mixed",
}
GRID_TYPES = ["hydro", "coal", "gas", "nuclear", "mixed"]


def build_training_dataset(
    country_codes: list[str],
) -> tuple[np.ndarray, np.ndarray, list, list[str]]:
    """
    Query PostgreSQL for outage + weather data and build feature matrix.

    Returns (X, y, timestamps, feature_names).
    Returns empty arrays (not raises) when data is insufficient.
    """
    if not country_codes:
        logger.warning("build_training_dataset called with empty country_codes")
        return np.array([]), np.array([]), [], []

    try:
        engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True)
    except Exception as exc:
        logger.error("Cannot connect to database: %s", exc)
        return np.array([]), np.array([]), [], []

    query = sa.text("""
        SELECT
            w.h3_index,
            w.recorded_at,
            w.temperature_c,
            COALESCE(w.rainfall_mm, 0.0)   AS rainfall_mm,
            COALESCE(w.wind_speed_ms, 0.0) AS wind_speed_ms,
            COALESCE(w.humidity_pct, 50.0) AS humidity_pct,
            COALESCE(w.weather_code, 0)    AS weather_code,
            h.country_code,
            CASE WHEN COUNT(o.id) > 0 THEN 1 ELSE 0 END AS had_outage
        FROM weather_snapshots w
        INNER JOIN h3_cells h
            ON h.h3_index = w.h3_index
           AND h.country_code = ANY(:codes)
        LEFT JOIN outage_reports o
            ON o.h3_index = w.h3_index
           AND o.reported_at BETWEEN w.recorded_at AND w.recorded_at + INTERVAL '4 hours'
           AND o.verified = TRUE
        GROUP BY w.h3_index, w.recorded_at, w.temperature_c,
                 w.rainfall_mm, w.wind_speed_ms, w.humidity_pct, w.weather_code,
                 h.country_code
        ORDER BY w.recorded_at
    """)

    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"codes": country_codes})
    except Exception as exc:
        logger.error("Database query failed: %s", exc)
        return np.array([]), np.array([]), [], []

    if df.empty:
        logger.warning("No training data found for countries: %s", country_codes)
        return np.array([]), np.array([]), [], []

    logger.info(
        "Raw dataset: %d rows, %d positive (%.2f%%)",
        len(df), int(df["had_outage"].sum()),
        100 * df["had_outage"].mean(),
    )

    from features.weather_features import build_weather_features
    from features.temporal_features import build_temporal_features

    weather_feats = build_weather_features(df)
    temporal_feats = build_temporal_features(
        df, country_codes[0] if country_codes else "US"
    )
    historical_feats = _build_historical_features(df)
    grid_feats = _build_grid_features(df)

    feature_df = pd.concat(
        [weather_feats, temporal_feats, historical_feats, grid_feats], axis=1
    ).fillna(0)

    feature_names = list(feature_df.columns)
    X = feature_df.values.astype(np.float32)
    y = df["had_outage"].values.astype(np.int32)
    timestamps = df["recorded_at"].tolist()

    logger.info(
        "Feature matrix: %d samples × %d features  positive_rate=%.3f",
        X.shape[0], X.shape[1], float(y.mean()),
    )
    return X, y, timestamps, feature_names


def _build_historical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rolling outage counts per h3_index as of each row's timestamp.
    Uses a vectorised approach — one sort + groupby rolling.
    """
    df = df.copy()
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True)

    # Per-cell rolling 7d and 30d outage sums
    df = df.sort_values(["h3_index", "recorded_at"])
    df["outages_7d"] = (
        df.groupby("h3_index", group_keys=False)["had_outage"]
        .apply(lambda s: s.rolling("7D", closed="left").sum())
        .fillna(0)
        .astype(int)
    )
    df["outages_30d"] = (
        df.groupby("h3_index", group_keys=False)["had_outage"]
        .apply(lambda s: s.rolling("30D", closed="left").sum())
        .fillna(0)
        .astype(int)
    )
    df["outage_freq_7d"] = (df["outages_7d"] / 7.0).round(4)

    feats = pd.DataFrame()
    feats["outages_7d"] = df["outages_7d"].values
    feats["outages_30d"] = df["outages_30d"].values
    feats["outage_freq_7d"] = df["outage_freq_7d"].values
    feats["has_recent_outage"] = (df["outages_7d"] > 0).astype(int).values
    return feats


def _build_grid_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode grid type per country."""
    grid_types = df["country_code"].map(GRID_TYPE_MAP).fillna("mixed")
    feats = pd.DataFrame()
    for gt in GRID_TYPES:
        feats[f"grid_{gt}"] = (grid_types == gt).astype(int)
    return feats
