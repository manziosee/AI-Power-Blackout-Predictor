from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.billing import SubscriptionPlan
from app.models.user import User
from app.services.billing_service import (
    activate_plan_directly,
    create_checkout_session,
    get_user_plan,
    handle_webhook,
    seed_plans,
)

router = APIRouter()


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.price_usd_monthly))
    plans = result.scalars().all()
    if not plans:
        await seed_plans(db)
        result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.price_usd_monthly))
        plans = result.scalars().all()
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "price_monthly": p.price_usd_monthly,
            "price_yearly": p.price_usd_yearly,
            "max_locations": p.max_locations,
            "sms_per_month": p.sms_alerts_per_month,
            "api_access": p.api_access,
            "webhook_access": p.webhook_access,
            "white_label": p.white_label,
            "data_export": p.data_export,
        }
        for p in plans
    ]


class SubscribeRequest(BaseModel):
    plan: str
    interval: str = "monthly"


@router.post("/subscribe")
async def subscribe(
    body: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    url = await create_checkout_session(current_user, body.plan, body.interval, db)
    if url:
        return {"checkout_url": url}
    # No Stripe key — activate directly for dev environments
    user_sub = await activate_plan_directly(current_user, body.plan, db)
    await db.commit()
    return {"activated": True, "plan": body.plan, "status": user_sub.status}


@router.get("/me")
async def get_my_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_user_plan(current_user.id, db)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    result = await handle_webhook(payload, stripe_signature or "")
    return result
