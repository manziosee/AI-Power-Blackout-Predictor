"""Celery task — periodic grid load data fetch."""
from celery import shared_task


@shared_task(name="tasks.fetch_grid_load")
def fetch_grid_load(region: str, source: str = "eia") -> dict:
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.services.grid_load_service import fetch_eia_load, fetch_entso_e_load

    async def _run():
        async with AsyncSessionLocal() as db:
            if source == "eia":
                snap = await fetch_eia_load(region, db)
            else:
                snap = await fetch_entso_e_load(region, db)
            await db.commit()
            if snap:
                return {"region": snap.region, "load_mw": snap.load_mw, "source": snap.source}
            return {"region": region, "fetched": False}

    return asyncio.run(_run())
