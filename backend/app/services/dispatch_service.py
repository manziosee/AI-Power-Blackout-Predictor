"""Service for crew dispatch recommendations."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regulatory import DispatchRecommendation


async def generate_recommendations(
    utility_id: uuid.UUID | None,
    crew_count: int,
    db: AsyncSession,
) -> DispatchRecommendation:
    from app.models.medical_priority import MedicalPriorityUser
    from app.models.prediction import Prediction
    from app.models.user import UserLocation

    now = datetime.now(timezone.utc)

    # Fetch high-risk predictions
    pred_query = select(Prediction).where(
        Prediction.probability >= 0.65,
        Prediction.window_end > now,
    ).order_by(Prediction.probability.desc()).limit(50)

    pred_result = await db.execute(pred_query)
    predictions = pred_result.scalars().all()

    # Build cell info with medical priority weighting
    cell_scores: dict[str, dict] = {}
    for pred in predictions:
        h3 = pred.h3_index
        if h3 not in cell_scores:
            # Count medical priority users in this cell
            loc_result = await db.execute(
                select(UserLocation.user_id).where(
                    UserLocation.h3_index == h3, UserLocation.is_active
                )
            )
            user_ids = [r[0] for r in loc_result.all()]
            med_count = 0
            if user_ids:
                med_result = await db.execute(
                    select(MedicalPriorityUser).where(MedicalPriorityUser.user_id.in_(user_ids))
                )
                med_count = len(med_result.scalars().all())

            cell_scores[h3] = {
                "h3_index": h3,
                "probability": pred.probability,
                "medical_priority_count": med_count,
                "priority_score": pred.probability * (1 + med_count * 2),
            }

    # Sort by priority score, take top N for crew positions
    sorted_cells = sorted(cell_scores.values(), key=lambda x: x["priority_score"], reverse=True)
    high_risk_cells = [
        {
            "h3_index": c["h3_index"],
            "probability": c["probability"],
            "medical_priority_count": c["medical_priority_count"],
        }
        for c in sorted_cells[:20]
    ]

    # Suggest crew positions (simplified: one position per crew covering top cells)
    top_cells_for_crew = sorted_cells[: crew_count * 3]
    recommended_positions = []
    chunk_size = max(1, len(top_cells_for_crew) // crew_count) if crew_count else 1
    for i in range(crew_count):
        chunk = top_cells_for_crew[i * chunk_size : (i + 1) * chunk_size]
        covers = [c["h3_index"] for c in chunk]
        if covers:
            recommended_positions.append(
                {
                    "priority": i + 1,
                    "covers_cells": covers,
                    "lat": None,
                    "lng": None,
                }
            )

    total_score = sum(c["priority_score"] for c in sorted_cells[:20]) if sorted_cells else 0.0

    rec = DispatchRecommendation(
        utility_id=utility_id,
        valid_until=now + timedelta(hours=4),
        high_risk_cells=high_risk_cells,
        recommended_positions=recommended_positions,
        crew_count=crew_count,
        total_priority_score=round(total_score, 2),
    )
    db.add(rec)
    await db.flush()
    return rec
