"""
Integration tests for reports, analytics, and report builder endpoints.

Tests coverage for:
- GET /reports/pipeline-summary
- GET /reports/lead-funnel
- GET /reports/case-metrics
- GET /reports/activity-summary
- GET /analytics/revenue-forecast
- GET /analytics/lead-scores
- GET /analytics/trends
- GET /analytics/win-loss
- POST /reports/query (with various filters and operators)
- POST /reports/cross-query
- List endpoints with filters and search
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


def _auth(role: str = "admin") -> dict:
    token = create_access_token(
        data={"sub": TEST_USER_ID, "email": "test@example.com", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


# Helper functions to create entities via the API
async def _create_account(client, headers, name="Test Corp") -> str:
    resp = await client.post(
        "/accounts",
        json={
            "name": name,
            "industry": "technology",
            "territory": "north_america",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_contact(
    client, headers, account_id, first_name="John", last_name="Doe", email="john@example.com"
) -> str:
    resp = await client.post(
        "/contacts",
        json={
            "account_id": account_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_opportunity(
    client, headers, account_id, name="Big Deal", amount=50000.0
) -> str:
    resp = await client.post(
        "/opportunities",
        json={
            "account_id": account_id,
            "name": name,
            "amount": amount,
            "currency": "USD",
            "close_date": "2026-12-31T00:00:00",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_lead(client, headers, email="lead@example.com") -> str:
    resp = await client.post(
        "/leads",
        json={
            "first_name": "Lead",
            "last_name": "Test",
            "email": email,
            "company": "Lead Inc",
            "owner_id": TEST_USER_ID,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def _create_case(client, headers, account_id, case_number="TC-001") -> str:
    resp = await client.post(
        "/cases",
        json={
            "subject": "Test Case",
            "description": "Issue desc",
            "account_id": account_id,
            "owner_id": TEST_USER_ID,
            "case_number": case_number,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ============================================================================
# REPORT ENDPOINTS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_pipeline_summary_returns_expected_fields():
    """Test GET /reports/pipeline-summary returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id)

        resp = await client.get("/reports/pipeline-summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "by_stage" in data
        assert "total_pipeline_value" in data
        assert "total_weighted_pipeline" in data
        assert "won_count" in data
        assert "lost_count" in data
        assert "open_count" in data


@pytest.mark.asyncio
async def test_pipeline_summary_without_auth_returns_401():
    """Test GET /reports/pipeline-summary requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/reports/pipeline-summary")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_lead_funnel_returns_expected_fields():
    """Test GET /reports/lead-funnel returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="funnel1@example.com")
        await _create_lead(client, headers, email="funnel2@example.com")

        resp = await client.get("/reports/lead-funnel", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "by_status" in data
        assert "total" in data
        assert isinstance(data["by_status"], dict)
        assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_lead_funnel_without_auth_returns_401():
    """Test GET /reports/lead-funnel requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/reports/lead-funnel")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_case_metrics_returns_expected_fields():
    """Test GET /reports/case-metrics returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_case(client, headers, account_id, case_number="CM-001")

        resp = await client.get("/reports/case-metrics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "open_count" in data
        assert "resolved_count" in data
        assert "closed_count" in data
        assert "avg_resolution_hours" in data
        assert "by_priority" in data
        assert "by_status" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_case_metrics_without_auth_returns_401():
    """Test GET /reports/case-metrics requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/reports/case-metrics")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_activity_summary_day_period():
    """Test GET /reports/activity-summary with day period."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_contact(client, headers, account_id)
        await _create_opportunity(client, headers, account_id)
        await _create_lead(client, headers, email="activity1@example.com")

        resp = await client.get("/reports/activity-summary?period=day", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "accounts" in data
        assert "contacts" in data
        assert "opportunities" in data
        assert "leads" in data
        assert "cases" in data


@pytest.mark.asyncio
async def test_activity_summary_month_period():
    """Test GET /reports/activity-summary with month period."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")

        resp = await client.get("/reports/activity-summary?period=month", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "accounts" in data


# ============================================================================
# ANALYTICS ENDPOINTS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_revenue_forecast_returns_expected_fields():
    """Test GET /analytics/revenue-forecast returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, amount=100000.0)

        resp = await client.get("/analytics/revenue-forecast", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "weighted_pipeline" in data
        assert "best_case" in data
        assert "committed" in data
        assert "closed_won_total" in data
        assert "by_month" in data
        assert "by_stage" in data


@pytest.mark.asyncio
async def test_revenue_forecast_without_auth_returns_401():
    """Test GET /analytics/revenue-forecast requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analytics/revenue-forecast")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_lead_scores_returns_expected_fields():
    """Test GET /analytics/lead-scores returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="score1@example.com")
        await _create_lead(client, headers, email="score2@example.com")

        resp = await client.get("/analytics/lead-scores", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "leads" in data
        assert "avg_score" in data
        assert "distribution" in data
        assert "total" in data
        assert isinstance(data["leads"], list)
        assert "hot" in data["distribution"]
        assert "warm" in data["distribution"]
        assert "cold" in data["distribution"]


@pytest.mark.asyncio
async def test_lead_scores_without_auth_returns_401():
    """Test GET /analytics/lead-scores requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analytics/lead-scores")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_trends_with_leads_entity():
    """Test GET /analytics/trends with leads entity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="trend1@example.com")

        resp = await client.get(
            "/analytics/trends?entity=leads&period=month", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "grouped" in data
        assert data["grouped"] is False


@pytest.mark.asyncio
async def test_trends_with_opportunities_entity_and_group_by():
    """Test GET /analytics/trends with opportunities and group_by."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id)

        resp = await client.get(
            "/analytics/trends?entity=opportunities&period=day&group_by=stage",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "grouped" in data
        assert data["grouped"] is True


@pytest.mark.asyncio
async def test_win_loss_returns_expected_fields():
    """Test GET /analytics/win-loss returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, amount=50000.0)

        resp = await client.get("/analytics/win-loss", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "win_rate" in data
        assert "avg_cycle_days" in data
        assert "avg_won_amount" in data
        assert "avg_lost_amount" in data
        assert "won_count" in data
        assert "lost_count" in data
        assert "by_source" in data
        assert "by_month" in data


@pytest.mark.asyncio
async def test_win_loss_without_auth_returns_401():
    """Test GET /analytics/win-loss requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analytics/win-loss")
        assert resp.status_code in (401, 403)


# ============================================================================
# REPORT BUILDER ENDPOINTS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_report_query_basic_accounts():
    """Test POST /reports/query with basic accounts query."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_account(client, headers, name="Query Test Corp")

        resp = await client.post(
            "/reports/query",
            json={"entity": "accounts", "columns": ["name", "industry"], "limit": 10},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "type" in data
        assert data["type"] == "tabular"
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_report_query_with_filters():
    """Test POST /reports/query with filters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="filter1@example.com")
        await _create_lead(client, headers, email="filter2@example.com")

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "leads",
                "filters": [{"field": "status", "operator": "eq", "value": "new"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "type" in data
        assert "data" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_report_query_with_group_by():
    """Test POST /reports/query with group_by."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="group1@example.com")
        await _create_lead(client, headers, email="group2@example.com")

        resp = await client.post(
            "/reports/query",
            json={"entity": "leads", "group_by": "status"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "type" in data
        assert data["type"] == "aggregated"
        assert "data" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_report_query_unknown_entity_returns_400():
    """Test POST /reports/query with unknown entity returns 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")

        resp = await client.post(
            "/reports/query",
            json={"entity": "unknown_entity", "columns": ["id"]},
            headers=headers,
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_report_query_filter_contains_operator():
    """Test POST /reports/query with contains filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="contains@example.com")

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "leads",
                "filters": [{"field": "company", "operator": "contains", "value": "Inc"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data


@pytest.mark.asyncio
async def test_report_query_filter_neq_operator():
    """Test POST /reports/query with neq filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="neq@example.com")

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "leads",
                "filters": [{"field": "status", "operator": "neq", "value": "qualified"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_filter_gt_operator():
    """Test POST /reports/query with gt filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, amount=100000.0)

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "opportunities",
                "filters": [{"field": "amount", "operator": "gt", "value": "50000"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_filter_lt_operator():
    """Test POST /reports/query with lt filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, amount=25000.0)

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "opportunities",
                "filters": [{"field": "amount", "operator": "lt", "value": "50000"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_filter_gte_operator():
    """Test POST /reports/query with gte filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, amount=50000.0)

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "opportunities",
                "filters": [{"field": "amount", "operator": "gte", "value": "50000"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_filter_lte_operator():
    """Test POST /reports/query with lte filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, amount=25000.0)

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "opportunities",
                "filters": [{"field": "amount", "operator": "lte", "value": "50000"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_filter_is_empty_operator():
    """Test POST /reports/query with is_empty filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="empty@example.com")

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "leads",
                "filters": [{"field": "company", "operator": "is_empty", "value": ""}],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_filter_is_not_empty_operator():
    """Test POST /reports/query with is_not_empty filter operator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="notempty@example.com")

        resp = await client.post(
            "/reports/query",
            json={
                "entity": "leads",
                "filters": [
                    {"field": "company", "operator": "is_not_empty", "value": ""}
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_query_without_auth_returns_401():
    """Test POST /reports/query requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/reports/query", json={"entity": "accounts", "columns": ["name"]}
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cross_query_accounts_opportunities():
    """Test POST /reports/cross-query between accounts and opportunities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers, name="Cross Query Account")
        await _create_opportunity(client, headers, account_id, name="Big Deal")

        resp = await client.post(
            "/reports/cross-query",
            json={
                "primary_entity": "accounts",
                "related_entity": "opportunities",
                "related_filters": [{"field": "name", "operator": "contains", "value": "deal"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "type" in data
        assert data["type"] == "tabular"
        assert "data" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_cross_query_unknown_entity_returns_400():
    """Test POST /reports/cross-query with unknown entity returns 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")

        resp = await client.post(
            "/reports/cross-query",
            json={
                "primary_entity": "unknown",
                "related_entity": "opportunities",
                "related_filters": [],
            },
            headers=headers,
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cross_query_without_auth_returns_401():
    """Test POST /reports/cross-query requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/reports/cross-query",
            json={
                "primary_entity": "accounts",
                "related_entity": "opportunities",
                "related_filters": [],
            },
        )
        assert resp.status_code in (401, 403)


# ============================================================================
# LIST ENDPOINTS WITH FILTERS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_list_accounts_with_search_filter():
    """Test GET /accounts?search=Test returns matching items."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_account(client, headers, name="Test Search Corp")

        resp = await client.get("/accounts?search=Search", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_list_leads_with_status_filter():
    """Test GET /leads?status=new returns filtered items."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        await _create_lead(client, headers, email="status@example.com")

        resp = await client.get("/leads?status=new", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_list_cases_with_priority_filter():
    """Test GET /cases?priority=medium returns filtered items."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_case(client, headers, account_id, case_number="PRI-001")

        resp = await client.get("/cases?priority=medium", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_list_opportunities_with_sorting():
    """Test GET /opportunities?sort_by=name&sort_order=asc returns sorted results."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _auth("admin")
        account_id = await _create_account(client, headers)
        await _create_opportunity(client, headers, account_id, name="Zulu Deal")
        await _create_opportunity(client, headers, account_id, name="Alpha Deal")

        resp = await client.get(
            "/opportunities?sort_by=name&sort_order=asc", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
