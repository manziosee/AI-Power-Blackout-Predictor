from connectors.fallback import FallbackConnector
from connectors.jasmin import JasminConnector

_FALLBACK = FallbackConnector()

# One shared Jasmin connector instance — routes by connector ID via env vars
_JASMIN = JasminConnector()

# In-flight message_id → connector key (for status lookups)
_MESSAGE_REGISTRY: dict[str, str] = {}


def get_connector(country_code: str):
    """Return the right connector for a country code."""
    return _JASMIN


def get_connector_by_message_id(message_id: str):
    return _JASMIN if message_id in _MESSAGE_REGISTRY else _FALLBACK


def register_message(message_id: str, country_code: str):
    _MESSAGE_REGISTRY[message_id] = country_code
