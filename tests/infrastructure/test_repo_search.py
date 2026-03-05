"""
Tests for search() methods on all 5 InMemory*Repository classes.

Covers:
- InMemoryAccountRepository.search()
- InMemoryContactRepository.search()
- InMemoryOpportunityRepository.search()
- InMemoryLeadRepository.search()
- InMemoryCaseRepository.search()

Each test covers: empty search, text search, field filtering, pagination,
sorting, and combined filters.
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC

from domain.entities.account import Account
from domain.entities.contact import Contact
from domain.entities.opportunity import Opportunity, OpportunityStage
from domain.entities.lead import Lead, LeadStatus, LeadRating
from domain.entities.case import Case, CaseStatus, CasePriority, CaseOrigin
from domain.value_objects import Industry, Territory, Email, Money
from infrastructure.mcp_servers.nexus_crm_server import (
    InMemoryAccountRepository,
    InMemoryContactRepository,
    InMemoryOpportunityRepository,
    InMemoryLeadRepository,
    InMemoryCaseRepository,
)


# ============================================================================
# Account Repository Search Tests
# ============================================================================


def make_account(name="Test Corp", industry=None, territory=None) -> Account:
    return Account.create(
        name=name,
        industry=industry or Industry.from_string("technology"),
        territory=territory or Territory(region="north_america"),
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_account_search_empty_returns_all():
    repo = InMemoryAccountRepository()
    owner_id = uuid4()

    acct1 = Account.create(
        name="Acme Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    acct2 = Account.create(
        name="Tech Solutions",
        industry=Industry.from_string("consulting"),
        territory=Territory(region="EMEA"),
        owner_id=owner_id,
    )
    acct3 = Account.create(
        name="Healthcare Inc",
        industry=Industry.from_string("healthcare"),
        territory=Territory(region="APAC"),
        owner_id=uuid4(),
    )

    await repo.save(acct1)
    await repo.save(acct2)
    await repo.save(acct3)

    results, total = await repo.search()
    assert len(results) == 3
    assert total == 3


@pytest.mark.asyncio
async def test_account_search_by_name():
    repo = InMemoryAccountRepository()
    owner_id = uuid4()

    acct1 = Account.create(
        name="Acme Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    acct2 = Account.create(
        name="Another Company",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    acct3 = Account.create(
        name="Solutions Ltd",
        industry=Industry.from_string("consulting"),
        territory=Territory(region="EMEA"),
        owner_id=owner_id,
    )

    await repo.save(acct1)
    await repo.save(acct2)
    await repo.save(acct3)

    results, total = await repo.search(search="acme")
    assert len(results) == 1
    assert total == 1
    assert results[0].name == "Acme Corp"

    results, total = await repo.search(search="another")
    assert total == 1
    assert len(results) == 1
    assert results[0].name == "Another Company"


@pytest.mark.asyncio
async def test_account_search_by_industry():
    repo = InMemoryAccountRepository()
    owner_id = uuid4()

    acct1 = Account.create(
        name="Acme Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    acct2 = Account.create(
        name="Tech Consulting",
        industry=Industry.from_string("consulting"),
        territory=Territory(region="EMEA"),
        owner_id=owner_id,
    )
    acct3 = Account.create(
        name="Health Org",
        industry=Industry.from_string("technology"),
        territory=Territory(region="APAC"),
        owner_id=owner_id,
    )

    await repo.save(acct1)
    await repo.save(acct2)
    await repo.save(acct3)

    results, total = await repo.search(industry="technology")
    assert len(results) == 2
    assert total == 2
    for acct in results:
        assert acct.industry.type.value == "technology"


@pytest.mark.asyncio
async def test_account_search_by_owner():
    repo = InMemoryAccountRepository()
    owner_id_a = uuid4()
    owner_id_b = uuid4()

    acct1 = Account.create(
        name="Acme Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id_a,
    )
    acct2 = Account.create(
        name="Euro Company",
        industry=Industry.from_string("technology"),
        territory=Territory(region="emea"),
        owner_id=owner_id_a,
    )
    acct3 = Account.create(
        name="Asia Company",
        industry=Industry.from_string("technology"),
        territory=Territory(region="apac"),
        owner_id=owner_id_b,
    )

    await repo.save(acct1)
    await repo.save(acct2)
    await repo.save(acct3)

    results, total = await repo.search(owner_id=owner_id_a)
    assert len(results) == 2
    assert total == 2
    for acct in results:
        assert str(acct.owner_id) == str(owner_id_a)


@pytest.mark.asyncio
async def test_account_search_pagination():
    repo = InMemoryAccountRepository()
    owner_id = uuid4()

    for i in range(5):
        acct = Account.create(
            name=f"Company {i}",
            industry=Industry.from_string("technology"),
            territory=Territory(region="north_america"),
            owner_id=owner_id,
        )
        await repo.save(acct)

    results, total = await repo.search(limit=2, offset=0)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=2)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=4)
    assert len(results) == 1
    assert total == 5


@pytest.mark.asyncio
async def test_account_search_sort_order():
    repo = InMemoryAccountRepository()
    owner_id = uuid4()

    # Create accounts with different creation times
    acct1 = Account.create(
        name="Aaa Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    await repo.save(acct1)

    acct2 = Account.create(
        name="Bbb Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    await repo.save(acct2)

    acct3 = Account.create(
        name="Ccc Corp",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id,
    )
    await repo.save(acct3)

    # Descending (most recent first, default)
    results, _ = await repo.search(sort_by="created_at", sort_order="desc")
    assert results[0].name == "Ccc Corp"
    assert results[2].name == "Aaa Corp"

    # Ascending (oldest first)
    results, _ = await repo.search(sort_by="created_at", sort_order="asc")
    assert results[0].name == "Aaa Corp"
    assert results[2].name == "Ccc Corp"


@pytest.mark.asyncio
async def test_account_search_combined_filters():
    repo = InMemoryAccountRepository()
    owner_id_a = uuid4()
    owner_id_b = uuid4()

    acct1 = Account.create(
        name="Acme Tech",
        industry=Industry.from_string("technology"),
        territory=Territory(region="north_america"),
        owner_id=owner_id_a,
    )
    acct2 = Account.create(
        name="Tech Solutions",
        industry=Industry.from_string("consulting"),
        territory=Territory(region="north_america"),
        owner_id=owner_id_a,
    )
    acct3 = Account.create(
        name="Acme Health",
        industry=Industry.from_string("healthcare"),
        territory=Territory(region="EMEA"),
        owner_id=owner_id_b,
    )

    await repo.save(acct1)
    await repo.save(acct2)
    await repo.save(acct3)

    results, total = await repo.search(
        search="acme", industry="technology", owner_id=owner_id_a
    )
    assert len(results) == 1
    assert total == 1
    assert results[0].name == "Acme Tech"


# ============================================================================
# Contact Repository Search Tests
# ============================================================================


def make_contact(
    first_name="John", last_name="Doe", account_id=None
) -> Contact:
    return Contact.create(
        first_name=first_name,
        last_name=last_name,
        email=Email.create(f"{first_name.lower()}@example.com"),
        account_id=account_id or uuid4(),
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_contact_search_empty_returns_all():
    repo = InMemoryContactRepository()
    account_id = uuid4()

    contact1 = Contact.create(
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice@example.com"),
        account_id=account_id,
        owner_id=uuid4(),
    )
    contact2 = Contact.create(
        first_name="Bob",
        last_name="Jones",
        email=Email.create("bob@example.com"),
        account_id=account_id,
        owner_id=uuid4(),
    )
    contact3 = Contact.create(
        first_name="Charlie",
        last_name="Brown",
        email=Email.create("charlie@example.com"),
        account_id=uuid4(),
        owner_id=uuid4(),
    )

    await repo.save(contact1)
    await repo.save(contact2)
    await repo.save(contact3)

    results, total = await repo.search()
    assert len(results) == 3
    assert total == 3


@pytest.mark.asyncio
async def test_contact_search_by_name():
    repo = InMemoryContactRepository()
    account_id = uuid4()

    contact1 = Contact.create(
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice@example.com"),
        account_id=account_id,
        owner_id=uuid4(),
    )
    contact2 = Contact.create(
        first_name="Bob",
        last_name="Alice",
        email=Email.create("bob@example.com"),
        account_id=account_id,
        owner_id=uuid4(),
    )
    contact3 = Contact.create(
        first_name="Charlie",
        last_name="Brown",
        email=Email.create("charlie@example.com"),
        account_id=account_id,
        owner_id=uuid4(),
    )

    await repo.save(contact1)
    await repo.save(contact2)
    await repo.save(contact3)

    results, total = await repo.search(search="alice")
    assert len(results) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_contact_search_by_account():
    repo = InMemoryContactRepository()
    account_id_a = uuid4()
    account_id_b = uuid4()

    contact1 = Contact.create(
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice@example.com"),
        account_id=account_id_a,
        owner_id=uuid4(),
    )
    contact2 = Contact.create(
        first_name="Bob",
        last_name="Jones",
        email=Email.create("bob@example.com"),
        account_id=account_id_a,
        owner_id=uuid4(),
    )
    contact3 = Contact.create(
        first_name="Charlie",
        last_name="Brown",
        email=Email.create("charlie@example.com"),
        account_id=account_id_b,
        owner_id=uuid4(),
    )

    await repo.save(contact1)
    await repo.save(contact2)
    await repo.save(contact3)

    results, total = await repo.search(account_id=account_id_a)
    assert len(results) == 2
    assert total == 2
    for contact in results:
        assert str(contact.account_id) == str(account_id_a)


@pytest.mark.asyncio
async def test_contact_search_by_owner():
    repo = InMemoryContactRepository()
    account_id = uuid4()
    owner_id_a = uuid4()
    owner_id_b = uuid4()

    contact1 = Contact.create(
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice@example.com"),
        account_id=account_id,
        owner_id=owner_id_a,
    )
    contact2 = Contact.create(
        first_name="Bob",
        last_name="Jones",
        email=Email.create("bob@example.com"),
        account_id=account_id,
        owner_id=owner_id_a,
    )
    contact3 = Contact.create(
        first_name="Charlie",
        last_name="Brown",
        email=Email.create("charlie@example.com"),
        account_id=account_id,
        owner_id=owner_id_b,
    )

    await repo.save(contact1)
    await repo.save(contact2)
    await repo.save(contact3)

    results, total = await repo.search(owner_id=owner_id_a)
    assert len(results) == 2
    assert total == 2
    for contact in results:
        assert str(contact.owner_id) == str(owner_id_a)


@pytest.mark.asyncio
async def test_contact_search_pagination():
    repo = InMemoryContactRepository()
    account_id = uuid4()

    for i in range(5):
        contact = Contact.create(
            first_name=f"Contact{i}",
            last_name="Test",
            email=Email.create(f"contact{i}@example.com"),
            account_id=account_id,
            owner_id=uuid4(),
        )
        await repo.save(contact)

    results, total = await repo.search(limit=2, offset=0)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=2)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=4)
    assert len(results) == 1
    assert total == 5


@pytest.mark.asyncio
async def test_contact_search_sort_order():
    repo = InMemoryContactRepository()
    account_id = uuid4()
    owner_id = uuid4()

    contact1 = Contact.create(
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice@example.com"),
        account_id=account_id,
        owner_id=owner_id,
    )
    await repo.save(contact1)

    contact2 = Contact.create(
        first_name="Bob",
        last_name="Jones",
        email=Email.create("bob@example.com"),
        account_id=account_id,
        owner_id=owner_id,
    )
    await repo.save(contact2)

    contact3 = Contact.create(
        first_name="Charlie",
        last_name="Brown",
        email=Email.create("charlie@example.com"),
        account_id=account_id,
        owner_id=owner_id,
    )
    await repo.save(contact3)

    # Descending
    results, _ = await repo.search(sort_by="created_at", sort_order="desc")
    assert results[0].first_name == "Charlie"
    assert results[2].first_name == "Alice"

    # Ascending
    results, _ = await repo.search(sort_by="created_at", sort_order="asc")
    assert results[0].first_name == "Alice"
    assert results[2].first_name == "Charlie"


@pytest.mark.asyncio
async def test_contact_search_combined_filters():
    repo = InMemoryContactRepository()
    account_id_a = uuid4()
    account_id_b = uuid4()
    owner_id = uuid4()

    contact1 = Contact.create(
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice@example.com"),
        account_id=account_id_a,
        owner_id=owner_id,
    )
    contact2 = Contact.create(
        first_name="Alice",
        last_name="Jones",
        email=Email.create("alice.jones@example.com"),
        account_id=account_id_b,
        owner_id=owner_id,
    )
    contact3 = Contact.create(
        first_name="Bob",
        last_name="Brown",
        email=Email.create("bob@example.com"),
        account_id=account_id_a,
        owner_id=uuid4(),
    )

    await repo.save(contact1)
    await repo.save(contact2)
    await repo.save(contact3)

    results, total = await repo.search(search="alice", account_id=account_id_a)
    assert len(results) == 1
    assert total == 1
    assert results[0].first_name == "Alice"
    assert str(results[0].account_id) == str(account_id_a)


# ============================================================================
# Opportunity Repository Search Tests
# ============================================================================


def make_opportunity(name="Big Deal", account_id=None) -> Opportunity:
    return Opportunity.create(
        name=name,
        account_id=account_id or uuid4(),
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_opportunity_search_empty_returns_all():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    opp1 = Opportunity.create(
        name="Deal 1",
        account_id=account_id,
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )
    opp2 = Opportunity.create(
        name="Deal 2",
        account_id=account_id,
        amount=Money.from_float(75000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=60),
        owner_id=uuid4(),
    )
    opp3 = Opportunity.create(
        name="Deal 3",
        account_id=uuid4(),
        amount=Money.from_float(100000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=90),
        owner_id=uuid4(),
    )

    await repo.save(opp1)
    await repo.save(opp2)
    await repo.save(opp3)

    results, total = await repo.search()
    assert len(results) == 3
    assert total == 3


@pytest.mark.asyncio
async def test_opportunity_search_by_name():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    opp1 = Opportunity.create(
        name="Big Enterprise Deal",
        account_id=account_id,
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )
    opp2 = Opportunity.create(
        name="Small Startup Deal",
        account_id=account_id,
        amount=Money.from_float(10000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=60),
        owner_id=uuid4(),
    )

    await repo.save(opp1)
    await repo.save(opp2)

    results, total = await repo.search(search="enterprise")
    assert len(results) == 1
    assert total == 1
    assert results[0].name == "Big Enterprise Deal"


@pytest.mark.asyncio
async def test_opportunity_search_by_stage():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    opp1 = Opportunity.create(
        name="Deal 1",
        account_id=account_id,
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )
    opp2 = (
        Opportunity.create(
            name="Deal 2",
            account_id=account_id,
            amount=Money.from_float(75000.0, "USD"),
            close_date=datetime.now(UTC) + timedelta(days=60),
            owner_id=uuid4(),
        )
    ).change_stage(OpportunityStage.QUALIFICATION)

    opp3 = (
        Opportunity.create(
            name="Deal 3",
            account_id=account_id,
            amount=Money.from_float(100000.0, "USD"),
            close_date=datetime.now(UTC) + timedelta(days=90),
            owner_id=uuid4(),
        )
    ).change_stage(OpportunityStage.QUALIFICATION).change_stage(OpportunityStage.NEEDS_ANALYSIS)

    await repo.save(opp1)
    await repo.save(opp2)
    await repo.save(opp3)

    results, total = await repo.search(stage="qualification")
    assert len(results) == 1
    assert total == 1
    assert results[0].stage == OpportunityStage.QUALIFICATION


@pytest.mark.asyncio
async def test_opportunity_search_by_is_closed():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    opp1 = Opportunity.create(
        name="Open Deal",
        account_id=account_id,
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )
    opp2 = (
        Opportunity.create(
            name="Won Deal",
            account_id=account_id,
            amount=Money.from_float(75000.0, "USD"),
            close_date=datetime.now(UTC) + timedelta(days=60),
            owner_id=uuid4(),
        )
    ).change_stage(OpportunityStage.CLOSED_WON)

    opp3 = (
        Opportunity.create(
            name="Lost Deal",
            account_id=account_id,
            amount=Money.from_float(100000.0, "USD"),
            close_date=datetime.now(UTC) + timedelta(days=90),
            owner_id=uuid4(),
        )
    ).change_stage(OpportunityStage.CLOSED_LOST)

    await repo.save(opp1)
    await repo.save(opp2)
    await repo.save(opp3)

    results, total = await repo.search(is_closed=False)
    assert len(results) == 1
    assert total == 1
    assert not results[0].is_closed

    results, total = await repo.search(is_closed=True)
    assert len(results) == 2
    assert total == 2
    for opp in results:
        assert opp.is_closed


@pytest.mark.asyncio
async def test_opportunity_search_pagination():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    for i in range(5):
        opp = Opportunity.create(
            name=f"Deal {i}",
            account_id=account_id,
            amount=Money.from_float(50000.0 + i * 1000, "USD"),
            close_date=datetime.now(UTC) + timedelta(days=30 + i),
            owner_id=uuid4(),
        )
        await repo.save(opp)

    results, total = await repo.search(limit=2, offset=0)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=2)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=4)
    assert len(results) == 1
    assert total == 5


@pytest.mark.asyncio
async def test_opportunity_search_sort_order():
    repo = InMemoryOpportunityRepository()
    account_id = uuid4()

    opp1 = Opportunity.create(
        name="Deal 1",
        account_id=account_id,
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )
    await repo.save(opp1)

    opp2 = Opportunity.create(
        name="Deal 2",
        account_id=account_id,
        amount=Money.from_float(75000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=60),
        owner_id=uuid4(),
    )
    await repo.save(opp2)

    opp3 = Opportunity.create(
        name="Deal 3",
        account_id=account_id,
        amount=Money.from_float(100000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=90),
        owner_id=uuid4(),
    )
    await repo.save(opp3)

    # Descending
    results, _ = await repo.search(sort_by="created_at", sort_order="desc")
    assert results[0].name == "Deal 3"
    assert results[2].name == "Deal 1"

    # Ascending
    results, _ = await repo.search(sort_by="created_at", sort_order="asc")
    assert results[0].name == "Deal 1"
    assert results[2].name == "Deal 3"


@pytest.mark.asyncio
async def test_opportunity_search_combined_filters():
    repo = InMemoryOpportunityRepository()
    account_id_a = uuid4()
    account_id_b = uuid4()
    owner_id = uuid4()

    opp1 = Opportunity.create(
        name="Big Deal",
        account_id=account_id_a,
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=owner_id,
    )
    opp2 = (
        Opportunity.create(
            name="Another Deal",
            account_id=account_id_a,
            amount=Money.from_float(75000.0, "USD"),
            close_date=datetime.now(UTC) + timedelta(days=60),
            owner_id=owner_id,
        )
    ).change_stage(OpportunityStage.CLOSED_WON)

    opp3 = Opportunity.create(
        name="Small Deal",
        account_id=account_id_b,
        amount=Money.from_float(10000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=90),
        owner_id=uuid4(),
    )

    await repo.save(opp1)
    await repo.save(opp2)
    await repo.save(opp3)

    results, total = await repo.search(
        search="deal", account_id=account_id_a, owner_id=owner_id
    )
    assert len(results) == 2
    assert total == 2
    for opp in results:
        assert str(opp.account_id) == str(account_id_a)
        assert str(opp.owner_id) == str(owner_id)


# ============================================================================
# Lead Repository Search Tests
# ============================================================================


def make_lead(first_name="Jane", last_name="Doe") -> Lead:
    return Lead.create(
        first_name=first_name,
        last_name=last_name,
        email=Email.create(f"{first_name.lower()}@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_lead_search_empty_returns_all():
    repo = InMemoryLeadRepository()

    lead1 = Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )
    lead2 = Lead.create(
        first_name="John",
        last_name="Smith",
        email=Email.create("john@example.com"),
        company="Tech Inc",
        owner_id=uuid4(),
    )
    lead3 = Lead.create(
        first_name="Bob",
        last_name="Johnson",
        email=Email.create("bob@example.com"),
        company="StartUp Co",
        owner_id=uuid4(),
    )

    await repo.save(lead1)
    await repo.save(lead2)
    await repo.save(lead3)

    results, total = await repo.search()
    assert len(results) == 3
    assert total == 3


@pytest.mark.asyncio
async def test_lead_search_by_name():
    repo = InMemoryLeadRepository()

    lead1 = Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )
    lead2 = Lead.create(
        first_name="John",
        last_name="Jane",
        email=Email.create("john@example.com"),
        company="Tech Inc",
        owner_id=uuid4(),
    )
    lead3 = Lead.create(
        first_name="Bob",
        last_name="Johnson",
        email=Email.create("bob@example.com"),
        company="StartUp Co",
        owner_id=uuid4(),
    )

    await repo.save(lead1)
    await repo.save(lead2)
    await repo.save(lead3)

    results, total = await repo.search(search="jane")
    assert len(results) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_lead_search_by_status():
    repo = InMemoryLeadRepository()

    lead1 = Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )
    lead2 = (
        Lead.create(
            first_name="John",
            last_name="Smith",
            email=Email.create("john@example.com"),
            company="Tech Inc",
            owner_id=uuid4(),
        )
    ).change_status(LeadStatus.CONTACTED)

    lead3 = (
        Lead.create(
            first_name="Bob",
            last_name="Johnson",
            email=Email.create("bob@example.com"),
            company="StartUp Co",
            owner_id=uuid4(),
        )
    ).change_status(LeadStatus.QUALIFIED)

    await repo.save(lead1)
    await repo.save(lead2)
    await repo.save(lead3)

    results, total = await repo.search(status="new")
    assert len(results) == 1
    assert total == 1
    assert results[0].status == LeadStatus.NEW

    results, total = await repo.search(status="qualified")
    assert len(results) == 1
    assert total == 1
    assert results[0].status == LeadStatus.QUALIFIED


@pytest.mark.asyncio
async def test_lead_search_by_rating():
    repo = InMemoryLeadRepository()

    lead1 = Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )
    lead2 = (
        Lead.create(
            first_name="John",
            last_name="Smith",
            email=Email.create("john@example.com"),
            company="Tech Inc",
            owner_id=uuid4(),
        )
    ).update_rating(LeadRating.WARM)

    lead3 = (
        Lead.create(
            first_name="Bob",
            last_name="Johnson",
            email=Email.create("bob@example.com"),
            company="StartUp Co",
            owner_id=uuid4(),
        )
    ).update_rating(LeadRating.HOT)

    await repo.save(lead1)
    await repo.save(lead2)
    await repo.save(lead3)

    results, total = await repo.search(rating="warm")
    assert len(results) == 1
    assert total == 1
    assert results[0].rating == LeadRating.WARM

    results, total = await repo.search(rating="hot")
    assert len(results) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_lead_search_pagination():
    repo = InMemoryLeadRepository()

    for i in range(5):
        lead = Lead.create(
            first_name=f"Lead{i}",
            last_name="Test",
            email=Email.create(f"lead{i}@example.com"),
            company=f"Company {i}",
            owner_id=uuid4(),
        )
        await repo.save(lead)

    results, total = await repo.search(limit=2, offset=0)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=2)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=4)
    assert len(results) == 1
    assert total == 5


@pytest.mark.asyncio
async def test_lead_search_sort_order():
    repo = InMemoryLeadRepository()

    lead1 = Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )
    await repo.save(lead1)

    lead2 = Lead.create(
        first_name="John",
        last_name="Smith",
        email=Email.create("john@example.com"),
        company="Tech Inc",
        owner_id=uuid4(),
    )
    await repo.save(lead2)

    lead3 = Lead.create(
        first_name="Bob",
        last_name="Johnson",
        email=Email.create("bob@example.com"),
        company="StartUp Co",
        owner_id=uuid4(),
    )
    await repo.save(lead3)

    # Descending
    results, _ = await repo.search(sort_by="created_at", sort_order="desc")
    assert results[0].first_name == "Bob"
    assert results[2].first_name == "Jane"

    # Ascending
    results, _ = await repo.search(sort_by="created_at", sort_order="asc")
    assert results[0].first_name == "Jane"
    assert results[2].first_name == "Bob"


@pytest.mark.asyncio
async def test_lead_search_combined_filters():
    repo = InMemoryLeadRepository()
    owner_id = uuid4()

    lead1 = Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane@example.com"),
        company="Acme Corp",
        owner_id=owner_id,
    )
    lead2 = (
        Lead.create(
            first_name="Jane",
            last_name="Smith",
            email=Email.create("jane.smith@example.com"),
            company="Tech Inc",
            owner_id=owner_id,
        )
    ).change_status(LeadStatus.CONTACTED).update_rating(LeadRating.WARM)

    lead3 = (
        Lead.create(
            first_name="Bob",
            last_name="Johnson",
            email=Email.create("bob@example.com"),
            company="StartUp Co",
            owner_id=uuid4(),
        )
    ).update_rating(LeadRating.WARM)

    await repo.save(lead1)
    await repo.save(lead2)
    await repo.save(lead3)

    results, total = await repo.search(
        search="jane", status="contacted", owner_id=owner_id
    )
    assert len(results) == 1
    assert total == 1
    assert results[0].first_name == "Jane"
    assert results[0].last_name == "Smith"


# ============================================================================
# Case Repository Search Tests
# ============================================================================


def make_case(subject="Test Issue", account_id=None, case_number="CASE-001") -> Case:
    return Case.create(
        subject=subject,
        description="Something is broken",
        account_id=account_id or uuid4(),
        owner_id=uuid4(),
        case_number=case_number,
    )


@pytest.mark.asyncio
async def test_case_search_empty_returns_all():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    case1 = Case.create(
        subject="Login Issue",
        description="Cannot login",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-001",
    )
    case2 = Case.create(
        subject="Payment Error",
        description="Payment failed",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-002",
    )
    case3 = Case.create(
        subject="Data Sync Issue",
        description="Data not syncing",
        account_id=uuid4(),
        owner_id=uuid4(),
        case_number="CASE-003",
    )

    await repo.save(case1)
    await repo.save(case2)
    await repo.save(case3)

    results, total = await repo.search()
    assert len(results) == 3
    assert total == 3


@pytest.mark.asyncio
async def test_case_search_by_subject():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    case1 = Case.create(
        subject="Login Issue",
        description="Cannot login",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-001",
    )
    case2 = Case.create(
        subject="Payment Error",
        description="Payment failed",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-002",
    )
    case3 = Case.create(
        subject="Login Timeout",
        description="Login takes too long",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-003",
    )

    await repo.save(case1)
    await repo.save(case2)
    await repo.save(case3)

    results, total = await repo.search(search="login")
    assert len(results) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_case_search_by_status():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    case1 = Case.create(
        subject="Issue 1",
        description="Problem 1",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-001",
    )
    case2 = (
        Case.create(
            subject="Issue 2",
            description="Problem 2",
            account_id=account_id,
            owner_id=uuid4(),
            case_number="CASE-002",
        )
    ).change_status(CaseStatus.IN_PROGRESS)

    case3 = (
        Case.create(
            subject="Issue 3",
            description="Problem 3",
            account_id=account_id,
            owner_id=uuid4(),
            case_number="CASE-003",
        )
    ).change_status(CaseStatus.IN_PROGRESS).resolve("Fixed", "agent@company.com")

    await repo.save(case1)
    await repo.save(case2)
    await repo.save(case3)

    results, total = await repo.search(status="new")
    assert len(results) == 1
    assert total == 1
    assert results[0].status == CaseStatus.NEW

    results, total = await repo.search(status="in_progress")
    assert len(results) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_case_search_by_priority():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    case1 = Case.create(
        subject="Issue 1",
        description="Problem 1",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-001",
        priority=CasePriority.MEDIUM,
    )
    case2 = Case.create(
        subject="Issue 2",
        description="Problem 2",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-002",
        priority=CasePriority.HIGH,
    )

    case3 = Case.create(
        subject="Issue 3",
        description="Problem 3",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-003",
        priority=CasePriority.LOW,
    )

    await repo.save(case1)
    await repo.save(case2)
    await repo.save(case3)

    results, total = await repo.search(priority="high")
    assert len(results) == 1
    assert total == 1
    assert results[0].priority == CasePriority.HIGH

    results, total = await repo.search(priority="low")
    assert len(results) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_case_search_pagination():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    for i in range(5):
        case = Case.create(
            subject=f"Issue {i}",
            description=f"Problem {i}",
            account_id=account_id,
            owner_id=uuid4(),
            case_number=f"CASE-{i:03d}",
        )
        await repo.save(case)

    results, total = await repo.search(limit=2, offset=0)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=2)
    assert len(results) == 2
    assert total == 5

    results, total = await repo.search(limit=2, offset=4)
    assert len(results) == 1
    assert total == 5


@pytest.mark.asyncio
async def test_case_search_sort_order():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    case1 = Case.create(
        subject="Issue 1",
        description="Problem 1",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-001",
    )
    await repo.save(case1)

    case2 = Case.create(
        subject="Issue 2",
        description="Problem 2",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-002",
    )
    await repo.save(case2)

    case3 = Case.create(
        subject="Issue 3",
        description="Problem 3",
        account_id=account_id,
        owner_id=uuid4(),
        case_number="CASE-003",
    )
    await repo.save(case3)

    # Descending
    results, _ = await repo.search(sort_by="created_at", sort_order="desc")
    assert results[0].case_number == "CASE-003"
    assert results[2].case_number == "CASE-001"

    # Ascending
    results, _ = await repo.search(sort_by="created_at", sort_order="asc")
    assert results[0].case_number == "CASE-001"
    assert results[2].case_number == "CASE-003"


@pytest.mark.asyncio
async def test_case_search_combined_filters():
    repo = InMemoryCaseRepository()
    account_id_a = uuid4()
    account_id_b = uuid4()
    owner_id = uuid4()

    case1 = Case.create(
        subject="Login Issue",
        description="Cannot login",
        account_id=account_id_a,
        owner_id=owner_id,
        case_number="CASE-001",
        priority=CasePriority.MEDIUM,
    )
    case2 = Case.create(
        subject="Payment Issue",
        description="Payment failed",
        account_id=account_id_a,
        owner_id=owner_id,
        case_number="CASE-002",
        priority=CasePriority.HIGH,
    )

    case3 = Case.create(
        subject="Login Timeout",
        description="Login takes too long",
        account_id=account_id_b,
        owner_id=uuid4(),
        case_number="CASE-003",
        priority=CasePriority.HIGH,
    )

    await repo.save(case1)
    await repo.save(case2)
    await repo.save(case3)

    results, total = await repo.search(
        search="login", priority="high", owner_id=owner_id, account_id=account_id_a
    )
    assert len(results) == 0
    assert total == 0

    results, total = await repo.search(
        search="issue", priority="high", owner_id=owner_id, account_id=account_id_a
    )
    assert len(results) == 1
    assert total == 1
    assert results[0].case_number == "CASE-002"
