import json
import os

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")
_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _cache:
        path = os.path.join(_TEMPLATE_DIR, f"{lang}.json")
        fallback = os.path.join(_TEMPLATE_DIR, "en.json")
        try:
            with open(path if os.path.exists(path) else fallback) as f:
                _cache[lang] = json.load(f)
        except FileNotFoundError:
            _cache[lang] = {}
    return _cache[lang]


def render_template(template_key: str, lang: str, variables: dict) -> str | None:
    templates = _load(lang)
    if template_key not in templates:
        templates = _load("en")
    raw = templates.get(template_key)
    if not raw:
        return None
    return raw.format(**variables)
