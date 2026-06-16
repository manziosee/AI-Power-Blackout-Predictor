"""
Pytest fixtures for the backend test suite.

Uses an in-memory SQLite database so no Postgres is needed in CI.
All async tests run via pytest-asyncio with auto mode.
"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── SQLite compat: teach it to render JSONB and UUID as plain JSON / VARCHAR ──
from sqlalchemy import JSON, String
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

def _visit_JSONB(self, type_, **kw):
    return self.visit_JSON(type_, **kw)

def _visit_UUID(self, type_, **kw):
    return self.visit_VARCHAR(String(36), **kw)

SQLiteTypeCompiler.visit_JSONB = _visit_JSONB
SQLiteTypeCompiler.visit_UUID = _visit_UUID
# ─────────────────────────────────────────────────────────────────────────────

# Point config at SQLite before importing the app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("OPENWEATHERMAP_API_KEY", "test-key")
os.environ.setdefault("SMS_GATEWAY_API_KEY", "test-sms-key")
os.environ.setdefault("SMS_GATEWAY_URL", "http://localhost:8001")

from app.core.database import Base
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with _session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    from app.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_payload():
    return {
        "phone": "+250788000001",
        "password": "TestPass123!",
        "country_code": "RW",
        "language": "en",
    }
