"""
Generic Jasmin HTTP connector.

Jasmin routes SMS to the correct SMPP operator connection via the `connector`
parameter. Configure connector IDs per country in environment variables —
no code changes needed when adding new operators.

Environment variables:
  JASMIN_HOST            default: localhost
  JASMIN_HTTP_PORT       default: 8080
  JASMIN_USERNAME        default: jcliadmin
  JASMIN_PASSWORD        default: jclipwd
  JASMIN_SENDER_ID       default: BLACKOUT   (the From / sender ID)
  JASMIN_CONNECTOR_{CC}  connector ID for country code CC
                         e.g. JASMIN_CONNECTOR_RW=default
                              JASMIN_CONNECTOR_KE=default
                              JASMIN_CONNECTOR_NG=default
  JASMIN_CONNECTOR_DEFAULT  fallback connector ID (default: default)
"""
import os
import uuid

import httpx

from connectors.base import BaseConnector

_HOST     = os.getenv("JASMIN_HOST", "localhost")
_PORT     = os.getenv("JASMIN_HTTP_PORT", "8080")
_USER     = os.getenv("JASMIN_USERNAME", "jcliadmin")
_PASS     = os.getenv("JASMIN_PASSWORD", "jclipwd")
_SENDER   = os.getenv("JASMIN_SENDER_ID", "BLACKOUT")
_DEFAULT_CID = os.getenv("JASMIN_CONNECTOR_DEFAULT", "default")


def _connector_id(country_code: str) -> str:
    env_key = f"JASMIN_CONNECTOR_{country_code.upper()}"
    return os.getenv(env_key, _DEFAULT_CID)


class JasminConnector(BaseConnector):
    """Single connector for all countries — routes via Jasmin connector IDs."""

    provider_name = "jasmin"

    def __init__(self, country_code: str = ""):
        self._country = country_code.upper()

    async def send(self, to: str, message: str) -> dict:
        params = {
            "username": _USER,
            "password": _PASS,
            "to":       to,
            "content":  message,
            "from":     _SENDER,
            "connector": _connector_id(self._country or _infer_country(to)),
            "coding":   0,   # GSM7
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"http://{_HOST}:{_PORT}/send", params=params)
            resp.raise_for_status()
            text = resp.text.strip()
            # Jasmin success: Success "msgid"
            msg_id = text.split('"')[1] if '"' in text else str(uuid.uuid4())
            return {"message_id": msg_id, "status": "sent"}

    async def get_delivery_status(self, message_id: str) -> str:
        try:
            params = {"username": _USER, "password": _PASS, "messageid": message_id}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"http://{_HOST}:{_PORT}/dlr", params=params)
                resp.raise_for_status()
                body = resp.text.strip().lower()
                if "delivered" in body:
                    return "delivered"
                if "failed" in body or "undeliverable" in body:
                    return "failed"
            return "sent"
        except Exception:
            return "unknown"


def _infer_country(phone: str) -> str:
    """Best-effort country from E.164 prefix when no country is passed."""
    prefixes = {
        "+250": "RW", "+254": "KE", "+255": "TZ", "+256": "UG",
        "+234": "NG", "+233": "GH", "+221": "SN", "+212": "MA",
        "+27":  "ZA", "+1":   "US", "+44":  "GB",
    }
    for prefix, code in sorted(prefixes.items(), key=lambda x: -len(x[0])):
        if phone.startswith(prefix):
            return code
    return ""
