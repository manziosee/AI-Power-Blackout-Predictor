import pandas as pd


def normalize_weather(df: pd.DataFrame) -> pd.DataFrame:
    df["rainfall_mm"] = df["rainfall_mm"].clip(0, 500).fillna(0)
    df["temperature_c"] = df["temperature_c"].clip(-60, 60).fillna(20)
    df["wind_speed_ms"] = df["wind_speed_ms"].clip(0, 100).fillna(0)
    df["humidity_pct"] = df["humidity_pct"].clip(0, 100).fillna(50)
    return df


def normalize_outages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["h3_index", "reported_at"])
    df["duration_minutes"] = df["duration_minutes"].clip(0, 1440).fillna(0)
    return df.reset_index(drop=True)
