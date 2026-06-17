"""Regulatory Reporting endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.neighborhood import H3Cell
from app.models.outage import OutageReport
from app.models.regulatory import RegulatoryReport
from app.models.user import User
from app.services.regulatory_service import generate_report

router = APIRouter()


class ReportGenerate(BaseModel):
    country_code: str
    district: str | None = None
    year: int
    month: int


class ReportOut(BaseModel):
    id: uuid.UUID
    country_code: str
    district: str | None
    report_year: int
    report_month: int
    total_outages: int
    total_outage_hours: float | None
    uptime_pct: float | None
    affected_cells_count: int
    worst_cell_h3: str | None
    avg_repair_minutes: float | None

    model_config = {"from_attributes": True}


@router.get("/reports", response_model=List[ReportOut])
async def list_reports(
    country_code: str | None = Query(default=None),
    year: int | None = Query(default=None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(RegulatoryReport).order_by(
        RegulatoryReport.report_year.desc(), RegulatoryReport.report_month.desc()
    )
    if country_code:
        query = query.where(RegulatoryReport.country_code == country_code)
    if year:
        query = query.where(RegulatoryReport.report_year == year)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report_by_id(
    report_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RegulatoryReport).where(RegulatoryReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/reports/generate", response_model=ReportOut)
async def generate_regulatory_report(
    payload: ReportGenerate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    report = await generate_report(
        country_code=payload.country_code,
        district=payload.district,
        year=payload.year,
        month=payload.month,
        db=db,
    )
    await db.commit()
    return report


@router.get("/districts/{country_code}")
async def list_districts(
    country_code: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(H3Cell.region, func.count(OutageReport.id).label("outage_count"))
        .join(OutageReport, OutageReport.h3_index == H3Cell.h3_index, isouter=True)
        .where(H3Cell.country_code == country_code, H3Cell.region.is_not(None))
        .group_by(H3Cell.region)
        .order_by(func.count(OutageReport.id).desc())
    )
    return [{"district": row.region, "outage_count": int(row.outage_count or 0)} for row in result.all()]
