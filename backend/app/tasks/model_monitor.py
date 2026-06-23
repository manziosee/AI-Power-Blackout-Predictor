"""Celery task — detect model accuracy drift and export retraining feedback."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_ACCURACY_FLOOR = 0.60
_MIN_PREDICTIONS = 10
_FEEDBACK_DIR = Path("/tmp/retrain_feedback")


@celery_app.task(name="app.tasks.model_monitor.check_model_drift", queue="analytics")
def check_model_drift():
    asyncio.run(_check())


async def _check():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import PredictionAccuracy
    from app.models.outage import OutageReport
    from app.models.prediction import Prediction

    async with AsyncSessionLocal() as db:
        low_accuracy = (await db.execute(
            select(PredictionAccuracy).where(
                PredictionAccuracy.accuracy.isnot(None),
                PredictionAccuracy.accuracy < _ACCURACY_FLOOR,
                PredictionAccuracy.total_predictions >= _MIN_PREDICTIONS,
            ).order_by(PredictionAccuracy.accuracy.asc()).limit(100)
        )).scalars().all()

        if not low_accuracy:
            logger.debug("Model drift check: all cells within acceptable accuracy range")
            return

        drift_cells = [row.h3_index for row in low_accuracy]
        logger.warning(f"Model drift detected in {len(drift_cells)} cells: {drift_cells[:5]}...")

        _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        feedback_file = _FEEDBACK_DIR / f"retrain_feedback_{timestamp}.jsonl"

        records_written = 0
        with feedback_file.open("w") as fout:
            for row in low_accuracy:
                fn_preds = (await db.execute(
                    select(Prediction, OutageReport).join(
                        OutageReport,
                        (OutageReport.h3_index == Prediction.h3_index)
                        & (OutageReport.reported_at >= Prediction.window_start)
                        & (OutageReport.reported_at <= Prediction.window_end),
                        isouter=True,
                    ).where(
                        Prediction.h3_index == row.h3_index,
                        Prediction.probability < 0.50,
                        OutageReport.id.isnot(None),
                    ).limit(50)
                )).fetchall()

                for pred, outage in fn_preds:
                    fout.write(json.dumps({
                        "h3_index": pred.h3_index,
                        "window_start": pred.window_start.isoformat(),
                        "window_end": pred.window_end.isoformat(),
                        "predicted_probability": pred.probability,
                        "actual_outage": True,
                        "label": 1,
                        "accuracy_at_cell": row.accuracy,
                    }) + "\n")
                    records_written += 1

        logger.info(
            f"Drift report: {len(drift_cells)} low-accuracy cells, "
            f"{records_written} false-negative records written to {feedback_file}"
        )


async def get_drift_report(db) -> dict:
    from sqlalchemy import select
    from app.models.analytics import PredictionAccuracy

    rows = (await db.execute(
        select(PredictionAccuracy)
        .where(PredictionAccuracy.total_predictions >= _MIN_PREDICTIONS)
        .order_by(PredictionAccuracy.accuracy.asc())
        .limit(200)
    )).scalars().all()

    critical = [r for r in rows if r.accuracy is not None and r.accuracy < 0.60]
    degraded = [r for r in rows if r.accuracy is not None and 0.60 <= r.accuracy < 0.70]
    healthy = [r for r in rows if r.accuracy is not None and r.accuracy >= 0.70]

    return {
        "critical_cells": len(critical),
        "degraded_cells": len(degraded),
        "healthy_cells": len(healthy),
        "worst": [
            {"h3_index": r.h3_index, "accuracy": r.accuracy, "f1": r.f1_score, "computed_at": r.computed_at.isoformat()}
            for r in critical[:10]
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
