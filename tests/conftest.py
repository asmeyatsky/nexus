"""
Test Configuration & Fixtures

Shared fixtures for all test suites.
"""

import os
import pytest
import asyncio

# Set test environment before importing settings
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def account_repo():
    from infrastructure.mcp_servers.nexus_crm_server import InMemoryAccountRepository

    return InMemoryAccountRepository()


@pytest.fixture
def contact_repo():
    from infrastructure.mcp_servers.nexus_crm_server import InMemoryContactRepository

    return InMemoryContactRepository()


@pytest.fixture
def opportunity_repo():
    from infrastructure.mcp_servers.nexus_crm_server import (
        InMemoryOpportunityRepository,
    )

    return InMemoryOpportunityRepository()


@pytest.fixture
def lead_repo():
    from infrastructure.mcp_servers.nexus_crm_server import InMemoryLeadRepository

    return InMemoryLeadRepository()


@pytest.fixture
def case_repo():
    from infrastructure.mcp_servers.nexus_crm_server import InMemoryCaseRepository

    return InMemoryCaseRepository()


@pytest.fixture
def event_bus():
    from infrastructure.adapters import InMemoryEventBusAdapter

    return InMemoryEventBusAdapter()


@pytest.fixture
def audit_log():
    from infrastructure.adapters import ConsoleAuditLogAdapter

    return ConsoleAuditLogAdapter()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests to prevent 429 errors."""
    from infrastructure.adapters.security import rate_limiter

    rate_limiter._buckets.clear()
    yield
    rate_limiter._buckets.clear()
