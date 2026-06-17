"""Service for grid topology model."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.grid_topology import GridTransformer, TransformerCellCoverage


async def get_affected_cells(transformer_id: uuid.UUID, db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(TransformerCellCoverage.h3_index).where(
            TransformerCellCoverage.transformer_id == transformer_id
        )
    )
    return [r[0] for r in result.all()]


async def get_transformers_for_cell(h3_index: str, db: AsyncSession) -> list:
    result = await db.execute(
        select(GridTransformer)
        .join(TransformerCellCoverage, TransformerCellCoverage.transformer_id == GridTransformer.id)
        .where(TransformerCellCoverage.h3_index == h3_index)
    )
    return result.scalars().all()


async def propagate_risk_from_failure(transformer_id: uuid.UUID, db: AsyncSession) -> list[str]:
    """Return cells that should have elevated risk due to transformer failure."""
    return await get_affected_cells(transformer_id, db)
