"""
API Integration Tests

Tests for REST API endpoints.
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from httpx import AsyncClient, ASGITransport
from presentation.api.main import app
from infrastructure.adapters.auth import create_access_token

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _get_auth_headers(role: str = "admin") -> dict:
    token = create_access_token(
        data={"sub": TEST_USER_ID, "email": "test@example.com", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in data
        assert "checks" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_account_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/accounts",
            json={
                "name": "Test",
                "industry": "technology",
                "territory": "north_america",
                "owner_id": TEST_USER_ID,
            },
        )
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_account_with_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/accounts",
            json={
                "name": "Auth Test Corp",
                "industry": "technology",
                "territory": "north_america",
                "owner_id": TEST_USER_ID,
            },
            headers=_get_auth_headers("admin"),
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Auth Test Corp"


@pytest.mark.asyncio
async def test_list_accounts_with_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/accounts",
            headers=_get_auth_headers("user"),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
