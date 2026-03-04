"""
Tests for InMemoryLeadRepository.
"""

import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from uuid import uuid4

from domain.entities.lead import Lead, LeadStatus
from domain.value_objects import Email
from infrastructure.mcp_servers.nexus_crm_server import InMemoryLeadRepository


def make_lead(email_suffix="test") -> Lead:
    return Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create(f"jane.{email_suffix}@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_lead_repo_save_and_get_by_id():
    repo = InMemoryLeadRepository()
    lead = make_lead()
    await repo.save(lead)

    found = await repo.get_by_id(lead.id)
    assert found is not None
    assert str(found.id) == str(lead.id)
    assert found.first_name == "Jane"


@pytest.mark.asyncio
async def test_lead_repo_get_by_status():
    repo = InMemoryLeadRepository()

    new_lead = make_lead(email_suffix="new")
    contacted_lead = make_lead(email_suffix="contacted").change_status(LeadStatus.CONTACTED)
    qualified_lead = (
        make_lead(email_suffix="qual")
        .change_status(LeadStatus.CONTACTED)
        .change_status(LeadStatus.QUALIFIED)
    )

    await repo.save(new_lead)
    await repo.save(contacted_lead)
    await repo.save(qualified_lead)

    new_leads = await repo.get_by_status("new")
    assert len(new_leads) == 1

    contacted_leads = await repo.get_by_status("contacted")
    assert len(contacted_leads) == 1

    qualified_leads = await repo.get_by_status("qualified")
    assert len(qualified_leads) == 1


@pytest.mark.asyncio
async def test_lead_repo_get_all_with_pagination():
    repo = InMemoryLeadRepository()

    for i in range(5):
        await repo.save(make_lead(email_suffix=str(i)))

    all_leads = await repo.get_all(limit=100, offset=0)
    assert len(all_leads) == 5

    page1 = await repo.get_all(limit=2, offset=0)
    assert len(page1) == 2

    page2 = await repo.get_all(limit=2, offset=2)
    assert len(page2) == 2

    page3 = await repo.get_all(limit=10, offset=4)
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_lead_repo_delete():
    repo = InMemoryLeadRepository()
    lead = make_lead()
    await repo.save(lead)

    await repo.delete(lead.id)

    found = await repo.get_by_id(lead.id)
    assert found is None
