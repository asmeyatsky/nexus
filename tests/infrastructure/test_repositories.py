"""
Repository Implementation Tests

Tests for in-memory repository adapters.
"""

import pytest
from domain.entities.account import Account


@pytest.mark.asyncio
async def test_account_save_and_retrieve(account_repo):
    account = Account.create(
        id="acc-test-1", name="Repo Test Corp",
        industry="technology", territory="north_america",
        owner_id="user-1",
    )
    saved = await account_repo.save(account)
    assert saved.id == "acc-test-1"

    retrieved = await account_repo.get_by_id("acc-test-1")
    assert retrieved is not None
    assert retrieved.name == "Repo Test Corp"


@pytest.mark.asyncio
async def test_account_get_all(account_repo):
    for i in range(5):
        account = Account.create(
            id=f"acc-list-{i}", name=f"Corp {i}",
            industry="finance", territory="europe",
            owner_id="user-1",
        )
        await account_repo.save(account)

    all_accounts = await account_repo.get_all(limit=10, offset=0)
    assert len(all_accounts) >= 5


@pytest.mark.asyncio
async def test_account_delete(account_repo):
    account = Account.create(
        id="acc-del-1", name="Delete Me",
        industry="retail", territory="asia_pacific",
        owner_id="user-1",
    )
    await account_repo.save(account)
    await account_repo.delete("acc-del-1")

    retrieved = await account_repo.get_by_id("acc-del-1")
    assert retrieved is None
