import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.fraud import FraudFlag
from app.models.user import User
from app.services.admin_service import (
    get_accuracy_by_country,
    get_celery_health,
    get_platform_stats,
    get_smpp_connectors,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Platform stats ─────────────────────────────────────────────────────────────

@router.get("/stats")
async def platform_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_platform_stats(db)


# ── Prediction accuracy by country ────────────────────────────────────────────

@router.get("/accuracy")
async def accuracy_by_country(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_accuracy_by_country(db)


# ── SMPP connector health ──────────────────────────────────────────────────────

@router.get("/smpp-status")
async def smpp_status(_admin: User = Depends(require_admin)):
    return {"connectors": get_smpp_connectors()}


# ── Celery worker health ───────────────────────────────────────────────────────

@router.get("/celery-health")
async def celery_health(_admin: User = Depends(require_admin)):
    return get_celery_health()


# ── Fraud flags ────────────────────────────────────────────────────────────────

@router.get("/fraud/flags")
async def list_fraud_flags(
    resolved: bool = False,
    limit: int = 50,
    offset: int = 0,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(FraudFlag).where(FraudFlag.resolved == resolved).order_by(FraudFlag.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return rows


class ResolveFlagBody(BaseModel):
    note: str | None = None


@router.patch("/fraud/flags/{flag_id}")
async def resolve_flag(
    flag_id: uuid.UUID,
    body: ResolveFlagBody,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(FraudFlag)
        .where(FraudFlag.id == flag_id)
        .values(resolved=True, resolved_by=admin.id, resolved_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"ok": True}


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    if search:
        q = q.where(User.phone.ilike(f"%{search}%"))
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(u.id),
            "phone": u.phone,
            "country_code": u.country_code,
            "language": u.language,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.patch("/users/{user_id}/ban")
async def toggle_ban(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    await db.commit()
    return {"user_id": str(user_id), "is_active": user.is_active}


@router.patch("/users/{user_id}/make-admin")
async def toggle_admin(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = not user.is_admin
    await db.commit()
    return {"user_id": str(user_id), "is_admin": user.is_admin}


# ── Dead-letter SMS queue (Feature 17) ────────────────────────────────────────

@router.get("/alerts/failed")
async def list_failed_alerts(
    status: str = "failed",
    limit: int = 50,
    offset: int = 0,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.alert import SmsAlert
    rows = (await db.execute(
        select(SmsAlert)
        .where(SmsAlert.status.in_(["failed", "dead"]) if status == "all" else SmsAlert.status == status)
        .order_by(SmsAlert.sent_at.desc())
        .limit(limit).offset(offset)
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "phone": r.phone,
            "status": r.status,
            "retry_count": r.retry_count,
            "next_retry_at": r.next_retry_at.isoformat() if r.next_retry_at else None,
            "error_message": r.error_message,
            "sent_at": r.sent_at.isoformat(),
            "template_key": r.template_key,
        }
        for r in rows
    ]


@router.post("/alerts/{alert_id}/retry")
async def force_retry_alert(
    alert_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.alert import SmsAlert
    sms = (await db.execute(select(SmsAlert).where(SmsAlert.id == alert_id))).scalar_one_or_none()
    if not sms:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    sms.status = "failed"
    sms.retry_count = 0
    sms.next_retry_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "alert_id": str(alert_id), "queued_at": datetime.now(timezone.utc).isoformat()}


# ── Model drift report (Feature 18) ───────────────────────────────────────────

@router.get("/model/drift-report")
async def model_drift_report(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.tasks.model_monitor import get_drift_report
    return await get_drift_report(db)
