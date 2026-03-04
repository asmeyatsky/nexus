"""
Tests for all application query classes.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta

from domain.entities.account import Account
from domain.entities.contact import Contact
from domain.entities.opportunity import Opportunity, OpportunityStage
from domain.entities.lead import Lead
from domain.entities.case import Case, CaseStatus
from domain.value_objects import Email, Money, Industry, Territory
from domain.value_objects.industry import IndustryType
from application.queries import (
    GetAccountQuery,
    ListAccountsQuery,
    GetAccountsByOwnerQuery,
    GetContactQuery,
    ListContactsQuery,
    GetContactsByAccountQuery,
    GetOpportunityQuery,
    ListOpportunitiesQuery,
    GetOpenOpportunitiesQuery,
    GetLeadQuery,
    ListLeadsQuery,
    GetCaseQuery,
    ListCasesQuery,
    GetOpenCasesQuery,
    GetCaseByNumberQuery,
)


OWNER_ID = uuid4()


def make_account(name="Test Corp", owner_id=None) -> Account:
    return Account.create(
        name=name,
        industry=Industry(type=IndustryType.TECHNOLOGY),
        territory=Territory(region="Americas"),
        owner_id=owner_id or OWNER_ID,
    )


def make_contact(account_id, email_suffix="test") -> Contact:
    return Contact.create(
        account_id=account_id,
        first_name="Alice",
        last_name="Smith",
        email=Email.create(f"alice.{email_suffix}@example.com"),
        owner_id=OWNER_ID,
    )


def make_opportunity(account_id) -> Opportunity:
    return Opportunity.create(
        account_id=account_id,
        name="Big Deal",
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=OWNER_ID,
    )


def make_lead(email_suffix="test") -> Lead:
    return Lead.create(
        first_name="Jane",
        last_name="Doe",
        email=Email.create(f"jane.{email_suffix}@example.com"),
        company="Acme",
        owner_id=OWNER_ID,
    )


def make_case(account_id, case_number="CASE-001") -> Case:
    return Case.create(
        subject="Test Issue",
        description="Something broke",
        account_id=account_id,
        owner_id=OWNER_ID,
        case_number=case_number,
    )


# ---------------------------------------------------------------------------
# Account queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_account_query_returns_account_by_id(account_repo):
    account = make_account()
    await account_repo.save(account)

    query = GetAccountQuery(repository=account_repo)
    result = await query.execute(str(account.id))
    assert result is not None
    assert result.id == str(account.id)
    assert result.name == "Test Corp"


@pytest.mark.asyncio
async def test_get_account_query_returns_none_for_missing(account_repo):
    query = GetAccountQuery(repository=account_repo)
    result = await query.execute(str(uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_list_accounts_query_with_pagination(account_repo):
    for i in range(5):
        await account_repo.save(make_account(name=f"Corp {i}"))

    query = ListAccountsQuery(repository=account_repo)
    all_results = await query.execute(limit=100, offset=0)
    assert len(all_results) == 5

    page1 = await query.execute(limit=2, offset=0)
    assert len(page1) == 2

    page2 = await query.execute(limit=2, offset=2)
    assert len(page2) == 2


# ---------------------------------------------------------------------------
# Contact queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_contact_query_returns_contact_by_id(contact_repo):
    account_id = uuid4()
    contact = make_contact(account_id)
    await contact_repo.save(contact)

    query = GetContactQuery(repository=contact_repo)
    result = await query.execute(str(contact.id))
    assert result is not None
    assert result.id == str(contact.id)


@pytest.mark.asyncio
async def test_list_contacts_query_with_pagination(contact_repo):
    account_id = uuid4()
    for i in range(4):
        await contact_repo.save(make_contact(account_id, email_suffix=str(i)))

    query = ListContactsQuery(repository=contact_repo)
    results = await query.execute(limit=2, offset=0)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_contacts_by_account_query(contact_repo):
    account_id_a = uuid4()
    account_id_b = uuid4()

    for i in range(3):
        await contact_repo.save(make_contact(account_id_a, email_suffix=f"a{i}"))
    await contact_repo.save(make_contact(account_id_b, email_suffix="b0"))

    query = GetContactsByAccountQuery(repository=contact_repo)
    results = await query.execute(str(account_id_a))
    assert len(results) == 3
    for r in results:
        assert r.account_id == str(account_id_a)


# ---------------------------------------------------------------------------
# Opportunity queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_opportunity_query(opportunity_repo):
    account_id = uuid4()
    opp = make_opportunity(account_id)
    await opportunity_repo.save(opp)

    query = GetOpportunityQuery(repository=opportunity_repo)
    result = await query.execute(str(opp.id))
    assert result is not None
    assert result.id == str(opp.id)


@pytest.mark.asyncio
async def test_list_opportunities_query(opportunity_repo):
    account_id = uuid4()
    for _ in range(3):
        await opportunity_repo.save(make_opportunity(account_id))

    query = ListOpportunitiesQuery(repository=opportunity_repo)
    results = await query.execute(limit=100, offset=0)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_get_open_opportunities_query_returns_only_open(opportunity_repo):
    account_id = uuid4()
    open_opp = make_opportunity(account_id)
    closed_opp = make_opportunity(account_id).change_stage(OpportunityStage.CLOSED_WON)

    await opportunity_repo.save(open_opp)
    await opportunity_repo.save(closed_opp)

    query = GetOpenOpportunitiesQuery(repository=opportunity_repo)
    results = await query.execute()
    assert len(results) == 1
    assert results[0].id == str(open_opp.id)


@pytest.mark.asyncio
async def test_get_open_opportunities_query_with_pagination(opportunity_repo):
    account_id = uuid4()
    for _ in range(5):
        await opportunity_repo.save(make_opportunity(account_id))

    query = GetOpenOpportunitiesQuery(repository=opportunity_repo)
    page = await query.execute(limit=2, offset=0)
    assert len(page) == 2

    page2 = await query.execute(limit=2, offset=2)
    assert len(page2) == 2


# ---------------------------------------------------------------------------
# Lead queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_lead_query(lead_repo):
    lead = make_lead()
    await lead_repo.save(lead)

    query = GetLeadQuery(repository=lead_repo)
    result = await query.execute(str(lead.id))
    assert result is not None
    assert result.id == str(lead.id)


@pytest.mark.asyncio
async def test_list_leads_query(lead_repo):
    for i in range(3):
        await lead_repo.save(make_lead(email_suffix=str(i)))

    query = ListLeadsQuery(repository=lead_repo)
    results = await query.execute(limit=100, offset=0)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# Case queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_case_query(case_repo):
    account_id = uuid4()
    case = make_case(account_id)
    await case_repo.save(case)

    query = GetCaseQuery(repository=case_repo)
    result = await query.execute(str(case.id))
    assert result is not None
    assert result.id == str(case.id)


@pytest.mark.asyncio
async def test_list_cases_query(case_repo):
    account_id = uuid4()
    for i in range(3):
        await case_repo.save(make_case(account_id, case_number=f"CASE-{i:03d}"))

    query = ListCasesQuery(repository=case_repo)
    results = await query.execute(limit=100, offset=0)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_get_open_cases_query_returns_only_open(case_repo):
    account_id = uuid4()
    open_case = make_case(account_id, case_number="CASE-001")
    closed_case = make_case(account_id, case_number="CASE-002").change_status(CaseStatus.IN_PROGRESS).resolve("Fixed", "agent").close()

    await case_repo.save(open_case)
    await case_repo.save(closed_case)

    query = GetOpenCasesQuery(repository=case_repo)
    results = await query.execute()
    assert len(results) == 1
    assert results[0].id == str(open_case.id)


@pytest.mark.asyncio
async def test_get_open_cases_query_with_pagination(case_repo):
    account_id = uuid4()
    for i in range(5):
        await case_repo.save(make_case(account_id, case_number=f"CASE-{i:03d}"))

    query = GetOpenCasesQuery(repository=case_repo)
    page = await query.execute(limit=2, offset=0)
    assert len(page) == 2

    page2 = await query.execute(limit=2, offset=2)
    assert len(page2) == 2


@pytest.mark.asyncio
async def test_get_case_by_number_query(case_repo):
    account_id = uuid4()
    case = make_case(account_id, case_number="CASE-UNIQUE-42")
    await case_repo.save(case)

    query = GetCaseByNumberQuery(repository=case_repo)
    result = await query.execute("CASE-UNIQUE-42")
    assert result is not None
    assert result.case_number == "CASE-UNIQUE-42"


@pytest.mark.asyncio
async def test_get_accounts_by_owner_query(account_repo):
    owner_a = uuid4()
    owner_b = uuid4()

    for i in range(2):
        await account_repo.save(make_account(name=f"Owner A Corp {i}", owner_id=owner_a))
    await account_repo.save(make_account(name="Owner B Corp", owner_id=owner_b))

    query = GetAccountsByOwnerQuery(repository=account_repo)
    results = await query.execute(str(owner_a))
    assert len(results) == 2
    for r in results:
        assert r.owner_id == str(owner_a)
