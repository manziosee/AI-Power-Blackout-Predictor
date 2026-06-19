"""
Prediction Celery task.

Runs every 4 hours. For each active H3 cell:
1. Fetches the latest weather snapshot from DB.
2. Builds historical features (outage counts).
3. Calls the ML engine API (/predict/batch) with feature vectors.
4. Falls back to rule-based scoring if ML engine is unavailable.
5. Writes Prediction rows and fires prediction-threshold webhooks.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

ML_ENGINE_URL = "http://ml-engine:8002"
BATCH_SIZE = 200   # cells per ML engine batch call

REGION_MAP = {
    "RW": "africa_east",  "KE": "africa_east",  "UG": "africa_east",  "TZ": "africa_east",
    "ET": "africa_east",  "NG": "africa_west",  "GH": "africa_west",  "SN": "africa_west",
    "CI": "africa_west",  "FR": "europe_central","DE": "europe_central","GB": "europe_central",
    "BE": "europe_central","NL": "europe_central","US": "north_america_east",
    "CA": "north_america_east","BR": "latin_america","CO": "latin_america",
    "AR": "latin_america","MX": "latin_america","IN": "asia_south",
    "PK": "asia_south",   "BD": "asia_south",
}


def _resolve_region(country_code: str | None) -> str:
    return REGION_MAP.get(country_code or "", "global")


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _rule_based(rain: float, wind: float, hour: int, outages_7d: int) -> float:
    p = (
        min(rain / 50.0, 1.0) * 0.35
        + min(wind / 20.0, 1.0) * 0.25
        + (0.15 if hour in (7, 8, 17, 18, 19, 20) else 0.0)
        + min(outages_7d / 5.0, 1.0) * 0.25
    )
    return round(p, 4)


def _classify(p: float) -> str:
    if p >= 0.80:
        return "VERY_HIGH"
    if p >= 0.60:
        return "HIGH"
    if p >= 0.35:
        return "MEDIUM"
    return "LOW"


# ── Celery task ───────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.predict.run_all_predictions")
def run_all_predictions():
    asyncio.run(_run())


async def _run():
    from app.core.database import AsyncSessionLocal
    from app.models.neighborhood import H3Cell
    from app.models.outage import OutageReport
    from app.models.prediction import Prediction
    from app.models.weather import WeatherSnapshot
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        window_start = now
        window_end   = now + timedelta(hours=4)

        # Load all active cells
        cells_res = await db.execute(select(H3Cell).limit(20000))
        cells = cells_res.scalars().all()
        if not cells:
            logger.info("No H3 cells found — skipping prediction run")
            return

        # Fetch latest weather per cell (one query)
        weather_res = await db.execute(
            select(WeatherSnapshot)
            .distinct(WeatherSnapshot.h3_index)
            .order_by(WeatherSnapshot.h3_index, WeatherSnapshot.recorded_at.desc())
        )
        weather_by_cell: dict[str, WeatherSnapshot] = {
            w.h3_index: w for w in weather_res.scalars().all()
        }

        # Fetch 7-day outage counts per cell
        week_ago = now - timedelta(days=7)
        counts_res = await db.execute(
            select(OutageReport.h3_index, func.count(OutageReport.id).label("cnt"))
            .where(OutageReport.reported_at >= week_ago)
            .group_by(OutageReport.h3_index)
        )
        outages_7d: dict[str, int] = {r.h3_index: r.cnt for r in counts_res.all()}

        # Build feature payloads grouped by region
        by_region: dict[str, list[dict]] = {}
        for cell in cells:
            w = weather_by_cell.get(cell.h3_index)
            region = _resolve_region(cell.country_code)
            feature = {
                "h3_index":        cell.h3_index,
                "rainfall_mm":     float(w.rainfall_mm or 0)     if w else 0.0,
                "temperature_c":   float(w.temperature_c or 20)  if w else 20.0,
                "wind_speed_ms":   float(w.wind_speed_ms or 0)   if w else 0.0,
                "humidity_pct":    float(w.humidity_pct or 50)   if w else 50.0,
                "weather_code":    int(w.weather_code or 0)      if w else 0,
                "hour":            now.hour,
                "day_of_week":     now.weekday(),
                "month":           now.month,
                "outages_last_7d": outages_7d.get(cell.h3_index, 0),
                "region_model":    region,
            }
            by_region.setdefault(region, []).append(feature)

        # Call ML engine per region in batches; fallback if unavailable
        results: dict[str, tuple[float, str, str]] = {}  # h3 → (prob, risk, version)
        ml_available = await _check_ml_engine()

        for region, feature_list in by_region.items():
            for i in range(0, len(feature_list), BATCH_SIZE):
                batch = feature_list[i : i + BATCH_SIZE]
                if ml_available:
                    try:
                        async with httpx.AsyncClient(timeout=30) as client:
                            resp = await client.post(
                                f"{ML_ENGINE_URL}/predict/batch",
                                json={"region_model": region, "cells": batch},
                            )
                            resp.raise_for_status()
                            for item in resp.json():
                                results[item["h3_index"]] = (
                                    item["probability"],
                                    item["risk_level"],
                                    item.get("model_version", "ensemble"),
                                )
                        continue
                    except Exception as exc:
                        logger.warning("ML engine batch failed (%s), using rule-based: %s", region, exc)

                # Rule-based fallback
                for feat in batch:
                    p = _rule_based(
                        feat["rainfall_mm"],
                        feat["wind_speed_ms"],
                        feat["hour"],
                        feat["outages_last_7d"],
                    )
                    results[feat["h3_index"]] = (p, _classify(p), "rule-based-v0")

        # Pre-fetch duration estimates (batch async)
        from app.services.duration_service import predict_duration
        duration_cache: dict[str, dict] = {}
        # Only compute for cells with non-trivial risk to avoid N+1 cost
        high_risk_cells = [c for c in cells if results.get(c.h3_index, (0,))[0] >= 0.35]
        for cell in high_risk_cells:
            try:
                dur = await predict_duration(cell.h3_index, cell.country_code)
                duration_cache[cell.h3_index] = dur
            except Exception:
                pass

        # Persist predictions
        for cell in cells:
            prob, risk, version = results.get(cell.h3_index, (0.05, "LOW", "rule-based-v0"))
            dur = duration_cache.get(cell.h3_index)
            db.add(Prediction(
                h3_index=cell.h3_index,
                window_start=window_start,
                window_end=window_end,
                probability=prob,
                confidence=0.75 if "ensemble" in version else 0.50,
                risk_level=risk,
                model_version=version,
                region_model=_resolve_region(cell.country_code),
                predicted_duration_min=dur["min_minutes"] if dur else None,
                predicted_duration_median=dur["median_minutes"] if dur else None,
                predicted_duration_max=dur["max_minutes"] if dur else None,
            ))

        await db.commit()
        logger.info("Prediction run complete — %d cells, ML=%s", len(cells), ml_available)


async def _check_ml_engine() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{ML_ENGINE_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False
