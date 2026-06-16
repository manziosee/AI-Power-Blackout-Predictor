"""
Synthetic training data seeder — development & CI use only.

Generates realistic weather + outage rows in weather_snapshots and outage_reports
so the ML engine has data to train on without needing real history.

Usage:
  python -m data.seeder --cells 500 --days 90
  python -m data.seeder --cells 500 --days 90 --countries RW KE NG

Strategy:
  - For each H3 cell, generate hourly weather snapshots for N days.
  - Outages are triggered probabilistically:
      P(outage) ∝ rainfall + wind_speed + peak_hour + country_base_rate
  - Country base outage rates are calibrated from public data.
"""
import argparse
import logging
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import h3
import sqlalchemy as sa

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/blackout_predictor",
)

# Base hourly outage probability per country (calibrated to real frequencies)
COUNTRY_BASE_RATES = {
    "RW": 0.018, "KE": 0.022, "UG": 0.025, "TZ": 0.020,
    "NG": 0.040, "GH": 0.030, "SN": 0.028,
    "FR": 0.003, "DE": 0.002, "GB": 0.003,
    "US": 0.005, "CA": 0.004,
    "BR": 0.012, "CO": 0.015, "IN": 0.020, "PK": 0.035,
}

# Representative city centers per country
COUNTRY_CENTERS = {
    "RW": (-1.9441, 30.0619), "KE": (-1.2921, 36.8219),
    "UG": (0.3476, 32.5825),  "TZ": (-6.7924, 39.2083),
    "NG": (6.5244, 3.3792),   "GH": (5.5600, -0.2057),
    "SN": (14.7167, -17.4677),"FR": (48.8566, 2.3522),
    "DE": (52.5200, 13.4050), "GB": (51.5074, -0.1278),
    "US": (40.7128, -74.0060),"CA": (43.6532, -79.3832),
    "BR": (-23.5505, -46.6333),"CO": (4.7110, -74.0721),
    "IN": (28.6139, 77.2090), "PK": (31.5497, 74.3436),
}


def _generate_weather_hour(base_temp: float, month: int, hour: int) -> dict:
    """Generate plausible weather for a single hour."""
    # Seasonal + diurnal temperature variation
    seasonal = 3 * math.sin(2 * math.pi * (month - 3) / 12)
    diurnal  = 5 * math.sin(2 * math.pi * (hour - 6) / 24)
    temp = base_temp + seasonal + diurnal + random.gauss(0, 1.5)

    # Random weather event (storm ~5% of hours)
    is_storm = random.random() < 0.05
    rainfall = max(0, random.gauss(25, 10)) if is_storm else max(0, random.gauss(0, 1))
    wind = max(0, random.gauss(18, 5)) if is_storm else max(0, random.gauss(4, 2))

    weather_code = random.choice([200, 201, 202]) if is_storm else random.choice([800, 801, 802, 500])
    humidity = random.randint(60, 95) if is_storm else random.randint(35, 75)

    return {
        "temperature_c": round(temp, 1),
        "rainfall_mm":   round(rainfall, 2),
        "wind_speed_ms": round(wind, 2),
        "humidity_pct":  humidity,
        "weather_code":  weather_code,
    }


def _outage_probability(w: dict, hour: int, base_rate: float) -> float:
    rain_boost = min(w["rainfall_mm"] / 30.0, 1.0) * 0.30
    wind_boost = min(w["wind_speed_ms"] / 20.0, 1.0) * 0.20
    peak_boost = 0.10 if hour in (7, 8, 17, 18, 19, 20) else 0.0
    return min(base_rate + rain_boost + wind_boost + peak_boost, 0.80)


def seed(
    country_codes: list[str],
    n_cells_per_country: int = 50,
    n_days: int = 90,
    resolution: int = 8,
):
    engine = sa.create_engine(DATABASE_URL)

    with engine.begin() as conn:
        # Ensure H3 cells exist for seeded countries
        for cc in country_codes:
            if cc not in COUNTRY_CENTERS:
                logger.warning("No center defined for %s — skipping", cc)
                continue
            lat, lng = COUNTRY_CENTERS[cc]
            base_temp = 25 if cc in ("RW","KE","NG","GH","IN") else 15
            base_rate = COUNTRY_BASE_RATES.get(cc, 0.015)

            # Generate ring of cells around country center
            center_cell = h3.latlng_to_cell(lat, lng, resolution)
            cells = list(h3.grid_disk(center_cell, int(n_cells_per_country ** 0.5)))[:n_cells_per_country]

            # Ensure h3_cells rows exist
            for cell in cells:
                clat, clng = h3.cell_to_latlng(cell)
                conn.execute(sa.text("""
                    INSERT INTO h3_cells (h3_index, center_lat, center_lng, country_code, resolution)
                    VALUES (:h3, :lat, :lng, :cc, :res)
                    ON CONFLICT (h3_index) DO NOTHING
                """), {"h3": cell, "lat": clat, "lng": clng, "cc": cc, "res": resolution})

            # Generate time series
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=n_days)

            weather_rows = []
            outage_rows  = []

            for cell in cells:
                current = start
                last_outage_end = start  # track when outage ended to avoid consecutive duplicates
                while current <= now:
                    w = _generate_weather_hour(base_temp, current.month, current.hour)
                    weather_rows.append({
                        "id":          str(uuid.uuid4()),
                        "h3_index":    cell,
                        "recorded_at": current,
                        "temperature_c": w["temperature_c"],
                        "rainfall_mm":   w["rainfall_mm"],
                        "wind_speed_ms": w["wind_speed_ms"],
                        "humidity_pct":  w["humidity_pct"],
                        "weather_code":  w["weather_code"],
                        "is_forecast":   False,
                    })

                    # Probabilistic outage
                    p = _outage_probability(w, current.hour, base_rate)
                    cooldown_hours = 4  # minimum gap between outages
                    if (random.random() < p and
                            current >= last_outage_end + timedelta(hours=cooldown_hours)):
                        duration = random.randint(30, 240)
                        outage_rows.append({
                            "id":           str(uuid.uuid4()),
                            "h3_index":     cell,
                            "reported_at":  current,
                            "resolved_at":  current + timedelta(minutes=duration),
                            "verified":     True,
                            "verification_count": random.randint(2, 8),
                            "source":       "synthetic",
                        })
                        last_outage_end = current + timedelta(minutes=duration)

                    current += timedelta(hours=1)

            # Bulk insert weather
            if weather_rows:
                conn.execute(sa.text("""
                    INSERT INTO weather_snapshots
                        (id, h3_index, recorded_at, temperature_c, rainfall_mm,
                         wind_speed_ms, humidity_pct, weather_code, is_forecast)
                    VALUES
                        (:id, :h3_index, :recorded_at, :temperature_c, :rainfall_mm,
                         :wind_speed_ms, :humidity_pct, :weather_code, :is_forecast)
                    ON CONFLICT DO NOTHING
                """), weather_rows)

            if outage_rows:
                conn.execute(sa.text("""
                    INSERT INTO outage_reports
                        (id, h3_index, reported_at, resolved_at, verified,
                         verification_count, source)
                    VALUES
                        (:id, :h3_index, :reported_at, :resolved_at, :verified,
                         :verification_count, :source)
                    ON CONFLICT DO NOTHING
                """), outage_rows)

            logger.info(
                "%s: seeded %d weather rows + %d outages across %d cells",
                cc, len(weather_rows), len(outage_rows), len(cells),
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Seed synthetic training data")
    parser.add_argument("--cells",    type=int, default=50,  help="Cells per country")
    parser.add_argument("--days",     type=int, default=90,  help="Days of history")
    parser.add_argument("--countries",nargs="+", default=["RW","KE","NG","GH","FR","US","IN"])
    args = parser.parse_args()

    seed(
        country_codes=args.countries,
        n_cells_per_country=args.cells,
        n_days=args.days,
    )
