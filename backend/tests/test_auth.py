import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, sample_user_payload):
    resp = await client.post("/api/v1/users/register", json=sample_user_payload)
    assert resp.status_code == 201
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_register_duplicate_phone(client: AsyncClient, sample_user_payload):
    await client.post("/api/v1/users/register", json=sample_user_payload)
    resp = await client.post("/api/v1/users/register", json=sample_user_payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, sample_user_payload):
    await client.post("/api/v1/users/register", json=sample_user_payload)
    resp = await client.post("/api/v1/users/login", json={
        "phone": sample_user_payload["phone"],
        "password": sample_user_payload["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, sample_user_payload):
    await client.post("/api/v1/users/register", json=sample_user_payload)
    resp = await client.post("/api/v1/users/login", json={
        "phone": sample_user_payload["phone"],
        "password": "wrong-password",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, sample_user_payload):
    reg = await client.post("/api/v1/users/register", json=sample_user_payload)
    token = reg.json()["access_token"]
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == sample_user_payload["phone"]
