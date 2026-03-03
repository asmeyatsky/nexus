"""Tests for error handling: 404s, validation errors."""

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


# ---- 404 for missing entities ----


@pytest.mark.asyncio
async def test_get_missing_account_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/accounts/00000000-0000-0000-0000-999999999999", headers=_auth()
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_missing_contact_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/contacts/00000000-0000-0000-0000-999999999999", headers=_auth()
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_missing_opportunity_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/opportunities/00000000-0000-0000-0000-999999999999", headers=_auth()
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_missing_lead_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/leads/00000000-0000-0000-0000-999999999999", headers=_auth()
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_missing_case_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/cases/00000000-0000-0000-0000-999999999999", headers=_auth()
        )
        assert resp.status_code == 404


# ---- Validation errors ----


@pytest.mark.asyncio
async def test_invalid_industry_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/accounts",
            json={
                "name": "Bad Industry",
                "industry": "space_mining",
                "territory": "north_america",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth(),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_territory_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/accounts",
            json={
                "name": "Bad Territory",
                "industry": "technology",
                "territory": "mars",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth(),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_priority_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/cases",
            json={
                "subject": "Bad Priority",
                "description": "test",
                "account_id": "x",
                "owner_id": TEST_USER_ID,
                "case_number": "ERR-001",
                "priority": "ultra",
            },
            headers=_auth(),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_origin_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/cases",
            json={
                "subject": "Bad Origin",
                "description": "test",
                "account_id": "x",
                "owner_id": TEST_USER_ID,
                "case_number": "ERR-002",
                "origin": "carrier_pigeon",
            },
            headers=_auth(),
        )
        assert resp.status_code == 422
