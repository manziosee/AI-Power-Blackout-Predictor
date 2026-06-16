import pandas as pd


def build_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract weather-related features from raw snapshot data."""
    feats = pd.DataFrame()
    feats["rainfall_mm"] = df["rainfall_mm"].fillna(0.0)
    feats["temperature_c"] = df["temperature_c"].fillna(df["temperature_c"].mean())
    feats["wind_speed_ms"] = df["wind_speed_ms"].fillna(0.0)
    feats["humidity_pct"] = df["humidity_pct"].fillna(50)

    # Derived
    feats["is_heavy_rain"] = (feats["rainfall_mm"] > 20).astype(int)
    feats["is_high_wind"] = (feats["wind_speed_ms"] > 15).astype(int)
    feats["heat_index"] = feats["temperature_c"] * (feats["humidity_pct"] / 100)

    # Weather code groups (OpenWeatherMap)
    feats["is_storm"] = df["weather_code"].between(200, 299).astype(int) if "weather_code" in df else 0
    feats["is_extreme"] = df["weather_code"].between(900, 999).astype(int) if "weather_code" in df else 0

    return feats
