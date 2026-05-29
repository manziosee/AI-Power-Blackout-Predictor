import pandas as pd


def clean_outage_reports(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["h3_index", "reported_at"])
    df = df[df["verification_count"] >= 1]
    df["reported_at"] = pd.to_datetime(df["reported_at"], utc=True)
    df["duration_minutes"] = df["duration_minutes"].clip(0, 1440)   # max 24h
    return df.reset_index(drop=True)


def clean_weather_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["h3_index", "recorded_at"])
    df["rainfall_mm"] = df["rainfall_mm"].clip(0, 500)
    df["temperature_c"] = df["temperature_c"].clip(-60, 60)
    df["wind_speed_ms"] = df["wind_speed_ms"].clip(0, 100)
    df["humidity_pct"] = df["humidity_pct"].clip(0, 100)
    return df.reset_index(drop=True)
