"""WhatsApp Cloud API (Meta) integration for outage alerts."""
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

WA_API_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"

# WhatsApp message template names — must be pre-approved in Meta Business Manager
TEMPLATES = {
    "outage_warning":   "blackout_outage_warning",
    "outage_confirmed": "blackout_outage_confirmed",
    "outage_resolved":  "blackout_outage_resolved",
    "welcome":          "blackout_welcome",
    "weekly_digest":    "blackout_weekly_digest",
}


async def send_whatsapp_message(
    to: str,
    template_key: str,
    language: str,
    components: list[dict] | None = None,
) -> dict:
    """Send a WhatsApp template message via the Meta Cloud API.

    Args:
        to: Recipient phone in E.164 format e.g. +250788123456
        template_key: Internal template key (mapped to approved WA template name)
        language: BCP-47 language code e.g. en, fr, sw
        components: Optional list of template variable components
    """
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        log.debug("WhatsApp not configured — skipping")
        return {}

    url = WA_API_URL.format(phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID)
    template_name = TEMPLATES.get(template_key, template_key)
    wa_lang = _map_language(language)

    payload: dict = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": wa_lang},
        },
    }
    if components:
        payload["template"]["components"] = components

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            log.error(f"WhatsApp API error {resp.status_code}: {resp.text}")
            resp.raise_for_status()
        return resp.json()


async def send_whatsapp_text(to: str, text: str) -> dict:
    """Send a plain text WhatsApp message (for bot-style replies)."""
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        return {}

    url = WA_API_URL.format(phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID)
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "text",
        "text": {"body": text},
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def build_outage_warning_components(probability: int, time_str: str) -> list[dict]:
    """Build template variable components for outage_warning template."""
    return [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": f"{probability}%"},
                {"type": "text", "text": time_str},
            ],
        }
    ]


def build_weekly_digest_components(outages_last_week: int, predictions_this_week: int, area: str) -> list[dict]:
    return [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": area},
                {"type": "text", "text": str(outages_last_week)},
                {"type": "text", "text": str(predictions_this_week)},
            ],
        }
    ]


def _map_language(lang: str) -> str:
    mapping = {
        "en": "en_US",
        "fr": "fr",
        "sw": "sw",
        "rw": "rw",
        "ar": "ar",
        "es": "es",
        "pt": "pt_BR",
    }
    return mapping.get(lang, "en_US")
