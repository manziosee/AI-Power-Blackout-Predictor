"""Celery task — auto-initiate insurance claims for resolved outages."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_LOOK_BACK_HOURS = 24  # process outages resolved in last 24 hours


@celery_app.task(name="app.tasks.auto_claim.auto_initiate_claims_task")
def auto_initiate_claims_task():
    asyncio.run(_run())


async def _run():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.insurance import InsuranceClaim, InsurancePolicy
    from app.models.outage import OutageReport
    from app.services.insurance_service import calculate_payout

    since = datetime.now(timezone.utc) - timedelta(hours=_LOOK_BACK_HOURS)

    async with AsyncSessionLocal() as db:
        resolved = (await db.execute(
            select(OutageReport).where(
                OutageReport.resolved_at.isnot(None),
                OutageReport.verified.is_(True),
                OutageReport.resolved_at >= since,
                OutageReport.duration_minutes.isnot(None),
            )
        )).scalars().all()

        claims_created = 0
        for report in resolved:
            policies = (await db.execute(
                select(InsurancePolicy).where(
                    InsurancePolicy.h3_index == report.h3_index,
                    InsurancePolicy.is_active.is_(True),
                )
            )).scalars().all()

            for policy in policies:
                # Skip if claim already exists for this outage start
                existing = (await db.execute(
                    select(InsuranceClaim).where(
                        InsuranceClaim.policy_id == policy.id,
                        InsuranceClaim.outage_start == report.reported_at,
                    )
                )).scalar_one_or_none()
                if existing:
                    continue

                duration_hours = (report.duration_minutes or 0) / 60.0
                if duration_hours < policy.min_duration_hours:
                    continue

                payout = calculate_payout(policy, duration_hours)
                claim = InsuranceClaim(
                    policy_id=policy.id,
                    h3_index=report.h3_index,
                    outage_start=report.reported_at,
                    outage_end=report.resolved_at,
                    duration_hours=round(duration_hours, 2),
                    payout_usd=round(payout, 2) if payout > 0 else None,
                    status="pending",
                    notes="Auto-initiated from verified outage",
                )
                db.add(claim)
                claims_created += 1

        await db.commit()
        if claims_created:
            logger.info(f"Auto-initiated {claims_created} insurance claims")
