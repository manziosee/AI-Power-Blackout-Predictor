"""Service for IVR phone call alerts."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ivr import IvrCall
from app.models.user import UserLocation

_TTS_SCRIPTS = {
    "en": "Power outage risk alert. Your area has a {probability}% risk of outage at {time}. Stay prepared.",
    "fr": "Alerte risque de panne. Votre zone a {probability}% de risque à {time}. Soyez prêts.",
    "rw": "Imenyesha ry'amashanyarazi. Gace kawe karagira {probability}% yo guta amashanyarazi saa {time}.",
    "sw": "Tahadhari ya umeme. Eneo lako lina hatari ya {probability}% ya kukosa umeme saa {time}.",
    "ar": "تحذير انقطاع الكهرباء. منطقتك معرضة لخطر {probability}% في الساعة {time}.",
    "es": "Alerta de corte de luz. Su área tiene {probability}% de riesgo a las {time}.",
    "pt": "Alerta de corte de energia. Sua área tem {probability}% de risco às {time}.",
}


def get_tts_script(language: str, risk_level: str, probability: float, window_start: datetime) -> str:
    template = _TTS_SCRIPTS.get(language, _TTS_SCRIPTS["en"])
    time_str = window_start.strftime("%H:%M") if window_start else "soon"
    return template.format(probability=int(probability * 100), time=time_str)


async def queue_calls_for_cell(
    h3_index: str,
    risk_level: str,
    probability: float,
    db: AsyncSession,
) -> list[IvrCall]:
    """Create IvrCall rows for all users in the cell."""
    loc_result = await db.execute(
        select(UserLocation).where(UserLocation.h3_index == h3_index, UserLocation.is_active)
    )
    locations = loc_result.scalars().all()

    user_ids = [loc.user_id for loc in locations]
    if not user_ids:
        return []

    from app.models.user import User as UserModel
    users_result = await db.execute(
        select(UserModel).where(UserModel.id.in_(user_ids), UserModel.is_active)
    )
    users = users_result.scalars().all()

    calls = []
    for user in users:
        call = IvrCall(
            user_id=user.id,
            phone=user.phone,
            h3_index=h3_index,
            language=user.language or "en",
            risk_level=risk_level,
            probability=probability,
            call_status="queued",
        )
        db.add(call)
        calls.append(call)
    await db.flush()
    return calls
