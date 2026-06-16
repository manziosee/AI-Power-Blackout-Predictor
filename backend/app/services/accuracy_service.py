"""Compute how accurately the model predicted outages for a given cell and period."""
import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

ALERT_THRESHOLD = 0.50   # probability above which we count as a "positive prediction"


async def compute_accuracy(h3_index: str, days: int = 30) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.models.outage import OutageReport
    from app.models.prediction import Prediction
    from sqlalchemy import select

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    async with AsyncSessionLocal() as db:
        # All closed prediction windows in the period
        preds_result = await db.execute(
            select(Prediction).where(
                Prediction.h3_index == h3_index,
                Prediction.window_start >= start,
                Prediction.window_end <= end,
            ).order_by(Prediction.window_start)
        )
        predictions = preds_result.scalars().all()

        if not predictions:
            return _empty_metrics(h3_index, days)

        # Actual outage windows
        outages_result = await db.execute(
            select(OutageReport).where(
                OutageReport.h3_index == h3_index,
                OutageReport.reported_at >= start,
                OutageReport.reported_at <= end,
                OutageReport.verified,
            )
        )
        outages = outages_result.scalars().all()

    tp = fp = tn = fn = 0

    for pred in predictions:
        predicted_positive = pred.probability >= ALERT_THRESHOLD
        # Check if any verified outage falls within this prediction window
        actual_outage = any(
            pred.window_start <= o.reported_at <= pred.window_end
            for o in outages
        )
        if predicted_positive and actual_outage:
            tp += 1
        elif predicted_positive and not actual_outage:
            fp += 1
        elif not predicted_positive and actual_outage:
            fn += 1
        else:
            tn += 1

    total = tp + fp + tn + fn
    accuracy  = round((tp + tn) / total, 4) if total else None
    precision = round(tp / (tp + fp), 4) if (tp + fp) else None
    recall    = round(tp / (tp + fn), 4) if (tp + fn) else None
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision and recall) else None

    return {
        "h3_index": h3_index,
        "period_days": days,
        "total_predictions": total,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "accuracy_pct": round(accuracy * 100, 1) if accuracy else None,
        "grade": _grade(accuracy),
        "verdict": _verdict(accuracy, total),
    }


async def persist_accuracy(h3_index: str, days: int = 30) -> None:
    """Compute and upsert accuracy metrics into prediction_accuracy table."""
    from app.core.database import AsyncSessionLocal
    from app.models.analytics import PredictionAccuracy
    from sqlalchemy import select

    metrics = await compute_accuracy(h3_index, days)

    async with AsyncSessionLocal() as db:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        existing = await db.execute(
            select(PredictionAccuracy).where(
                PredictionAccuracy.h3_index == h3_index,
                PredictionAccuracy.period_start >= start - timedelta(hours=1),
            )
        )
        row = existing.scalar_one_or_none()

        if row:
            row.total_predictions = metrics["total_predictions"]
            row.true_positives = metrics["true_positives"]
            row.false_positives = metrics["false_positives"]
            row.true_negatives = metrics["true_negatives"]
            row.false_negatives = metrics["false_negatives"]
            row.accuracy = metrics["accuracy"]
            row.precision = metrics["precision"]
            row.recall = metrics["recall"]
            row.f1_score = metrics["f1_score"]
            row.computed_at = end
        else:
            db.add(PredictionAccuracy(
                h3_index=h3_index,
                period_start=start,
                period_end=end,
                **{k: metrics[k] for k in [
                    "total_predictions", "true_positives", "false_positives",
                    "true_negatives", "false_negatives", "accuracy",
                    "precision", "recall", "f1_score",
                ]},
            ))
        await db.commit()


def _grade(accuracy: float | None) -> str:
    if accuracy is None:
        return "N/A"
    if accuracy >= 0.90:
        return "A"
    if accuracy >= 0.80:
        return "B"
    if accuracy >= 0.70:
        return "C"
    if accuracy >= 0.60:
        return "D"
    return "F"


def _verdict(accuracy: float | None, total: int) -> str:
    if total < 5:
        return "Not enough data yet"
    if accuracy is None:
        return "No predictions evaluated"
    if accuracy >= 0.85:
        return "Model is performing well in your area"
    if accuracy >= 0.70:
        return "Model has reasonable accuracy — improving with more data"
    return "Model needs more local data to improve accuracy"


def _empty_metrics(h3_index: str, days: int) -> dict:
    return {
        "h3_index": h3_index,
        "period_days": days,
        "total_predictions": 0,
        "true_positives": 0,
        "false_positives": 0,
        "true_negatives": 0,
        "false_negatives": 0,
        "accuracy": None,
        "precision": None,
        "recall": None,
        "f1_score": None,
        "accuracy_pct": None,
        "grade": "N/A",
        "verdict": "No predictions evaluated yet for this area",
    }
