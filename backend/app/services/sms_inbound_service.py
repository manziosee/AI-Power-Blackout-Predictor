"""
Two-way SMS command processor.

Incoming keywords (case-insensitive, multi-language):
  REPORT / TANGA / RIPOTI / SIGNALER / RAPORO  → confirm outage in user's area
  STATUS / HALI / IMBERE / STATUT / HALI       → get current risk
  STOP / ACHA / HAGARIKA / ARRÊT / SIMAMA      → unsubscribe
  HELP / MSAADA / UBUFASHA / AIDE / AYUDA      → help text
  JOIN / JIUNGE / INJIRA / REJOINDRE            → re-subscribe
  (anything else)                               → unknown command → help hint
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertSubscription
from app.models.outage import OutageReport
from app.models.prediction import Prediction
from app.models.user import User, UserLocation

logger = logging.getLogger(__name__)

# ── Keyword maps ────────────────────────────────────────────────────────────

_KEYWORDS: dict[str, set[str]] = {
    "report": {"report", "tanga", "ripoti", "signaler", "raporo", "arifu"},
    "status": {"status", "hali", "imbere", "statut", "estado", "situação"},
    "stop":   {"stop", "acha", "hagarika", "arrêt", "simama", "pare", "parar"},
    "help":   {"help", "msaada", "ubufasha", "aide", "ayuda", "ajuda"},
    "join":   {"join", "jiunge", "injira", "rejoindre", "unirse", "juntar"},
}

def _classify(text: str) -> str:
    word = text.strip().lower().split()[0] if text.strip() else ""
    for cmd, keywords in _KEYWORDS.items():
        if word in keywords:
            return cmd
    return "unknown"


# ── Reply templates (160-char SMS safe) ─────────────────────────────────────

_REPLIES: dict[str, dict[str, str]] = {
    "en": {
        "no_account": "You're not registered. Sign up free at blackoutpredictor.com",
        "no_location": "Set your location in the app first. blackoutpredictor.com",
        "report_done": "Outage reported in your area. +10 pts earned. Neighbors notified.",
        "status_none": "No prediction data for your area yet. Check back soon.",
        "status": "RISK: {level} ({pct}%) | Next: {window} | Est.duration: {dur}",
        "stop_done": "Unsubscribed from alerts. Text JOIN to reactivate anytime.",
        "already_stopped": "You're not subscribed to alerts. Text JOIN to subscribe.",
        "join_done": "Welcome back! You'll receive alerts for outages in your area.",
        "already_joined": "You already receive alerts. Text STOP to unsubscribe.",
        "help": "Commands: STATUS (check risk) REPORT (log outage) STOP (unsubscribe) JOIN (subscribe) | blackoutpredictor.com",
        "unknown": "Unknown command. Reply HELP for options.",
    },
    "fr": {
        "no_account": "Non enregistré. Inscrivez-vous sur blackoutpredictor.com",
        "no_location": "Définissez votre localisation dans l'app d'abord.",
        "report_done": "Panne signalée. +10 pts gagnés. Voisins notifiés.",
        "status_none": "Pas encore de données pour votre zone.",
        "status": "RISQUE: {level} ({pct}%) | Fenêtre: {window} | Durée: {dur}",
        "stop_done": "Désabonné. Envoyez REJOINDRE pour vous réabonner.",
        "already_stopped": "Vous n'êtes pas abonné. Envoyez REJOINDRE.",
        "join_done": "Bienvenue! Vous recevrez des alertes pour votre zone.",
        "already_joined": "Vous êtes déjà abonné. Envoyez ARRÊT pour vous désabonner.",
        "help": "Commandes: STATUT SIGNALER ARRÊT REJOINDRE | blackoutpredictor.com",
        "unknown": "Commande inconnue. Répondez AIDE pour les options.",
    },
    "rw": {
        "no_account": "Ntuyanditswe. Iyandikishe kuri blackoutpredictor.com",
        "no_location": "Shyira ahantu hwawe mu porogaramu mbere.",
        "report_done": "Raporo yatanzwe. +10 amanota. Abatuye hafi bamenyeshejwe.",
        "status_none": "Nta makuru ahari kuri zona yawe.",
        "status": "AKAGA: {level} ({pct}%) | Gihe: {window} | Igihe: {dur}",
        "stop_done": "Wahagaritswe. Tumira INJIRA kwisubira.",
        "already_stopped": "Ntuziyandikishije. Tumira INJIRA.",
        "join_done": "Murakaza neza! Uzakira ubutumwa bw'inzira.",
        "already_joined": "Usanzwe uyandikishije. Tumira HAGARIKA.",
        "help": "Amategeko: IMBERE TANGA HAGARIKA INJIRA | blackoutpredictor.com",
        "unknown": "Itegeko ntizwi. Subiza UBUFASHA.",
    },
    "sw": {
        "no_account": "Hujasajiliwa. Jisajili kwa blackoutpredictor.com",
        "no_location": "Weka eneo lako kwenye programu kwanza.",
        "report_done": "Ripoti imetumwa. +10 pointi. Majirani wamearifiwa.",
        "status_none": "Hakuna data ya utabiri kwa eneo lako bado.",
        "status": "HATARI: {level} ({pct}%) | Dirisha: {window} | Muda: {dur}",
        "stop_done": "Umejiondoa. Tuma JIUNGE kujiandikisha tena.",
        "already_stopped": "Hujisajilii. Tuma JIUNGE.",
        "join_done": "Karibu tena! Utapokea arifa za eneo lako.",
        "already_joined": "Tayari umesajiliwa. Tuma ACHA kujiondoa.",
        "help": "Amri: HALI RIPOTI ACHA JIUNGE | blackoutpredictor.com",
        "unknown": "Amri haijulikani. Jibu MSAADA kwa chaguzi.",
    },
    "ar": {
        "no_account": "غير مسجل. سجّل مجاناً على blackoutpredictor.com",
        "no_location": "حدّد موقعك في التطبيق أولاً.",
        "report_done": "تم الإبلاغ عن انقطاع الكهرباء. +10 نقاط. تم إخطار الجيران.",
        "status_none": "لا توجد بيانات تنبؤية لمنطقتك بعد.",
        "status": "الخطر: {level} ({pct}%) | النافذة: {window} | المدة: {dur}",
        "stop_done": "تم إلغاء الاشتراك. أرسل JOIN للاشتراك مجدداً.",
        "already_stopped": "لست مشتركاً. أرسل JOIN.",
        "join_done": "مرحباً! ستتلقى تنبيهات لمنطقتك.",
        "already_joined": "أنت مشترك بالفعل. أرسل STOP لإلغاء الاشتراك.",
        "help": "الأوامر: STATUS REPORT STOP JOIN | blackoutpredictor.com",
        "unknown": "أمر غير معروف. أرسل HELP للخيارات.",
    },
    "es": {
        "no_account": "No registrado. Regístrate en blackoutpredictor.com",
        "no_location": "Configura tu ubicación en la app primero.",
        "report_done": "Corte reportado. +10 pts. Vecinos notificados.",
        "status_none": "Sin datos de predicción para tu zona aún.",
        "status": "RIESGO: {level} ({pct}%) | Ventana: {window} | Duración: {dur}",
        "stop_done": "Dado de baja. Envía UNIRSE para volver.",
        "already_stopped": "No estás suscrito. Envía UNIRSE.",
        "join_done": "¡Bienvenido! Recibirás alertas para tu zona.",
        "already_joined": "Ya estás suscrito. Envía PARE para darse de baja.",
        "help": "Comandos: ESTADO REPORTAR PARE UNIRSE | blackoutpredictor.com",
        "unknown": "Comando desconocido. Responde AYUDA.",
    },
    "pt": {
        "no_account": "Não registado. Registe-se em blackoutpredictor.com",
        "no_location": "Defina a sua localização na app primeiro.",
        "report_done": "Corte reportado. +10 pts. Vizinhos notificados.",
        "status_none": "Sem dados de previsão para a sua zona ainda.",
        "status": "RISCO: {level} ({pct}%) | Janela: {window} | Duração: {dur}",
        "stop_done": "Cancelado. Envie JUNTAR para voltar.",
        "already_stopped": "Não está subscrito. Envie JUNTAR.",
        "join_done": "Bem-vindo! Receberá alertas para a sua zona.",
        "already_joined": "Já está subscrito. Envie PARAR para cancelar.",
        "help": "Comandos: SITUAÇÃO REPORTAR PARAR JUNTAR | blackoutpredictor.com",
        "unknown": "Comando desconhecido. Responda AJUDA.",
    },
}

def _r(lang: str, key: str, **kwargs) -> str:
    replies = _REPLIES.get(lang, _REPLIES["en"])
    tmpl = replies.get(key, _REPLIES["en"].get(key, ""))
    return tmpl.format(**kwargs) if kwargs else tmpl


# ── DB helpers ───────────────────────────────────────────────────────────────

async def _get_user(phone: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def _primary_location(user: User, db: AsyncSession) -> UserLocation | None:
    result = await db.execute(
        select(UserLocation)
        .where(UserLocation.user_id == user.id, UserLocation.is_active)
        .order_by(UserLocation.is_primary.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_prediction(h3_index: str, db: AsyncSession) -> Prediction | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Prediction)
        .where(Prediction.h3_index == h3_index, Prediction.window_end > now)
        .order_by(Prediction.probability.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _fmt_window(start: datetime, end: datetime) -> str:
    now = datetime.now(timezone.utc)
    prefix = "Today" if start.date() == now.date() else start.strftime("%b %d")
    return f"{prefix} {start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def _fmt_dur(pred: Prediction) -> str:
    if pred.predicted_duration_min and pred.predicted_duration_max:
        lo = pred.predicted_duration_min // 60
        hi = pred.predicted_duration_max // 60
        return f"{lo or '<1'}–{hi}h"
    return "?"


# ── Main handler ─────────────────────────────────────────────────────────────

async def process_inbound_sms(phone: str, message: str, db: AsyncSession) -> str:
    """
    Handle one inbound SMS. Returns the reply text to send back (max ~160 chars).
    Also persists an SmsInboundLog row.
    """
    cmd = _classify(message)
    user = await _get_user(phone, db)
    lang = user.language if user else "en"

    reply = await _dispatch(cmd, phone, user, lang, db)

    # Persist log
    from app.models.accessibility import SmsInboundLog
    log = SmsInboundLog(
        phone=phone,
        message=message[:160],
        command=cmd,
        reply=reply[:160],
        user_id=user.id if user else None,
    )
    db.add(log)
    await db.flush()

    return reply


async def _dispatch(cmd: str, phone: str, user: User | None, lang: str, db: AsyncSession) -> str:
    if not user:
        if cmd in ("join",):
            return _r(lang, "no_account")
        return _r(lang, "no_account")

    loc = await _primary_location(user, db)

    if cmd == "status":
        if not loc:
            return _r(lang, "no_location")
        pred = await _latest_prediction(loc.h3_index, db)
        if not pred:
            return _r(lang, "status_none")
        return _r(
            lang, "status",
            level=pred.risk_level,
            pct=int(pred.probability * 100),
            window=_fmt_window(pred.window_start, pred.window_end),
            dur=_fmt_dur(pred),
        )

    if cmd == "report":
        if not loc:
            return _r(lang, "no_location")
        report = OutageReport(
            id=uuid.uuid4(),
            user_id=user.id,
            h3_index=loc.h3_index,
            source="sms_inbound",
            reported_at=datetime.now(timezone.utc),
        )
        db.add(report)
        await db.flush()
        return _r(lang, "report_done")

    if cmd == "stop":
        if not user.is_active:
            return _r(lang, "already_stopped")
        result = await db.execute(
            select(AlertSubscription).where(AlertSubscription.user_id == user.id)
        )
        subs = result.scalars().all()
        for sub in subs:
            sub.is_active = False
        await db.flush()
        return _r(lang, "stop_done")

    if cmd == "join":
        result = await db.execute(
            select(AlertSubscription).where(AlertSubscription.user_id == user.id)
        )
        subs = result.scalars().all()
        if any(s.is_active for s in subs):
            return _r(lang, "already_joined")
        for sub in subs:
            sub.is_active = True
        await db.flush()
        return _r(lang, "join_done")

    if cmd == "help":
        return _r(lang, "help")

    return _r(lang, "unknown")
