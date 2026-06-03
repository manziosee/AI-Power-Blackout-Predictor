from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.fraud_scan.run_fraud_scan")
def run_fraud_scan() -> dict:
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.services.fraud_service import bulk_scan

    async def _run():
        async with AsyncSessionLocal() as db:
            return await bulk_scan(db, since_hours=24)

    flagged = asyncio.run(_run())
    return {"flagged": flagged}
