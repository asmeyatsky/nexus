"""
Tests for application-layer update commands.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta

from application.commands.case_commands import (
    CreateCaseCommand,
    UpdateCaseStatusCommand,
    ResolveCaseCommand,
    CloseCaseCommand,
)
from application.commands.opportunity_commands import (
    CreateOpportunityCommand,
    UpdateOpportunityStageCommand,
    UpdateOpportunityCommand,
)
from application.commands.account_commands import (
    CreateAccountCommand,
    UpdateAccountCommand,
    DeactivateAccountCommand,
)
from application.commands.lead_commands import (
    CreateLeadCommand,
    QualifyLeadCommand,
    ConvertLeadCommand,
)
from application.commands.contact_commands import (
    CreateContactCommand,
    UpdateContactCommand,
)
from application.dtos import (
    CreateCaseDTO,
    CreateOpportunityDTO,
    CreateAccountDTO,
    CreateLeadDTO,
    CreateContactDTO,
)

OWNER_ID = str(uuid4())


async def _create_account(account_repo, event_bus, audit_log):
    dto = CreateAccountDTO(
        name="Test Corp",
        industry="technology",
        territory="north_america",
        owner_id=OWNER_ID,
    )
    cmd = CreateAccountCommand(repository=account_repo, event_bus=event_bus, audit_log=audit_log)
    return await cmd.execute(dto)


async def _create_case(case_repo, account_repo, event_bus, audit_log, account_id):
    dto = CreateCaseDTO(
        subject="Test Case",
        description="Something went wrong",
        account_id=account_id,
        owner_id=OWNER_ID,
        case_number="CASE-001",
    )
    cmd = CreateCaseCommand(
        repository=case_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    return await cmd.execute(dto)


async def _create_opportunity(opp_repo, account_repo, event_bus, audit_log, account_id):
    dto = CreateOpportunityDTO(
        account_id=account_id,
        name="Big Deal",
        amount=50000.0,
        currency="USD",
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=OWNER_ID,
    )
    cmd = CreateOpportunityCommand(
        repository=opp_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    return await cmd.execute(dto)


async def _create_lead(lead_repo, event_bus, audit_log):
    dto = CreateLeadDTO(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        company="Acme",
        owner_id=OWNER_ID,
    )
    cmd = CreateLeadCommand(repository=lead_repo, event_bus=event_bus, audit_log=audit_log)
    return await cmd.execute(dto)


@pytest.mark.asyncio
async def test_update_case_status_command(case_repo, account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)
    case = await _create_case(case_repo, account_repo, event_bus, audit_log, account.id)

    cmd = UpdateCaseStatusCommand(repository=case_repo, event_bus=event_bus, audit_log=audit_log)
    updated = await cmd.execute(case.id, "in_progress", OWNER_ID)
    assert updated.status == "in_progress"


@pytest.mark.asyncio
async def test_resolve_case_command(case_repo, account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)
    case = await _create_case(case_repo, account_repo, event_bus, audit_log, account.id)

    # First move to in_progress
    update_cmd = UpdateCaseStatusCommand(repository=case_repo, event_bus=event_bus, audit_log=audit_log)
    await update_cmd.execute(case.id, "in_progress", OWNER_ID)

    resolve_cmd = ResolveCaseCommand(repository=case_repo, event_bus=event_bus, audit_log=audit_log)
    resolved = await resolve_cmd.execute(case.id, "Fixed it", "agent@company.com", OWNER_ID)
    assert resolved.status == "resolved"
    assert resolved.resolution_notes == "Fixed it"


@pytest.mark.asyncio
async def test_close_case_command(case_repo, account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)
    case = await _create_case(case_repo, account_repo, event_bus, audit_log, account.id)

    close_cmd = CloseCaseCommand(repository=case_repo, event_bus=event_bus, audit_log=audit_log)
    closed = await close_cmd.execute(case.id, OWNER_ID)
    assert closed.status == "closed"


@pytest.mark.asyncio
async def test_update_opportunity_stage_command(opportunity_repo, account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)
    opp = await _create_opportunity(opportunity_repo, account_repo, event_bus, audit_log, account.id)

    cmd = UpdateOpportunityStageCommand(
        repository=opportunity_repo, event_bus=event_bus, audit_log=audit_log
    )
    updated = await cmd.execute(opp.id, "qualification", OWNER_ID)
    assert updated.stage == "qualification"


@pytest.mark.asyncio
async def test_update_opportunity_command(opportunity_repo, account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)
    opp = await _create_opportunity(opportunity_repo, account_repo, event_bus, audit_log, account.id)

    update_dto = CreateOpportunityDTO(
        account_id=account.id,
        name="Updated Deal",
        amount=75000.0,
        currency="USD",
        close_date=datetime.now(UTC) + timedelta(days=60),
        owner_id=OWNER_ID,
        description="Updated description",
    )
    cmd = UpdateOpportunityCommand(
        repository=opportunity_repo, event_bus=event_bus, audit_log=audit_log
    )
    updated = await cmd.execute(opp.id, update_dto, OWNER_ID)
    assert updated.name == "Updated Deal"
    assert updated.amount == 75000.0


@pytest.mark.asyncio
async def test_update_account_command(account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)

    update_dto = CreateAccountDTO(
        name="Updated Corp",
        industry="finance",
        territory="europe",
        owner_id=OWNER_ID,
    )
    cmd = UpdateAccountCommand(repository=account_repo, event_bus=event_bus, audit_log=audit_log)
    updated = await cmd.execute(account.id, update_dto, OWNER_ID)
    assert updated.name == "Updated Corp"


@pytest.mark.asyncio
async def test_deactivate_account_command(account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)

    cmd = DeactivateAccountCommand(repository=account_repo, event_bus=event_bus, audit_log=audit_log)
    deactivated = await cmd.execute(account.id, OWNER_ID)
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_qualify_lead_command(lead_repo, event_bus, audit_log):
    lead = await _create_lead(lead_repo, event_bus, audit_log)

    cmd = QualifyLeadCommand(repository=lead_repo, event_bus=event_bus, audit_log=audit_log)
    qualified = await cmd.execute(lead.id, OWNER_ID)
    assert qualified.status == "qualified"


@pytest.mark.asyncio
async def test_convert_lead_command(lead_repo, account_repo, contact_repo, opportunity_repo, event_bus, audit_log):
    lead = await _create_lead(lead_repo, event_bus, audit_log)

    # Qualify first
    qualify_cmd = QualifyLeadCommand(repository=lead_repo, event_bus=event_bus, audit_log=audit_log)
    await qualify_cmd.execute(lead.id, OWNER_ID)

    account_id = str(uuid4())
    contact_id = str(uuid4())
    opportunity_id = str(uuid4())

    cmd = ConvertLeadCommand(
        lead_repository=lead_repo,
        account_repository=account_repo,
        contact_repository=contact_repo,
        opportunity_repository=opportunity_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await cmd.execute(lead.id, account_id, contact_id, opportunity_id, OWNER_ID)
    assert result["lead"].status == "converted"


@pytest.mark.asyncio
async def test_update_case_status_raises_for_not_found(case_repo, event_bus, audit_log):
    cmd = UpdateCaseStatusCommand(repository=case_repo, event_bus=event_bus, audit_log=audit_log)
    with pytest.raises(ValueError, match="not found"):
        await cmd.execute(str(uuid4()), "in_progress", OWNER_ID)


@pytest.mark.asyncio
async def test_update_opportunity_stage_raises_for_not_found(opportunity_repo, event_bus, audit_log):
    cmd = UpdateOpportunityStageCommand(
        repository=opportunity_repo, event_bus=event_bus, audit_log=audit_log
    )
    with pytest.raises(ValueError, match="not found"):
        await cmd.execute(str(uuid4()), "qualification", OWNER_ID)


@pytest.mark.asyncio
async def test_update_contact_command(contact_repo, account_repo, event_bus, audit_log):
    account = await _create_account(account_repo, event_bus, audit_log)

    create_dto = CreateContactDTO(
        account_id=account.id,
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        owner_id=OWNER_ID,
    )
    create_cmd = CreateContactCommand(
        repository=contact_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    contact = await create_cmd.execute(create_dto)

    update_dto = CreateContactDTO(
        account_id=account.id,
        first_name="Alicia",
        last_name="Smith",
        email="alicia@example.com",
        owner_id=OWNER_ID,
    )
    update_cmd = UpdateContactCommand(
        repository=contact_repo, event_bus=event_bus, audit_log=audit_log
    )
    updated = await update_cmd.execute(contact.id, update_dto, OWNER_ID)
    assert updated.first_name == "Alicia"
    assert updated.email == "alicia@example.com"
