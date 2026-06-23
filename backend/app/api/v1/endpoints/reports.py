"""Public outage report endpoint — accepts SMS/USSD reports without auth."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.outage import OutageReport
from app.schemas.outage import OutageReportCreate, OutageReportOut
from app.services.outage_service import resolve_h3_from_coords

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/public", response_model=OutageReportOut, status_code=201)
async def public_report(payload: OutageReportCreate, db: AsyncSession = Depends(get_db)):
    """Accepts unauthenticated outage reports from SMS/USSD callbacks."""
    h3_index = payload.h3_index
    if not h3_index and payload.lat and payload.lng:
        h3_index = resolve_h3_from_coords(payload.lat, payload.lng)

    report = OutageReport(
        h3_index=h3_index or "unknown",
        lat=payload.lat,
        lng=payload.lng,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(report)
    await db.flush()
    return report
