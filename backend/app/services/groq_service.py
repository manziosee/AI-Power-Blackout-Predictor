"""Groq LLM service — AI-powered outage risk explanations."""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.1-8b-instant"

_LANG_NAMES = {
    "en": "English",
    "fr": "French",
    "rw": "Kinyarwanda",
    "sw": "Swahili",
    "ar": "Arabic",
    "es": "Spanish",
    "pt": "Portuguese",
}


async def explain_prediction(
    risk_level: str,
    probability: float,
    rainfall_mm: float,
    wind_speed_ms: float,
    temperature_c: float,
    outages_7d: int,
    window_start: str,
    language: str = "en",
) -> str:
    """Return a 2–3 sentence plain-language explanation of why risk is high or low.
    Returns empty string if Groq is not configured or the call fails.
    """
    if not settings.GROQ_API_KEY:
        return ""

    lang = _LANG_NAMES.get(language, "English")
    prompt = (
        f"You are an AI assistant for a global electricity outage prediction system. "
        f"In 2-3 plain sentences in {lang}, explain why the area has a "
        f"{risk_level} outage risk ({int(probability * 100)}%) at {window_start}.\n"
        f"Conditions: rainfall={rainfall_mm}mm, wind={wind_speed_ms}m/s, "
        f"temperature={temperature_c}°C, outages in last 7 days={outages_7d}.\n"
        f"Be specific about which conditions are driving the risk. Under 80 words."
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _GROQ_URL,
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq explain_prediction failed: %s", exc)
        return ""


async def summarize_outage_history(
    h3_index: str,
    outage_count_7d: int,
    outage_count_30d: int,
    avg_duration_minutes: float | None,
    language: str = "en",
) -> str:
    """Return a short AI summary of outage history for a neighborhood."""
    if not settings.GROQ_API_KEY:
        return ""

    lang = _LANG_NAMES.get(language, "English")
    dur = f"{avg_duration_minutes:.0f} minutes" if avg_duration_minutes else "unknown"
    prompt = (
        f"In 2 sentences in {lang}, summarize the power reliability of a neighborhood "
        f"that had {outage_count_7d} outages in the last 7 days, {outage_count_30d} in the "
        f"last 30 days, with an average outage duration of {dur}. Be concise and factual."
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _GROQ_URL,
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq summarize_outage_history failed: %s", exc)
        return ""
