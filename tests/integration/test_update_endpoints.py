"""Tests for update and action endpoints."""

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


async def _create_account(client, headers) -> str:
    resp = await client.post(
        "/accounts",
        json={
            "name": "Upd Corp",
            "industry": "technology",
            "territory": "north_america",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    return resp.json()["id"]


async def _create_contact(client, headers, account_id) -> str:
    resp = await client.post(
        "/contacts",
        json={
            "account_id": account_id,
            "first_name": "Upd",
            "last_name": "Contact",
            "email": "upd@example.com",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    return resp.json()["id"]


async def _create_opportunity(client, headers, account_id) -> str:
    resp = await client.post(
        "/opportunities",
        json={
            "account_id": account_id,
            "name": "Upd Deal",
            "amount": 5000.0,
            "currency": "USD",
            "close_date": "2026-12-31T00:00:00",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    return resp.json()["id"]


async def _create_lead(client, headers) -> str:
    resp = await client.post(
        "/leads",
        json={
            "first_name": "Upd",
            "last_name": "Lead",
            "email": "updlead@example.com",
            "company": "Upd Inc",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    return resp.json()["id"]


async def _create_case(client, headers, account_id, num) -> str:
    resp = await client.post(
        "/cases",
        json={
            "subject": "Upd Case",
            "description": "Update me",
            "account_id": account_id,
            "owner_id": TEST_USER_ID,
            "case_number": f"UPD-{num}",
        },
        headers=headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_update_contact():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        cid = await _create_contact(c, h, aid)
        resp = await c.put(
            f"/contacts/{cid}",
            json={
                "account_id": aid,
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
                "owner_id": TEST_USER_ID,
            },
            headers=h,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Updated"


@pytest.mark.asyncio
async def test_update_opportunity():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        oid = await _create_opportunity(c, h, aid)
        resp = await c.put(
            f"/opportunities/{oid}",
            json={
                "account_id": aid,
                "name": "Updated Deal",
                "amount": 10000.0,
                "currency": "EUR",
                "close_date": "2027-06-30T00:00:00",
                "owner_id": TEST_USER_ID,
            },
            headers=h,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Deal"


@pytest.mark.asyncio
async def test_deactivate_account():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        resp = await c.post(f"/accounts/{aid}/deactivate", headers=h)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_deactivate_missing_account_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/accounts/00000000-0000-0000-0000-000000000099/deactivate",
            headers=_auth(),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_close_case():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        h = _auth()
        aid = await _create_account(c, h)
        caseid = await _create_case(c, h, aid, "CL01")
        # Transition to in_progress first (required before resolve)
        await c.patch(
            f"/cases/{caseid}/status",
            json={"status": "in_progress"},
            headers=h,
        )
        # Resolve (required before close)
        await c.post(
            f"/cases/{caseid}/resolve",
            json={
                "resolution_notes": "Fixed",
                "resolved_by": TEST_USER_ID,
            },
            headers=h,
        )
        resp = await c.post(f"/cases/{caseid}/close", headers=h)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_close_missing_case_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/cases/00000000-0000-0000-0000-000000000099/close",
            headers=_auth(),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_not_found_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.put(
            "/contacts/00000000-0000-0000-0000-000000000099",
            json={
                "account_id": "a",
                "first_name": "X",
                "last_name": "Y",
                "email": "x@y.com",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth(),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_opportunity_not_found_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.put(
            "/opportunities/00000000-0000-0000-0000-000000000099",
            json={
                "account_id": "a",
                "name": "X",
                "amount": 1.0,
                "currency": "USD",
                "close_date": "2027-01-01T00:00:00",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth(),
        )
        assert resp.status_code == 404
