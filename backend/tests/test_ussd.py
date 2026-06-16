"""
USSD service unit tests — no DB or Redis required (mocked).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_ussd_initial_dial_returns_main_menu():
    from app.services.ussd_service import handle_ussd

    db = _mock_db()
    # No user found
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with patch("app.services.ussd_service._get_redis") as mock_redis_fn:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        response = await handle_ussd("sess1", "+250788000001", "", db)

    assert response.startswith("CON")
    assert "1." in response
    assert "2." in response


@pytest.mark.asyncio
async def test_ussd_help_returns_end():
    from app.services.ussd_service import handle_ussd

    db = _mock_db()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with patch("app.services.ussd_service._get_redis") as mock_redis_fn:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        response = await handle_ussd("sess2", "+250788000001", "0", db)

    assert response.startswith("END")


@pytest.mark.asyncio
async def test_ussd_no_account_on_risk_check():
    from app.services.ussd_service import handle_ussd

    db = _mock_db()
    # Simulate user not found
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with patch("app.services.ussd_service._get_redis") as mock_redis_fn:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis_fn.return_value = mock_redis

        response = await handle_ussd("sess3", "+250788999999", "1", db)

    assert response.startswith("END")
    assert "not registered" in response.lower() or "nyanditswe" in response.lower() or \
           "enregistré" in response.lower() or "jisajili" in response.lower() or \
           "registered" in response.lower()
