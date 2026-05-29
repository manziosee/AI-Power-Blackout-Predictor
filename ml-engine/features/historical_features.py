import pandas as pd


def build_historical_features(outage_df: pd.DataFrame, h3_index: str) -> dict:
    """Compute historical outage statistics for an H3 cell."""
    cell_data = outage_df[outage_df["h3_index"] == h3_index].copy()

    if cell_data.empty:
        return {
            "outages_last_7d": 0,
            "outages_last_30d": 0,
            "avg_duration_minutes": 0.0,
            "outage_frequency_per_week": 0.0,
            "has_recent_outage": 0,
        }

    now = pd.Timestamp.utcnow()
    last_7d = cell_data[cell_data["reported_at"] >= now - pd.Timedelta(days=7)]
    last_30d = cell_data[cell_data["reported_at"] >= now - pd.Timedelta(days=30)]

    avg_duration = cell_data["duration_minutes"].dropna().mean()
    weeks_span = max((now - cell_data["reported_at"].min()).days / 7, 1)

    return {
        "outages_last_7d": len(last_7d),
        "outages_last_30d": len(last_30d),
        "avg_duration_minutes": round(float(avg_duration) if not pd.isna(avg_duration) else 0.0, 2),
        "outage_frequency_per_week": round(len(cell_data) / weeks_span, 4),
        "has_recent_outage": int(len(last_7d) > 0),
    }
