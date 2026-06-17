"""Transfer Learning endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.transfer_learning import RegionSimilarity
from app.models.user import User
from app.services.transfer_learning_service import get_similar_regions, list_regions_with_data

router = APIRouter()


class SimilarityCreate(BaseModel):
    source_region: str
    target_region: str
    similarity_score: float
    basis: str = "climate"
    climate_score: float | None = None
    infrastructure_score: float | None = None


class BootstrapRequest(BaseModel):
    source_region: str


@router.get("/similar/{region}")
async def similar_regions(
    region: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_similar_regions(region, db)


@router.post("/similarity", status_code=201)
async def create_similarity(
    payload: SimilarityCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Upsert
    existing = await db.execute(
        select(RegionSimilarity).where(
            RegionSimilarity.source_region == payload.source_region,
            RegionSimilarity.target_region == payload.target_region,
        )
    )
    sim = existing.scalar_one_or_none()
    if sim is None:
        sim = RegionSimilarity(
            source_region=payload.source_region,
            target_region=payload.target_region,
        )
        db.add(sim)

    sim.similarity_score = payload.similarity_score
    sim.basis = payload.basis
    sim.climate_score = payload.climate_score
    sim.infrastructure_score = payload.infrastructure_score
    sim.computed_at = datetime.utcnow()
    await db.flush()
    await db.commit()
    return {"source_region": sim.source_region, "target_region": sim.target_region, "score": sim.similarity_score}


@router.get("/regions")
async def list_regions(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_regions_with_data(db)


@router.post("/bootstrap/{target_region}")
async def bootstrap_region(
    target_region: str,
    payload: BootstrapRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark a region pair for ML bootstrap — ML engine will pick this up."""
    existing = await db.execute(
        select(RegionSimilarity).where(
            RegionSimilarity.source_region == payload.source_region,
            RegionSimilarity.target_region == target_region,
        )
    )
    sim = existing.scalar_one_or_none()
    if sim is None:
        sim = RegionSimilarity(
            source_region=payload.source_region,
            target_region=target_region,
            similarity_score=0.0,
            basis="bootstrap_pending",
        )
        db.add(sim)
        await db.flush()
        await db.commit()

    return {
        "status": "queued_for_bootstrap",
        "source_region": payload.source_region,
        "target_region": target_region,
    }
