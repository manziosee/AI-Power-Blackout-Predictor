"""
Prediction API endpoint tests.
"""
import pytest
from httpx import AsyncClient


async def _register_and_token(client: AsyncClient, phone="+250788000010") -> str:
    resp = await client.post("/api/v1/users/register", json={
        "phone": phone, "password": "TestPass123!", "country_code": "RW", "language": "en"
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_predictions_endpoint_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/predictions/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_returns_list(client: AsyncClient):
    token = await _register_and_token(client, "+250788000011")
    resp = await client.get(
        "/api/v1/predictions/",
        headers={"Authorization": f"Bearer {token}"},
        params={"h3_index": "88283082edfffff"},
    )
    # Returns 200 with a list (may be empty if no predictions seeded)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_report_outage(client: AsyncClient):
    token = await _register_and_token(client, "+250788000012")
    resp = await client.post(
        "/api/v1/outages/report",
        headers={"Authorization": f"Bearer {token}"},
        json={"h3_index": "88283082edfffff", "description": "Power out"},
    )
    assert resp.status_code in (200, 201)
