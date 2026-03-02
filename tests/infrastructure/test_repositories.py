"""
Repository Implementation Tests

Tests for in-memory repository adapters.
"""

import pytest
from uuid import uuid4
from domain.entities.account import Account
from domain.value_objects import Industry, Territory


@pytest.mark.asyncio
async def test_account_save_and_retrieve(account_repo):
    account = Account.create(
        name="Repo Test Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=uuid4(),
    )
    saved = await account_repo.save(account)
    assert saved.name == "Repo Test Corp"

    retrieved = await account_repo.get_by_id(str(account.id))
    assert retrieved is not None
    assert retrieved.name == "Repo Test Corp"


@pytest.mark.asyncio
async def test_account_get_all(account_repo):
    for i in range(5):
        account = Account.create(
            name=f"Corp {i}",
            industry=Industry.from_string("finance"),
            territory=Territory(region="europe"),
            owner_id=uuid4(),
        )
        await account_repo.save(account)

    all_accounts = await account_repo.get_all(limit=10, offset=0)
    assert len(all_accounts) >= 5


@pytest.mark.asyncio
async def test_account_delete(account_repo):
    account = Account.create(
        name="Delete Me",
        industry=Industry.from_string("retail"),
        territory=Territory(region="asia_pacific"),
        owner_id=uuid4(),
    )
    await account_repo.save(account)
    await account_repo.delete(str(account.id))

    retrieved = await account_repo.get_by_id(str(account.id))
    assert retrieved is None
