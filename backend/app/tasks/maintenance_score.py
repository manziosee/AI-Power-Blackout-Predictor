"""Weekly Celery task — score all grid transformers by maintenance risk."""
from celery import shared_task


@shared_task(name="tasks.score_transformers")
def score_transformers_task() -> dict:
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.services.maintenance_service import score_all_transformers

    async def _run():
        async with AsyncSessionLocal() as db:
            scored = await score_all_transformers(db)
            await db.commit()
            return {"scored": scored}

    return asyncio.run(_run())
