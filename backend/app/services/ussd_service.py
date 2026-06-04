"""
USSD session handler — Africa's Talking / generic aggregator format.

Session state lives in Redis (2-min TTL, matches network timeout).
Each session key maps to the current menu level + accumulated context.

Menu tree:
  0  → main menu
  1  → risk result   (END)
  2  → report confirm
  2c → report done   (END)
  3  → unsubscribe confirm
  3c → unsubscribed  (END)
"""
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.outage import OutageReport
from app.models.prediction import Prediction
from app.models.user import User, UserLocation

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

RISK_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "VERY_HIGH": "🔴"}

# Localised menu strings keyed by language code
_MENUS: dict[str, dict] = {
    "en": {
        "welcome": (
            "CON Welcome to Blackout Predictor\n"
            "1. Check my area risk\n"
            "2. Report power outage\n"
            "3. Unsubscribe alerts\n"
            "0. Help"
        ),
        "risk_none": "END No prediction data for your area yet. Try again later.",
        "risk": "END POWER RISK: {level} ({pct}%)\nNext window: {window}\nEst. duration: {dur}\n\nText STATUS to +{short} for updates.",
        "report_confirm": "CON Confirm outage in your area?\n1. Yes, power is out now\n2. Cancel",
        "report_done": "END Outage reported. Thank you!\nYou earned 10 pts. Neighbors will be alerted.",
        "report_cancel": "END Report cancelled.",
        "unsub_confirm": "CON Stop all SMS alerts?\n1. Yes, unsubscribe\n2. Keep alerts",
        "unsub_done": "END You have been unsubscribed. Text JOIN to re-subscribe anytime.",
        "unsub_cancel": "END You will keep receiving alerts.",
        "help": "END Blackout Predictor: AI-powered outage alerts.\nText STATUS for risk. Text REPORT to report outage.\nVisit blackoutpredictor.com",
        "no_account": "END Your number is not registered.\nVisit blackoutpredictor.com to sign up for free.",
        "invalid": "CON Invalid choice. Please try again.\n1. Check risk\n2. Report outage\n3. Unsubscribe\n0. Help",
    },
    "fr": {
        "welcome": (
            "CON Bienvenue sur Blackout Predictor\n"
            "1. Risque dans mon quartier\n"
            "2. Signaler une panne\n"
            "3. Désabonnement\n"
            "0. Aide"
        ),
        "risk_none": "END Pas encore de données pour votre zone.",
        "risk": "END RISQUE: {level} ({pct}%)\nFenêtre: {window}\nDurée est.: {dur}\n\nEnvoyez STATUT au +{short}.",
        "report_confirm": "CON Confirmer une panne dans votre zone?\n1. Oui, pas de courant\n2. Annuler",
        "report_done": "END Panne signalée. Merci!\nVous gagnez 10 pts.",
        "report_cancel": "END Signalement annulé.",
        "unsub_confirm": "CON Arrêter les alertes SMS?\n1. Oui\n2. Garder",
        "unsub_done": "END Désabonné. Envoyez REJOINDRE pour vous réabonner.",
        "unsub_cancel": "END Vous continuez à recevoir des alertes.",
        "help": "END Blackout Predictor: alertes pannes d'électricité.\nblackoutpredictor.com",
        "no_account": "END Numéro non enregistré. Visitez blackoutpredictor.com",
        "invalid": "CON Choix invalide.\n1. Risque\n2. Signaler\n3. Désabo\n0. Aide",
    },
    "rw": {
        "welcome": (
            "CON Murakaza neza kuri Blackout Predictor\n"
            "1. Reba inzira y'akaga\n"
            "2. Tangaza ikibazo cy'amashanyarazi\n"
            "3. Hagarika ubutumwa\n"
            "0. Ubufasha"
        ),
        "risk_none": "END Nta makuru ahari kuri zona yawe ubu.",
        "risk": "END AKAGA: {level} ({pct}%)\nGihe: {window}\nIgihe gishoboka: {dur}\n\nTumira STATUS kuri +{short}.",
        "report_confirm": "CON Emeza ko amashanyarazi arakaze?\n1. Yego, nta amashanyarazi\n2. Reka",
        "report_done": "END Raporo yatanzwe. Murakoze!\nWahawe amanota 10.",
        "report_cancel": "END Raporo irahagaritswe.",
        "unsub_confirm": "CON Hagarika ubutumwa bwa SMS?\n1. Yego\n2. Komeza",
        "unsub_done": "END Wahagaritswe. Tumira INJIRA kwisubira.",
        "unsub_cancel": "END Ukomeza guhabwa ubutumwa.",
        "help": "END Blackout Predictor: amatangazo y'ikibazo cy'amashanyarazi.\nblackoutpredictor.com",
        "no_account": "END Inomero yawe ntiyanditswe. Sura blackoutpredictor.com",
        "invalid": "CON Amahitamo sibyo.\n1. Akaga\n2. Tangaza\n3. Hagarika\n0. Ubufasha",
    },
    "sw": {
        "welcome": (
            "CON Karibu Blackout Predictor\n"
            "1. Angalia hatari ya eneo langu\n"
            "2. Ripoti kukata umeme\n"
            "3. Jiondoe arifa\n"
            "0. Msaada"
        ),
        "risk_none": "END Hakuna data ya utabiri kwa eneo lako bado.",
        "risk": "END HATARI: {level} ({pct}%)\nDirisha: {window}\nMuda: {dur}\n\nTuma HALI kwa +{short}.",
        "report_confirm": "CON Thibitisha kukata umeme eneo lako?\n1. Ndiyo, umeme umekatika\n2. Ghairi",
        "report_done": "END Ripoti imetumwa. Asante!\nUmepata pointi 10.",
        "report_cancel": "END Ripoti imeghairiwa.",
        "unsub_confirm": "CON Simama arifa za SMS?\n1. Ndiyo\n2. Endelea",
        "unsub_done": "END Umejiondoa. Tuma JIUNGE kujiandikisha tena.",
        "unsub_cancel": "END Utaendelea kupokea arifa.",
        "help": "END Blackout Predictor: arifa za kukata umeme.\nblackoutpredictor.com",
        "no_account": "END Nambari yako haijasajiliwa. Tembelea blackoutpredictor.com",
        "invalid": "CON Chaguo batili.\n1. Hatari\n2. Ripoti\n3. Jiondoe\n0. Msaada",
    },
}

def _t(lang: str, key: str, **kwargs) -> str:
    menu = _MENUS.get(lang, _MENUS["en"])
    tmpl = menu.get(key, _MENUS["en"].get(key, "END Error"))
    return tmpl.format(**kwargs) if kwargs else tmpl


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def _get_session(session_id: str) -> dict:
    r = await _get_redis()
    raw = await r.get(f"ussd:{session_id}")
    return json.loads(raw) if raw else {"step": "0"}


async def _save_session(session_id: str, data: dict) -> None:
    r = await _get_redis()
    await r.setex(f"ussd:{session_id}", 120, json.dumps(data))


async def _clear_session(session_id: str) -> None:
    r = await _get_redis()
    await r.delete(f"ussd:{session_id}")


def _format_window(window_start: datetime, window_end: datetime) -> str:
    now = datetime.now(timezone.utc)
    if window_start.date() == now.date():
        prefix = "Today"
    else:
        prefix = window_start.strftime("%b %d")
    return f"{prefix} {window_start.strftime('%H:%M')}–{window_end.strftime('%H:%M')}"


def _format_duration(pred: Prediction) -> str:
    if pred.predicted_duration_min and pred.predicted_duration_max:
        lo = pred.predicted_duration_min // 60 or f"{pred.predicted_duration_min}m"
        hi = pred.predicted_duration_max // 60 or f"{pred.predicted_duration_max}m"
        return f"{lo}–{hi}h"
    return "unknown"


async def _latest_prediction(h3_index: str, db: AsyncSession) -> Prediction | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index, Prediction.window_end > now)
        .order_by(Prediction.probability.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_user_and_location(phone: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        return None, None
    loc_result = await db.execute(
        select(UserLocation)
        .where(UserLocation.user_id == user.id, UserLocation.is_active == True)
        .order_by(UserLocation.is_primary.desc())
        .limit(1)
    )
    loc = loc_result.scalar_one_or_none()
    return user, loc


async def handle_ussd(
    session_id: str,
    phone: str,
    text: str,
    db: AsyncSession,
) -> str:
    """
    Process one USSD turn. Returns full response string starting with CON or END.
    `text` is the full accumulated input string from the aggregator (e.g. "1*2*1").
    """
    user, loc = await _get_user_and_location(phone, db)
    lang = user.language if user else "en"
    short = settings.USSD_SHORT_CODE

    # Split accumulated input into steps; use last part as current choice
    parts = [p.strip() for p in text.split("*")] if text else []
    step = len(parts)  # 0 = initial dial, 1 = first choice, etc.

    # ── Step 0: initial dial → show main menu ──────────────────────────────
    if step == 0 or text == "":
        await _save_session(session_id, {"step": "main"})
        return _t(lang, "welcome")

    choice = parts[-1] if parts else ""

    # ── Step 1: main menu choice ────────────────────────────────────────────
    if step == 1:
        if choice == "1":  # Check risk
            if not user or not loc:
                await _clear_session(session_id)
                return _t(lang, "no_account")
            pred = await _latest_prediction(loc.h3_index, db)
            if not pred:
                await _clear_session(session_id)
                return _t(lang, "risk_none")
            await _clear_session(session_id)
            return _t(
                lang, "risk",
                level=pred.risk_level,
                pct=int(pred.probability * 100),
                window=_format_window(pred.window_start, pred.window_end),
                dur=_format_duration(pred),
                short=short,
            )

        elif choice == "2":  # Report outage
            if not user or not loc:
                await _clear_session(session_id)
                return _t(lang, "no_account")
            await _save_session(session_id, {"step": "report", "h3": loc.h3_index, "uid": str(user.id)})
            return _t(lang, "report_confirm")

        elif choice == "3":  # Unsubscribe
            if not user:
                await _clear_session(session_id)
                return _t(lang, "no_account")
            await _save_session(session_id, {"step": "unsub", "uid": str(user.id)})
            return _t(lang, "unsub_confirm")

        elif choice == "0":  # Help
            await _clear_session(session_id)
            return _t(lang, "help")

        else:
            return _t(lang, "invalid")

    # ── Step 2: sub-menu confirmations ──────────────────────────────────────
    if step == 2:
        session = await _get_session(session_id)
        sub_step = session.get("step")

        if sub_step == "report":
            await _clear_session(session_id)
            if choice == "1":
                import uuid as _uuid
                report = OutageReport(
                    id=_uuid.uuid4(),
                    user_id=_uuid.UUID(session["uid"]),
                    h3_index=session["h3"],
                    source="ussd",
                    reported_at=datetime.now(timezone.utc),
                )
                db.add(report)
                await db.flush()
                return _t(lang, "report_done")
            return _t(lang, "report_cancel")

        if sub_step == "unsub":
            await _clear_session(session_id)
            if choice == "1":
                result = await db.execute(
                    select(User).where(User.id == _uuid.UUID(session["uid"]))
                )
                u = result.scalar_one_or_none()
                if u:
                    u.is_active = False
                    await db.flush()
                return _t(lang, "unsub_done")
            return _t(lang, "unsub_cancel")

    await _clear_session(session_id)
    return _t(lang, "help")
