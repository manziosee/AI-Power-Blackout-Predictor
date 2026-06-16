from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    alerts,
    analytics,
    business,
    community,
    email_alerts,
    insights,
    neighborhoods,
    outages,
    predictions,
    push,
    reports,
    sms_inbound,
    telegram,
    users,
    ussd,
    utility,
    webhooks,
    whatsapp,
)

api_router = APIRouter()

api_router.include_router(admin.router)
api_router.include_router(users.router)
api_router.include_router(predictions.router)
api_router.include_router(outages.router)
api_router.include_router(alerts.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(reports.router)
api_router.include_router(push.router)
api_router.include_router(whatsapp.router)
api_router.include_router(telegram.router)
api_router.include_router(email_alerts.router)
api_router.include_router(analytics.router)
api_router.include_router(community.router)
api_router.include_router(utility.router)
api_router.include_router(business.router)
api_router.include_router(webhooks.router)
api_router.include_router(ussd.router)
api_router.include_router(sms_inbound.router)
api_router.include_router(insights.router)
