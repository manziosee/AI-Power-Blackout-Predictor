from fastapi import APIRouter

from app.api.v1.endpoints import alerts, neighborhoods, outages, predictions, reports, users

api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(predictions.router)
api_router.include_router(outages.router)
api_router.include_router(alerts.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(reports.router)
