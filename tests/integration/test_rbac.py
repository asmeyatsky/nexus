"""Tests for RBAC permission enforcement on API endpoints."""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from httpx import AsyncClient, ASGITransport
from presentation.api.main import app
from infrastructure.adapters.auth import create_access_token

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _auth(role: str) -> dict:
    token = create_access_token(
        data={"sub": TEST_USER_ID, "email": "test@example.com", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_read_only_cannot_create_account():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/accounts",
            json={
                "name": "Blocked",
                "industry": "technology",
                "territory": "north_america",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth("read_only"),
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_read_only_cannot_create_contact():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/contacts",
            json={
                "account_id": "x",
                "first_name": "A",
                "last_name": "B",
                "email": "a@b.com",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth("read_only"),
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_support_user_cannot_create_opportunity():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/opportunities",
            json={
                "account_id": "x",
                "name": "Deal",
                "amount": 100.0,
                "currency": "USD",
                "close_date": "2026-12-31T00:00:00",
                "owner_id": TEST_USER_ID,
            },
            headers=_auth("support_user"),
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_marketing_user_cannot_create_case():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/cases",
            json={
                "subject": "Blocked",
                "description": "No access",
                "account_id": "x",
                "owner_id": TEST_USER_ID,
                "case_number": "RBAC-001",
            },
            headers=_auth("marketing_user"),
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_read_only_can_list_accounts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/accounts", headers=_auth("read_only"))
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_read_only_cannot_delete_account():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.delete("/accounts/some-id", headers=_auth("read_only"))
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_metrics_requires_audit_permission():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/metrics", headers=_auth("read_only"))
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_metrics():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/metrics", headers=_auth("admin"))
        assert resp.status_code == 200
        data = resp.json()
        assert "http_requests_total" in data
