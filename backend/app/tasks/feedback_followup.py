"""Celery tasks for prediction feedback follow-up SMS."""
import logging

logger = logging.getLogger(__name__)

_FEEDBACK_MESSAGES = {
    "en": "Did your power go out after our alert? Reply YES or NO",
    "fr": "Votre électricité a-t-elle été coupée après notre alerte? Répondez OUI ou NON",
    "rw": "Mbega amashanyarazi yarahagaze nyuma y'ubutumwa bwacu? Subiza YEG cyangwa OYA",
    "sw": "Je, umeme wako ulikwenda baada ya arifa yetu? Jibu NDIYO au HAPANA",
    "ar": "هل انقطعت الكهرباء لديك بعد تنبيهنا؟ أجب بـ نعم أو لا",
    "es": "¿Se fue la luz después de nuestra alerta? Responde SÍ o NO",
    "pt": "A luz foi embora depois do nosso alerta? Responda SIM ou NÃO",
}


def get_feedback_message(language: str) -> str:
    return _FEEDBACK_MESSAGES.get(language, _FEEDBACK_MESSAGES["en"])


def send_feedback_sms(feedback_id: str) -> None:
    """
    Celery task: send feedback SMS 4h after alert.
    countdown=14400 should be set when calling apply_async.
    """
    try:
        import asyncio
        from app.core.database import AsyncSessionLocal
        from app.models.prediction_feedback import PredictionFeedback
        from app.models.user import User
        import uuid
        from sqlalchemy import select
        from datetime import datetime, timezone

        async def _run():
            async with AsyncSessionLocal() as db:
                fb_result = await db.execute(
                    select(PredictionFeedback).where(
                        PredictionFeedback.id == uuid.UUID(feedback_id)
                    )
                )
                fb = fb_result.scalar_one_or_none()
                if fb is None or fb.outage_occurred is not None:
                    return

                if fb.user_id is None:
                    return

                user_result = await db.execute(
                    select(User).where(User.id == fb.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return

                lang = user.language or "en"
                msg = get_feedback_message(lang)

                # Send SMS via Jasmin
                from app.services.africastalking_service import send_sms
                await send_sms(user.phone, msg)

                fb.sms_sent_at = datetime.now(timezone.utc)
                await db.commit()

        asyncio.run(_run())
    except Exception as exc:
        logger.error("send_feedback_sms failed for %s: %s", feedback_id, exc)
        raise
