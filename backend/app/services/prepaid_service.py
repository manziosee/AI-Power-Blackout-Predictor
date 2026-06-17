"""Service for prepaid meter integration."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prepaid import PrepaidMeter, PrepaidTopupReminder

_LOW_BALANCE_MSGS = {
    "en": "Low balance alert: {balance} kWh remaining on {provider}. Power risk in {hours}h. Top up now.",
    "fr": "Alerte faible solde: {balance} kWh restants sur {provider}. Risque de panne dans {hours}h. Rechargez.",
    "rw": "Inkomyi ya lisansi yo hasi: {balance} kWh ari kuri {provider}. Akaga infashije mu masaha {hours}. Ishyura.",
    "sw": "Tahadhari ya salio: {balance} kWh zilizo kwenye {provider}. Hatari ya umeme baada ya saa {hours}. Lipa sasa.",
    "ar": "تحذير رصيد منخفض: {balance} كيلوواط متبقية على {provider}. خطر انقطاع خلال {hours} ساعة. اشحن الآن.",
    "es": "Alerta saldo bajo: {balance} kWh en {provider}. Riesgo de corte en {hours}h. Recarga ahora.",
    "pt": "Alerta de saldo baixo: {balance} kWh em {provider}. Risco de corte em {hours}h. Recarregue agora.",
}


def get_alert_message(language: str, balance: float, provider: str, hours_until_risk: int) -> str:
    template = _LOW_BALANCE_MSGS.get(language, _LOW_BALANCE_MSGS["en"])
    return template.format(
        balance=round(balance, 1),
        provider=provider or "your provider",
        hours=hours_until_risk,
    )


async def check_and_send_balance_alerts(db: AsyncSession) -> int:
    """Find meters with low balance where there's high-risk prediction. Returns count sent."""
    from app.models.prediction import Prediction
    from app.models.user import User

    now = datetime.now(timezone.utc)
    # Get meters with low balance and active status
    meters_result = await db.execute(
        select(PrepaidMeter).where(
            PrepaidMeter.is_active.is_(True),
            PrepaidMeter.last_balance_kwh.is_not(None),
        )
    )
    meters = meters_result.scalars().all()

    sent = 0
    for meter in meters:
        if meter.last_balance_kwh > meter.low_balance_threshold_kwh:
            continue

        # Check for high-risk prediction in alert window
        pred_result = await db.execute(
            select(Prediction).where(
                Prediction.h3_index == meter.h3_index,
                Prediction.risk_level.in_(["high", "critical"]),
                Prediction.window_start > now,
            ).order_by(Prediction.window_start).limit(1)
        )
        pred = pred_result.scalar_one_or_none()
        if not pred:
            continue

        hours_until = int((pred.window_start - now).total_seconds() / 3600)
        if hours_until > meter.alert_before_hours:
            continue

        # Get user language
        user_result = await db.execute(
            select(User).where(User.id == meter.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        lang = user.language or "en"
        msg = get_alert_message(lang, meter.last_balance_kwh, meter.provider or "provider", hours_until)

        reminder = PrepaidTopupReminder(
            user_id=meter.user_id,
            meter_id=meter.id,
            prediction_id=pred.id,
            balance_at_send=meter.last_balance_kwh,
        )
        db.add(reminder)
        sent += 1

    await db.flush()
    return sent
