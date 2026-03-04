"""
Integration tests for state machine error handling via the API.

Tests that invalid state transitions return 400 via the global error handler,
and that missing resources return 404.
"""

import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from presentation.api.main import app
from infrastructure.adapters.auth import create_access_token

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _auth_headers(role: str = "admin") -> dict:
    token = create_access_token(
        data={"sub": TEST_USER_ID, "email": "admin@example.com", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


async def _create_account(client: AsyncClient) -> str:
    resp = await client.post(
        "/accounts",
        json={
            "name": "State Machine Test Corp",
            "industry": "technology",
            "territory": "north_america",
            "owner_id": TEST_USER_ID,
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200, f"Failed to create account: {resp.text}"
    return resp.json()["id"]


async def _create_opportunity(client: AsyncClient, account_id: str) -> str:
    resp = await client.post(
        "/opportunities",
        json={
            "account_id": account_id,
            "name": "Test Opportunity",
            "amount": 50000.0,
            "currency": "USD",
            "close_date": "2030-12-31T00:00:00Z",
            "owner_id": TEST_USER_ID,
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200, f"Failed to create opportunity: {resp.text}"
    return resp.json()["id"]


async def _create_case(client: AsyncClient, account_id: str, case_number: str) -> str:
    resp = await client.post(
        "/cases",
        json={
            "subject": "Test Case",
            "description": "Something went wrong and needs attention",
            "account_id": account_id,
            "owner_id": TEST_USER_ID,
            "case_number": case_number,
            "priority": "medium",
            "origin": "web",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200, f"Failed to create case: {resp.text}"
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_closed_won_opportunity_cannot_change_stage_returns_400():
    """Move opportunity to closed_won, then try another stage change - should return 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        account_id = await _create_account(client)
        opp_id = await _create_opportunity(client, account_id)

        # Move to closed_won
        resp = await client.patch(
            f"/opportunities/{opp_id}/stage",
            json={"stage": "closed_won"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200

        # Try to change stage again from closed_won - invalid transition
        resp = await client.patch(
            f"/opportunities/{opp_id}/stage",
            json={"stage": "qualification"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_case_invalid_transition_new_to_resolved_returns_400():
    """Try to change case status from new -> resolved (invalid) - should return 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        account_id = await _create_account(client)
        case_id = await _create_case(client, account_id, f"CASE-SM-{uuid4().hex[:6]}")

        # Try invalid transition: new -> resolved
        resp = await client.patch(
            f"/cases/{case_id}/status",
            json={"status": "resolved"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_closed_case_status_change_returns_400():
    """Close a case, then try to change its status - should return 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        account_id = await _create_account(client)
        case_id = await _create_case(client, account_id, f"CASE-CL-{uuid4().hex[:6]}")

        # Close the case (new -> closed is valid)
        resp = await client.patch(
            f"/cases/{case_id}/status",
            json={"status": "closed"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200

        # Try to change status of a closed case - should fail
        resp = await client.patch(
            f"/cases/{case_id}/status",
            json={"status": "in_progress"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_nonexistent_opportunity_stage_returns_404():
    """Try to update stage of a non-existent opportunity - should return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_id = str(uuid4())
        resp = await client.patch(
            f"/opportunities/{fake_id}/stage",
            json={"stage": "qualification"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_case_status_returns_404():
    """Try to update status of a non-existent case - should return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_id = str(uuid4())
        resp = await client.patch(
            f"/cases/{fake_id}/status",
            json={"status": "in_progress"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 404
