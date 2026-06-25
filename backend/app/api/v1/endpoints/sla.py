import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.uptime import UptimeCheck
from app.models.user import User

router = APIRouter(prefix="/status", tags=["SLA Status"])

_SERVICES = ["api", "ml-engine", "sms-gateway", "database", "redis"]


async def _probe_service(name: str) -> dict:
    start = datetime.now(timezone.utc)
    try:
        if name == "api":
            url = f"{settings.APP_URL}/health"
        elif name == "ml-engine":
            url = f"{settings.ML_ENGINE_URL}/health"
        elif name == "sms-gateway":
            url = f"{settings.SMS_GATEWAY_URL}/health"
        else:
            return {
                "service": name, "status": "unknown",
                "is_healthy": True, "response_ms": None,
            }
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
        ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        healthy = resp.status_code == 200
        return {"service": name, "status": "up" if healthy else "degraded",
                "is_healthy": healthy, "response_ms": ms}
    except Exception:
        ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        return {"service": name, "status": "down", "is_healthy": False, "response_ms": ms}


@router.get("")
async def get_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Live health probe for all services with persistence."""
    results = []
    for svc in _SERVICES:
        probe = await _probe_service(svc)
        check = UptimeCheck(
            id=uuid.uuid4(),
            service=probe["service"],
            status=probe["status"],
            response_ms=probe["response_ms"],
            is_healthy=probe["is_healthy"],
        )
        db.add(check)
        results.append(probe)
    await db.commit()
    overall = all(r["is_healthy"] for r in results)
    return {"overall": "operational" if overall else "degraded", "services": results}


@router.get("/history")
async def get_status_history(
    service: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    q = select(UptimeCheck).order_by(UptimeCheck.checked_at.desc()).limit(limit)
    if service:
        q = q.where(UptimeCheck.service == service)
    rows = await db.execute(q)
    checks = rows.scalars().all()
    return {
        "checks": [
            {
                "id": str(c.id),
                "service": c.service,
                "status": c.status,
                "is_healthy": c.is_healthy,
                "response_ms": c.response_ms,
                "checked_at": c.checked_at.isoformat() if c.checked_at else None,
            }
            for c in checks
        ]
    }
