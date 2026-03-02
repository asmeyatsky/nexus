"""
Command Handler Tests

Tests for CQRS command handlers.
"""

import pytest

from application import (
    CreateAccountCommand,
    CreateContactCommand,
    CreateLeadCommand,
    CreateCaseCommand,
    CreateAccountDTO,
    CreateContactDTO,
    CreateLeadDTO,
    CreateCaseDTO,
)

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_create_account(account_repo, event_bus, audit_log):
    dto = CreateAccountDTO(
        name="Test Corp",
        industry="technology",
        territory="north_america",
        owner_id=TEST_USER_ID,
    )
    command = CreateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)
    assert result.name == "Test Corp"
    assert result.industry == "Technology"


@pytest.mark.asyncio
async def test_create_contact(account_repo, contact_repo, event_bus, audit_log):
    # First create an account
    acc_dto = CreateAccountDTO(
        name="Parent Corp",
        industry="finance",
        territory="europe",
        owner_id=TEST_USER_ID,
    )
    acc_cmd = CreateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    account = await acc_cmd.execute(acc_dto)

    dto = CreateContactDTO(
        account_id=account.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        owner_id=TEST_USER_ID,
    )
    command = CreateContactCommand(
        repository=contact_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)
    assert result.first_name == "John"
    assert result.account_id == account.id


@pytest.mark.asyncio
async def test_create_lead(lead_repo, event_bus, audit_log):
    dto = CreateLeadDTO(
        first_name="Jane",
        last_name="Smith",
        email="jane@company.com",
        company="Company Inc",
        owner_id=TEST_USER_ID,
    )
    command = CreateLeadCommand(
        repository=lead_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)
    assert result.first_name == "Jane"
    assert result.company == "Company Inc"


@pytest.mark.asyncio
async def test_create_case(account_repo, case_repo, event_bus, audit_log):
    # Create account first
    acc_dto = CreateAccountDTO(
        name="Case Corp",
        industry="healthcare",
        territory="asia_pacific",
        owner_id=TEST_USER_ID,
    )
    acc_cmd = CreateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    account = await acc_cmd.execute(acc_dto)

    dto = CreateCaseDTO(
        subject="Login issue",
        description="Cannot login to the system",
        account_id=account.id,
        owner_id=TEST_USER_ID,
        case_number="CASE-001",
        priority="high",
        origin="web",
    )
    command = CreateCaseCommand(
        repository=case_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)
    assert result.subject == "Login issue"
    assert result.priority == "high"
