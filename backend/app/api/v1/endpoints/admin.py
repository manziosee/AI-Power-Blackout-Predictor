import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.audit import AdminAuditLog
from app.models.fraud import FraudFlag
from app.models.user import User
from app.services.admin_service import (
    get_accuracy_by_country,
    get_celery_health,
    get_platform_stats,
    get_smpp_connectors,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


async def _audit(
    db: AsyncSession,
    admin: User,
    action: str,
    request: Request | None = None,
    target_table: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> None:
    ip = None
    if request:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action=action,
        target_table=target_table,
        target_id=str(target_id) if target_id else None,
        detail=detail,
        ip_address=ip,
    ))


# ── Platform stats ─────────────────────────────────────────────────────────────

@router.get("/stats", summary="Platform-wide KPIs and user/report totals")
async def platform_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_platform_stats(db)


# ── Prediction accuracy by country ────────────────────────────────────────────

@router.get("/accuracy", summary="Model prediction accuracy broken down by country")
async def accuracy_by_country(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_accuracy_by_country(db)


# ── SMPP connector health ──────────────────────────────────────────────────────

@router.get("/smpp-status", summary="Jasmin SMPP connector health")
async def smpp_status(_admin: User = Depends(require_admin)):
    return {"connectors": get_smpp_connectors()}


# ── Celery worker health ───────────────────────────────────────────────────────

@router.get("/celery-health", summary="Celery worker queue health check")
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
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(FraudFlag)
        .where(FraudFlag.id == flag_id)
        .values(resolved=True, resolved_by=admin.id, resolved_at=datetime.now(timezone.utc))
    )
    await _audit(db, admin, "resolve_fraud_flag", request, "fraud_flags", str(flag_id),
                 {"note": body.note})
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
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    await _audit(db, admin, "toggle_ban", request, "users", str(user_id),
                 {"is_active": user.is_active})
    await db.commit()
    return {"user_id": str(user_id), "is_active": user.is_active}


@router.patch("/users/{user_id}/make-admin")
async def toggle_admin(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = not user.is_admin
    await _audit(db, admin, "toggle_admin", request, "users", str(user_id),
                 {"is_admin": user.is_admin})
    await db.commit()
    return {"user_id": str(user_id), "is_admin": user.is_admin}


# ── Dead-letter SMS queue (Feature 17) ────────────────────────────────────────

@router.get("/alerts/failed",
            summary="Dead-letter SMS queue — failed and dead alerts",
            description="Lists SMS alerts with status `failed` or `dead` for manual review and retry. Pass `status=all` to see both.")
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


@router.post("/alerts/{alert_id}/retry",
             summary="Force-retry a failed SMS alert",
             description="Resets retry_count to 0 and next_retry_at to now so the sms_retry worker picks it up on its next 5-minute run.")
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

@router.get("/model/drift-report",
            summary="ML model drift report",
            description="Reads the latest JSONL feedback files and returns a breakdown of healthy/degraded/critical cells plus the worst 10 cells by accuracy drop.")
async def model_drift_report(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.tasks.model_monitor import get_drift_report
    return await get_drift_report(db)


# ── SMS template preview ─────────────────────────────────────────────────────

_SUPPORTED_LANGS = ["en", "fr", "sw", "rw", "ar", "es", "pt"]
_SAMPLE_VARS = {
    "outage_warning": {"prob": "78%", "time": "18:00"},
    "outage_confirmed": {},
    "outage_resolved": {"duration": "120"},
    "welcome": {},
    "test": {},
    "_raw": {"message": "Sample raw message"},
    "password_reset_otp": {"otp": "123456", "ttl_minutes": 10},
}


@router.get("/sms/template-preview",
            summary="Preview SMS templates in all 7 languages",
            description="Renders every template key with sample variables across all supported languages. Useful for QA before a campaign.")
async def sms_template_preview(
    template_key: str | None = Query(None, description="Filter to a single template key"),
    lang: str | None = Query(None, description="Filter to a single language code"),
    _admin: User = Depends(require_admin),
):
    import json as _json
    import os

    template_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..", "..", "sms-gateway", "templates"
    )
    template_dir = os.path.normpath(template_dir)

    langs = [lang] if lang else _SUPPORTED_LANGS
    result: dict[str, dict[str, str | None]] = {}

    for lc in langs:
        path = os.path.join(template_dir, f"{lc}.json")
        fallback = os.path.join(template_dir, "en.json")
        try:
            with open(path if os.path.exists(path) else fallback) as f:
                templates: dict = _json.load(f)
        except FileNotFoundError:
            templates = {}

        keys = [template_key] if template_key else list(templates.keys())
        result[lc] = {}
        for key in keys:
            raw = templates.get(key)
            if raw is None:
                result[lc][key] = None
                continue
            try:
                result[lc][key] = raw.format(**_SAMPLE_VARS.get(key, {}))
            except KeyError as exc:
                result[lc][key] = f"[render error: missing var {exc}]"

    return result


# ── Admin Audit Log ───────────────────────────────────────────────────────────

@router.get("/audit-log",
            summary="Admin action audit log",
            description="Immutable log of all admin actions: bans, role changes, fraud flag resolutions, alert retries, etc.")
async def get_audit_log(
    action: str | None = Query(None, description="Filter by action name e.g. toggle_ban"),
    admin_id: uuid.UUID | None = Query(None),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(AdminAuditLog)
        .where(AdminAuditLog.created_at >= since)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if action:
        q = q.where(AdminAuditLog.action == action)
    if admin_id:
        q = q.where(AdminAuditLog.admin_id == admin_id)

    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "admin_id": str(r.admin_id) if r.admin_id else None,
            "action": r.action,
            "target_table": r.target_table,
            "target_id": r.target_id,
            "detail": r.detail,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/audit-log/export",
            summary="Export audit log as CSV or JSONL",
            description="Download the admin audit log for SOC 2 / ISO 27001 compliance audits.")
async def export_audit_log(
    format: str = Query(default="csv", pattern="^(csv|jsonl)$", description="Output format"),
    days: int = Query(default=30, ge=1, le=365),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import csv
    import io
    import json as _json
    from datetime import timedelta

    from fastapi.responses import StreamingResponse

    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(AdminAuditLog)
        .where(AdminAuditLog.created_at >= since)
        .order_by(AdminAuditLog.created_at.asc())
    )).scalars().all()

    filename = f"audit-log-{days}d.{format}"

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "admin_id", "action", "target_table", "target_id", "ip_address", "created_at"])
        for r in rows:
            writer.writerow([
                str(r.id), str(r.admin_id) if r.admin_id else "",
                r.action, r.target_table or "", r.target_id or "",
                r.ip_address or "", r.created_at.isoformat(),
            ])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    lines = [
        _json.dumps({
            "id": str(r.id),
            "admin_id": str(r.admin_id) if r.admin_id else None,
            "action": r.action,
            "target_table": r.target_table,
            "target_id": r.target_id,
            "detail": r.detail,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat(),
        })
        for r in rows
    ]
    return StreamingResponse(
        iter(["\n".join(lines)]),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
