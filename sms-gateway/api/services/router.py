from connectors.airtel_rw import AirtelRwConnector
from connectors.fallback import FallbackConnector
from connectors.mtn_rw import MtnRwConnector
from connectors.safaricom_ke import SafaricomKeConnector

# Country code → connector instance
_CONNECTORS = {
    "RW_MTN": MtnRwConnector(),
    "RW_AIRTEL": AirtelRwConnector(),
    "KE": SafaricomKeConnector(),
}

_FALLBACK = FallbackConnector()

# country code → preferred connector key
_COUNTRY_MAP = {
    "RW": "RW_MTN",
    "KE": "KE",
}

# In-flight message_id → connector key (for status lookups)
_MESSAGE_REGISTRY: dict[str, str] = {}


def get_connector(country_code: str):
    key = _COUNTRY_MAP.get(country_code.upper())
    return _CONNECTORS.get(key, _FALLBACK)


def get_connector_by_message_id(message_id: str):
    key = _MESSAGE_REGISTRY.get(message_id)
    if not key:
        return None
    return _CONNECTORS.get(key, _FALLBACK)


def register_message(message_id: str, country_code: str):
    key = _COUNTRY_MAP.get(country_code.upper(), "fallback")
    _MESSAGE_REGISTRY[message_id] = key
