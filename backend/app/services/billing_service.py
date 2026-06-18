"""Stripe billing integration."""
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import SubscriptionPlan, UserSubscription

_PLAN_DEFAULTS = [
    {"name": "free", "display_name": "Free", "price_usd_monthly": 0.0, "price_usd_yearly": 0.0,
     "max_locations": 1, "max_alert_subscriptions": 3, "sms_alerts_per_month": 10},
    {"name": "pro", "display_name": "Pro", "price_usd_monthly": 9.99, "price_usd_yearly": 99.99,
     "max_locations": 5, "max_alert_subscriptions": 20, "sms_alerts_per_month": 100,
     "api_access": True},
    {"name": "business", "display_name": "Business", "price_usd_monthly": 49.0, "price_usd_yearly": 490.0,
     "max_locations": 25, "max_alert_subscriptions": 100, "sms_alerts_per_month": 1000,
     "api_access": True, "webhook_access": True, "data_export": True},
    {"name": "enterprise", "display_name": "Enterprise", "price_usd_monthly": 199.0, "price_usd_yearly": 1990.0,
     "max_locations": -1, "max_alert_subscriptions": -1, "sms_alerts_per_month": -1,
     "api_access": True, "webhook_access": True, "white_label": True, "data_export": True},
]


async def seed_plans(db: AsyncSession) -> None:
    for plan_data in _PLAN_DEFAULTS:
        existing = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name == plan_data["name"]))
        if not existing.scalar_one_or_none():
            db.add(SubscriptionPlan(**plan_data))
    await db.commit()


async def get_or_create_customer(user, db: AsyncSession) -> str | None:
    """Get existing Stripe customer ID or create one."""
    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return None
    try:
        import stripe
        stripe.api_key = secret_key
        sub_result = await db.execute(select(UserSubscription).where(UserSubscription.user_id == user.id))
        user_sub = sub_result.scalar_one_or_none()
        if user_sub and user_sub.stripe_customer_id:
            return user_sub.stripe_customer_id
        customer = stripe.Customer.create(email=user.email, phone=user.phone)
        return customer["id"]
    except Exception:
        return None


async def create_checkout_session(user, plan_name: str, interval: str, db: AsyncSession) -> str | None:
    """Create Stripe checkout session. Returns URL or None if no API key."""
    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return None
    try:
        import stripe
        stripe.api_key = secret_key
        price_env = f"STRIPE_{plan_name.upper()}_{interval.upper()}_PRICE_ID"
        price_id = os.getenv(price_env, "")
        if not price_id:
            return None
        customer_id = await get_or_create_customer(user, db)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=os.getenv("STRIPE_SUCCESS_URL", "http://localhost:5173/billing/success"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "http://localhost:5173/billing/cancel"),
        )
        return session["url"]
    except Exception:
        return None


async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Process Stripe webhook event."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        return {"received": True}
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return {"event_type": event["type"], "id": event["id"]}
    except Exception as e:
        return {"error": str(e)}


async def get_user_plan(user_id, db: AsyncSession) -> dict:
    """Get user's current plan name and limits."""
    result = await db.execute(
        select(UserSubscription, SubscriptionPlan)
        .join(SubscriptionPlan, SubscriptionPlan.id == UserSubscription.plan_id)
        .where(UserSubscription.user_id == user_id)
    )
    row = result.first()
    if not row:
        return {"plan": "free", "sms_per_month": 10, "api_access": False}
    _, plan = row
    return {
        "plan": plan.name,
        "display_name": plan.display_name,
        "sms_per_month": plan.sms_alerts_per_month,
        "max_locations": plan.max_locations,
        "api_access": plan.api_access,
        "webhook_access": plan.webhook_access,
        "white_label": plan.white_label,
        "data_export": plan.data_export,
    }


async def activate_plan_directly(user, plan_name: str, db: AsyncSession) -> UserSubscription:
    """Activate a plan without Stripe — for dev/testing when no API key is set."""
    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name == plan_name))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found")

    existing = await db.execute(select(UserSubscription).where(UserSubscription.user_id == user.id))
    user_sub = existing.scalar_one_or_none()
    if user_sub:
        user_sub.plan_id = plan.id
        user_sub.status = "active"
    else:
        user_sub = UserSubscription(user_id=user.id, plan_id=plan.id, status="active")
        db.add(user_sub)
    await db.flush()
    return user_sub
