"""
Query Handler Tests

Tests for CQRS query handlers.
"""

import pytest

from application import (
    CreateAccountCommand,
    GetAccountQuery,
    ListAccountsQuery,
    CreateAccountDTO,
)

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_get_account_by_id(account_repo, event_bus, audit_log):
    # Create
    dto = CreateAccountDTO(
        name="Query Corp",
        industry="retail",
        territory="europe",
        owner_id=TEST_USER_ID,
    )
    cmd = CreateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    created = await cmd.execute(dto)

    # Query
    query = GetAccountQuery(repository=account_repo)
    result = await query.execute(created.id)
    assert result is not None
    assert result.name == "Query Corp"


@pytest.mark.asyncio
async def test_get_nonexistent_account(account_repo):
    query = GetAccountQuery(repository=account_repo)
    result = await query.execute("00000000-0000-0000-0000-000000000099")
    assert result is None


@pytest.mark.asyncio
async def test_list_accounts(account_repo, event_bus, audit_log):
    cmd = CreateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    for i in range(5):
        await cmd.execute(
            CreateAccountDTO(
                name=f"Corp {i}",
                industry="technology",
                territory="north_america",
                owner_id=TEST_USER_ID,
            )
        )

    query = ListAccountsQuery(repository=account_repo)
    results = await query.execute(limit=3, offset=0)
    assert len(results) == 3
