"""Service for parametric outage insurance."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance import InsuranceClaim, InsurancePolicy


async def create_policy(
    user_id: uuid.UUID,
    h3_index: str,
    premium: float,
    payout_per_hour: float,
    min_hours: float,
    max_payout: float,
    start_date: datetime,
    db: AsyncSession,
) -> InsurancePolicy:
    policy = InsurancePolicy(
        user_id=user_id,
        h3_index=h3_index,
        premium_usd_monthly=premium,
        payout_usd_per_hour=payout_per_hour,
        min_duration_hours=min_hours,
        max_payout_usd=max_payout,
        start_date=start_date,
    )
    db.add(policy)
    await db.flush()
    return policy


def calculate_payout(policy: InsurancePolicy, duration_hours: float) -> float:
    if duration_hours < policy.min_duration_hours:
        return 0.0
    raw = duration_hours * policy.payout_usd_per_hour
    return min(raw, policy.max_payout_usd)


async def trigger_claims_for_outage(
    h3_index: str,
    outage_start: datetime,
    outage_end: datetime,
    db: AsyncSession,
) -> list[InsuranceClaim]:
    duration_hours = (outage_end - outage_start).total_seconds() / 3600.0

    result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.h3_index == h3_index,
            InsurancePolicy.is_active.is_(True),
        )
    )
    policies = result.scalars().all()

    claims = []
    for policy in policies:
        payout = calculate_payout(policy, duration_hours)
        claim = InsuranceClaim(
            policy_id=policy.id,
            h3_index=h3_index,
            outage_start=outage_start,
            outage_end=outage_end,
            duration_hours=round(duration_hours, 2),
            payout_usd=round(payout, 2) if payout > 0 else None,
            status="approved" if payout > 0 else "rejected",
        )
        db.add(claim)
        claims.append(claim)
    await db.flush()
    return claims
