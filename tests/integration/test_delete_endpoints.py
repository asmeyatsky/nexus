"""Tests for DELETE endpoints on all five entities."""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from httpx import AsyncClient, ASGITransport
from presentation.api.main import app
from infrastructure.adapters.auth import create_access_token

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _auth(role: str = "admin") -> dict:
    token = create_access_token(
        data={"sub": TEST_USER_ID, "email": "test@example.com", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


async def _create_account(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/accounts",
        json={
            "name": "Del Corp",
            "industry": "technology",
            "territory": "north_america",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_contact(client: AsyncClient, headers: dict, account_id: str) -> str:
    resp = await client.post(
        "/contacts",
        json={
            "account_id": account_id,
            "first_name": "Del",
            "last_name": "Contact",
            "email": "del@example.com",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_opportunity(
    client: AsyncClient, headers: dict, account_id: str
) -> str:
    resp = await client.post(
        "/opportunities",
        json={
            "account_id": account_id,
            "name": "Del Deal",
            "amount": 1000.0,
            "currency": "USD",
            "close_date": "2026-12-31T00:00:00",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_lead(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/leads",
        json={
            "first_name": "Del",
            "last_name": "Lead",
            "email": "dellead@example.com",
            "company": "Del Inc",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_case(
    client: AsyncClient, headers: dict, account_id: str, num: str
) -> str:
    resp = await client.post(
        "/cases",
        json={
            "subject": "Del Case",
            "description": "Delete me",
            "account_id": account_id,
            "owner_id": TEST_USER_ID,
            "case_number": f"DEL-{num}",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ---- Delete then confirm 204 ----


@pytest.mark.asyncio
async def test_delete_account():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        resp = await c.delete(f"/accounts/{aid}", headers=h)
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_contact():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        cid = await _create_contact(c, h, aid)
        resp = await c.delete(f"/contacts/{cid}", headers=h)
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_opportunity():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        oid = await _create_opportunity(c, h, aid)
        resp = await c.delete(f"/opportunities/{oid}", headers=h)
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_lead():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        lid = await _create_lead(c, h)
        resp = await c.delete(f"/leads/{lid}", headers=h)
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_case():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        caseid = await _create_case(c, h, aid, "001")
        resp = await c.delete(f"/cases/{caseid}", headers=h)
        assert resp.status_code == 204


# ---- Delete missing → 404 ----


@pytest.mark.asyncio
async def test_delete_missing_account_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.delete(
            "/accounts/00000000-0000-0000-0000-000000000099", headers=_auth()
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_missing_contact_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.delete(
            "/contacts/00000000-0000-0000-0000-000000000099", headers=_auth()
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_missing_lead_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.delete(
            "/leads/00000000-0000-0000-0000-000000000099", headers=_auth()
        )
        assert resp.status_code == 404


# ---- No auth → 401/403 ----


@pytest.mark.asyncio
async def test_delete_account_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.delete("/accounts/some-id")
        assert resp.status_code in (401, 403)


# ---- Read-only role → 403 ----


@pytest.mark.asyncio
async def test_delete_account_forbidden_for_read_only():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.delete("/accounts/some-id", headers=_auth("read_only"))
        assert resp.status_code == 403
