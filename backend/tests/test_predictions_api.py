"""
Prediction API endpoint tests — covers all endpoints including new ones.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


# ── helpers ────────────────────────────────────────────────────────────────────

async def _register_and_token(client: AsyncClient, phone: str = "+250788000010") -> str:
    resp = await client.post("/api/v1/users/register", json={
        "phone": phone,
        "password": "TestPass123!",
        "country_code": "RW",
        "language": "en",
    })
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    return resp.json()["access_token"]


async def _admin_token(client: AsyncClient) -> str:
    """Register a user and promote to admin directly in DB."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select

    phone = "+250788099999"
    resp = await client.post("/api/v1/users/register", json={
        "phone": phone,
        "password": "AdminPass123!",
        "country_code": "RW",
        "language": "en",
    })
    token = resp.json()["access_token"]

    # Promote to admin
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        if user:
            user.is_admin = True
            await db.commit()

    return token


H3_TEST = "88283082edfffff"


# ── auth guards ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_list_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/predictions/", params={"h3_index": H3_TEST})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_cell_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/v1/predictions/cell/{H3_TEST}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_latest_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/v1/predictions/latest/{H3_TEST}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_compare_requires_auth(client: AsyncClient):
    resp = await client.get(
        "/api/v1/predictions/compare",
        params={"h3_a": H3_TEST, "h3_b": "88283082eeffffff"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_accuracy_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/v1/predictions/accuracy/{H3_TEST}")
    assert resp.status_code == 401


# ── list endpoint ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_returns_list(client: AsyncClient):
    token = await _register_and_token(client, "+250788000011")
    resp = await client.get(
        "/api/v1/predictions/",
        headers={"Authorization": f"Bearer {token}"},
        params={"h3_index": H3_TEST},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_predictions_list_pagination(client: AsyncClient):
    token = await _register_and_token(client, "+250788000013")
    resp = await client.get(
        "/api/v1/predictions/",
        headers={"Authorization": f"Bearer {token}"},
        params={"h3_index": H3_TEST, "limit": 2, "offset": 0},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) <= 2


@pytest.mark.asyncio
async def test_predictions_list_invalid_limit(client: AsyncClient):
    token = await _register_and_token(client, "+250788000014")
    resp = await client.get(
        "/api/v1/predictions/",
        headers={"Authorization": f"Bearer {token}"},
        params={"h3_index": H3_TEST, "limit": 999},
    )
    # limit capped at 48 — FastAPI validates and returns 422
    assert resp.status_code == 422


# ── cell endpoint ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_cell_returns_list(client: AsyncClient):
    token = await _register_and_token(client, "+250788000015")
    resp = await client.get(
        f"/api/v1/predictions/cell/{H3_TEST}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── latest endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_latest_404_when_empty(client: AsyncClient):
    token = await _register_and_token(client, "+250788000016")
    # Use a cell that definitely has no predictions seeded
    resp = await client.get(
        "/api/v1/predictions/latest/8800000000fffff",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predictions_latest_returns_single_object_when_seeded(client: AsyncClient):
    """Seed a prediction directly then fetch via /latest/."""
    from app.core.database import AsyncSessionLocal
    from app.models.prediction import Prediction

    h3 = "88283082aaffffff"
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        db.add(Prediction(
            h3_index=h3,
            window_start=now,
            window_end=now + timedelta(hours=4),
            probability=0.72,
            confidence=0.75,
            risk_level="HIGH",
            model_version="test-v1",
            region_model="africa_east",
        ))
        await db.commit()

    token = await _register_and_token(client, "+250788000017")
    resp = await client.get(
        f"/api/v1/predictions/latest/{h3}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["h3_index"] == h3
    assert data["probability"] == pytest.approx(0.72, abs=0.01)
    assert data["risk_level"] == "HIGH"
    # features_snapshot is None — we didn't seed it
    assert "features_snapshot" in data


# ── compare endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_compare_returns_structure(client: AsyncClient):
    token = await _register_and_token(client, "+250788000018")
    resp = await client.get(
        "/api/v1/predictions/compare",
        headers={"Authorization": f"Bearer {token}"},
        params={"h3_a": H3_TEST, "h3_b": "88283082eeffffff"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cell_a" in data
    assert "cell_b" in data
    assert "delta_probability" in data
    assert "higher_risk" in data


@pytest.mark.asyncio
async def test_predictions_compare_both_seeded(client: AsyncClient):
    """Seed two cells and verify delta is computed correctly."""
    from app.core.database import AsyncSessionLocal
    from app.models.prediction import Prediction

    now = datetime.now(timezone.utc)
    h3a = "88283082bbffffff"
    h3b = "88283082ccffffff"

    async with AsyncSessionLocal() as db:
        for h3, prob in [(h3a, 0.70), (h3b, 0.40)]:
            db.add(Prediction(
                h3_index=h3,
                window_start=now,
                window_end=now + timedelta(hours=4),
                probability=prob,
                confidence=0.75,
                risk_level="HIGH" if prob >= 0.60 else "MEDIUM",
                model_version="test-v1",
                region_model="africa_east",
            ))
        await db.commit()

    token = await _register_and_token(client, "+250788000019")
    resp = await client.get(
        "/api/v1/predictions/compare",
        headers={"Authorization": f"Bearer {token}"},
        params={"h3_a": h3a, "h3_b": h3b},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["higher_risk"] == "a"
    assert data["delta_probability"] == pytest.approx(0.30, abs=0.01)


# ── accuracy endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_accuracy_returns_structure(client: AsyncClient):
    token = await _register_and_token(client, "+250788000020")
    resp = await client.get(
        f"/api/v1/predictions/accuracy/{H3_TEST}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for field in ("h3_index", "total_predictions", "accuracy", "grade", "verdict"):
        assert field in data
    assert data["h3_index"] == H3_TEST


# ── explain endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predictions_explain_404_when_empty(client: AsyncClient):
    token = await _register_and_token(client, "+250788000021")
    resp = await client.get(
        "/api/v1/predictions/cell/8800000001fffff/explain",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predictions_explain_returns_weights(client: AsyncClient):
    from app.core.database import AsyncSessionLocal
    from app.models.prediction import Prediction

    h3 = "88283082ddffffff"
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        db.add(Prediction(
            h3_index=h3,
            window_start=now,
            window_end=now + timedelta(hours=4),
            probability=0.65,
            confidence=0.75,
            risk_level="HIGH",
            model_version="test-v1",
            region_model="africa_east",
            features_snapshot={
                "rainfall_mm": 35.0,
                "wind_speed_ms": 12.0,
                "weather_risk": 0.40,
                "historical_frequency": 0.50,
            },
        ))
        await db.commit()

    token = await _register_and_token(client, "+250788000022")
    resp = await client.get(
        f"/api/v1/predictions/cell/{h3}/explain",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "feature_weights" in data
    assert "top_factor" in data
    assert "explanation_method" in data
    weights = data["feature_weights"]
    assert isinstance(weights, dict)
    assert len(weights) >= 3
    # All weights sum to ~1.0
    assert abs(sum(weights.values()) - 1.0) < 0.01


# ── heatmap endpoint (public) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_heatmap_returns_list(client: AsyncClient):
    resp = await client.get(
        "/api/v1/predictions/heatmap",
        params={"country_code": "RW"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_heatmap_missing_country_code(client: AsyncClient):
    resp = await client.get("/api/v1/predictions/heatmap")
    assert resp.status_code == 422


# ── trigger endpoint (admin) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_requires_admin(client: AsyncClient):
    token = await _register_and_token(client, "+250788000023")
    resp = await client.post(
        "/api/v1/predictions/trigger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_report_outage(client: AsyncClient):
    token = await _register_and_token(client, "+250788000012")
    resp = await client.post(
        "/api/v1/outages/report",
        headers={"Authorization": f"Bearer {token}"},
        json={"h3_index": H3_TEST, "description": "Power out"},
    )
    assert resp.status_code in (200, 201)
