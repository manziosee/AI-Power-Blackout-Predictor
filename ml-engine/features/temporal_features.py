import pandas as pd


_PUBLIC_HOLIDAYS: dict[str, list[str]] = {
    "RW": ["01-01", "02-01", "04-07", "05-01", "07-04", "07-01", "08-15", "12-25"],
    "KE": ["01-01", "05-01", "06-01", "10-20", "12-12", "12-25", "12-26"],
    "US": ["01-01", "07-04", "11-11", "12-25"],
}


def build_temporal_features(df: pd.DataFrame, country_code: str = "US") -> pd.DataFrame:
    """Extract time-based features from a datetime column."""
    dt = pd.to_datetime(df["recorded_at"])
    feats = pd.DataFrame()
    feats["hour"] = dt.dt.hour
    feats["day_of_week"] = dt.dt.dayofweek          # 0=Mon, 6=Sun
    feats["month"] = dt.dt.month
    feats["is_weekend"] = (feats["day_of_week"] >= 5).astype(int)
    feats["is_peak_hour"] = dt.dt.hour.isin([7, 8, 17, 18, 19, 20]).astype(int)
    feats["is_night"] = dt.dt.hour.between(0, 5).astype(int)

    holidays = _PUBLIC_HOLIDAYS.get(country_code, [])
    feats["is_holiday"] = dt.dt.strftime("%m-%d").isin(holidays).astype(int)

    # Cyclical encoding for hour and month (avoids 23→0 discontinuity)
    feats["hour_sin"] = (2 * 3.14159 * feats["hour"] / 24).apply(lambda x: round(float(__import__("math").sin(x)), 6))
    feats["hour_cos"] = (2 * 3.14159 * feats["hour"] / 24).apply(lambda x: round(float(__import__("math").cos(x)), 6))
    feats["month_sin"] = (2 * 3.14159 * feats["month"] / 12).apply(lambda x: round(float(__import__("math").sin(x)), 6))
    feats["month_cos"] = (2 * 3.14159 * feats["month"] / 12).apply(lambda x: round(float(__import__("math").cos(x)), 6))

    return feats
