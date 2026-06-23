from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    alerts,
    analytics,
    billing,
    business,
    calendar,
    community,
    data_marketplace,
    dispatch,
    email_alerts,
    feedback,
    gnn,
    grid_load,
    grid_topology,
    incidents,
    insights,
    insurance,
    ivr,
    maintenance,
    medical_priority,
    neighborhoods,
    outages,
    planned_outages,
    poi,
    predictions,
    prepaid,
    public_api,
    push,
    regulatory,
    reports,
    resilience,
    restoration,
    seasonal,
    sms_inbound,
    telegram,
    transfer_learning,
    users,
    ussd,
    utility,
    webhooks,
    white_label,
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
api_router.include_router(planned_outages.router, prefix="/planned-outages", tags=["Planned Outages"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(medical_priority.router, prefix="/medical-priority", tags=["Medical Priority"])
api_router.include_router(resilience.router, prefix="/resilience", tags=["Resilience"])
api_router.include_router(insurance.router, prefix="/insurance", tags=["Insurance"])
api_router.include_router(data_marketplace.router, prefix="/data-marketplace", tags=["Data Marketplace"])
api_router.include_router(white_label.router, prefix="/white-label", tags=["White Label"])
api_router.include_router(ivr.router, prefix="/ivr", tags=["IVR"])
api_router.include_router(poi.router, prefix="/poi", tags=["POI"])
api_router.include_router(prepaid.router, prefix="/prepaid", tags=["Prepaid"])
api_router.include_router(grid_topology.router, prefix="/grid", tags=["Grid Topology"])
api_router.include_router(seasonal.router, prefix="/seasonal", tags=["Seasonal"])
api_router.include_router(transfer_learning.router, prefix="/transfer-learning", tags=["Transfer Learning"])
api_router.include_router(regulatory.router, prefix="/regulatory", tags=["Regulatory"])
api_router.include_router(dispatch.router, prefix="/dispatch", tags=["Dispatch"])
api_router.include_router(grid_load.router, prefix="/grid-load", tags=["Grid Load"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(public_api.router, prefix="/public", tags=["Public API"])
api_router.include_router(gnn.router, prefix="/gnn", tags=["GNN"])
api_router.include_router(restoration.router, prefix="/restoration", tags=["Restoration"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["Maintenance"])
api_router.include_router(incidents.router)
api_router.include_router(calendar.router)
