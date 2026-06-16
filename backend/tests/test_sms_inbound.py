"""
SMS inbound service unit tests — keyword classification + reply generation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.parametrize("message,expected_cmd", [
    ("STATUS",   "status"),
    ("status",   "status"),
    ("HALI",     "status"),
    ("imbere",   "status"),
    ("REPORT",   "report"),
    ("tanga",    "report"),
    ("RIPOTI",   "report"),
    ("STOP",     "stop"),
    ("acha",     "stop"),
    ("HAGARIKA", "stop"),
    ("JOIN",     "join"),
    ("JIUNGE",   "join"),
    ("HELP",     "help"),
    ("msaada",   "help"),
    ("random",   "unknown"),
    ("",         "unknown"),
])
def test_keyword_classifier(message, expected_cmd):
    from app.services.sms_inbound_service import _classify
    assert _classify(message) == expected_cmd


@pytest.mark.asyncio
async def test_unknown_user_gets_no_account_reply():
    from app.services.sms_inbound_service import process_inbound_sms

    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    db.add = MagicMock()
    db.flush = AsyncMock()

    with patch("app.services.sms_inbound_service._get_user", return_value=None):
        reply = await process_inbound_sms("+250788000099", "STATUS", db)

    assert "register" in reply.lower() or "blackoutpredictor" in reply.lower()


@pytest.mark.asyncio
async def test_help_reply_contains_commands():
    from app.services.sms_inbound_service import _r
    reply = _r("en", "help")
    assert "STATUS" in reply or "REPORT" in reply


@pytest.mark.asyncio
async def test_reply_fits_in_single_sms():
    from app.services.sms_inbound_service import _REPLIES
    for lang, replies in _REPLIES.items():
        for key, tmpl in replies.items():
            # Template without vars filled should be under 160 chars
            # (with vars it expands, but the base is a proxy)
            assert len(tmpl) <= 160, f"Template {lang}.{key} too long: {len(tmpl)} chars"
