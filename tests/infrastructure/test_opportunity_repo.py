"""
Tests for InMemoryOpportunityRepository.
"""

import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta

from domain.entities.opportunity import Opportunity, OpportunityStage
from domain.value_objects import Money
from infrastructure.mcp_servers.nexus_crm_server import InMemoryOpportunityRepository


def make_opportunity(account_id=None) -> Opportunity:
    return Opportunity.create(
        account_id=account_id or uuid4(),
        name="Big Deal",
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_opportunity_repo_save_and_get_by_id():
    repo = InMemoryOpportunityRepository()
    opp = make_opportunity()
    await repo.save(opp)

    found = await repo.get_by_id(opp.id)
    assert found is not None
    assert str(found.id) == str(opp.id)
    assert found.name == "Big Deal"


@pytest.mark.asyncio
async def test_opportunity_repo_get_open_opportunities():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    open_opp1 = make_opportunity(account_id)
    open_opp2 = make_opportunity(account_id)
    closed_won = make_opportunity(account_id).change_stage(OpportunityStage.CLOSED_WON)
    closed_lost = make_opportunity(account_id).change_stage(OpportunityStage.CLOSED_LOST)

    await repo.save(open_opp1)
    await repo.save(open_opp2)
    await repo.save(closed_won)
    await repo.save(closed_lost)

    open_opps = await repo.get_open_opportunities()
    assert len(open_opps) == 2
    for o in open_opps:
        assert not o.is_closed


@pytest.mark.asyncio
async def test_opportunity_repo_get_all_with_pagination():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    for _ in range(5):
        await repo.save(make_opportunity(account_id))

    all_opps = await repo.get_all(limit=100, offset=0)
    assert len(all_opps) == 5

    page1 = await repo.get_all(limit=2, offset=0)
    assert len(page1) == 2

    page2 = await repo.get_all(limit=2, offset=2)
    assert len(page2) == 2

    page3 = await repo.get_all(limit=10, offset=4)
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_opportunity_repo_delete():
    repo = InMemoryOpportunityRepository()
    opp = make_opportunity()
    await repo.save(opp)

    await repo.delete(opp.id)

    found = await repo.get_by_id(opp.id)
    assert found is None
