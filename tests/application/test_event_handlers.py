"""
Tests for application event handler functions.

Tests call each handler directly with event objects and verify no exceptions are raised.
"""

import pytest
from datetime import datetime, UTC

from domain.events import (
    OpportunityWonEvent,
    OpportunityLostEvent,
    OpportunityStageChangedEvent,
    CaseEscalatedEvent,
    CaseCreatedEvent,
    CaseResolvedEvent,
    AccountCreatedEvent,
    AccountUpdatedEvent,
    ContactCreatedEvent,
    LeadCreatedEvent,
    LeadQualifiedEvent,
    LeadConvertedEvent,
)
from application.event_handlers import (
    on_opportunity_won,
    on_opportunity_lost,
    on_opportunity_stage_changed,
    on_case_escalated,
    on_case_created,
    on_case_resolved,
    on_account_created,
    on_account_updated,
    on_contact_created,
    on_lead_created,
    on_lead_qualified,
    on_lead_converted,
)


def _now():
    return datetime.now(UTC)


@pytest.mark.asyncio
async def test_on_opportunity_won_does_not_raise():
    event = OpportunityWonEvent(
        aggregate_id="opp-123",
        occurred_at=_now(),
        amount=50000.0,
    )
    await on_opportunity_won(event)


@pytest.mark.asyncio
async def test_on_opportunity_lost_does_not_raise():
    event = OpportunityLostEvent(
        aggregate_id="opp-456",
        occurred_at=_now(),
        amount=25000.0,
        reason="Budget cut",
    )
    await on_opportunity_lost(event)


@pytest.mark.asyncio
async def test_on_opportunity_stage_changed_logs():
    event = OpportunityStageChangedEvent(
        aggregate_id="opp-789",
        occurred_at=_now(),
        old_stage="prospecting",
        new_stage="qualification",
        amount=10000.0,
    )
    await on_opportunity_stage_changed(event)


@pytest.mark.asyncio
async def test_on_case_escalated_logs():
    event = CaseEscalatedEvent(
        aggregate_id="case-001",
        occurred_at=_now(),
        old_priority="medium",
        new_priority="high",
    )
    await on_case_escalated(event)


@pytest.mark.asyncio
async def test_on_case_created_logs():
    event = CaseCreatedEvent(
        aggregate_id="case-002",
        occurred_at=_now(),
        case_number="CASE-002",
        subject="Login issue",
        account_id="acct-abc",
    )
    await on_case_created(event)


@pytest.mark.asyncio
async def test_on_case_resolved_logs():
    event = CaseResolvedEvent(
        aggregate_id="case-003",
        occurred_at=_now(),
        resolution_notes="Issue was fixed",
        resolved_by="agent@company.com",
    )
    await on_case_resolved(event)


@pytest.mark.asyncio
async def test_on_account_created_logs():
    event = AccountCreatedEvent(
        aggregate_id="acct-001",
        occurred_at=_now(),
        account_name="Test Corp",
    )
    await on_account_created(event)


@pytest.mark.asyncio
async def test_on_account_updated_logs():
    event = AccountUpdatedEvent(
        aggregate_id="acct-001",
        occurred_at=_now(),
    )
    await on_account_updated(event)


@pytest.mark.asyncio
async def test_on_contact_created_logs():
    event = ContactCreatedEvent(
        aggregate_id="contact-001",
        occurred_at=_now(),
        contact_name="Alice Smith",
        account_id="acct-001",
    )
    await on_contact_created(event)


@pytest.mark.asyncio
async def test_on_lead_created_logs():
    event = LeadCreatedEvent(
        aggregate_id="lead-001",
        occurred_at=_now(),
        lead_name="Jane Doe",
        email="jane.doe@example.com",
    )
    await on_lead_created(event)


@pytest.mark.asyncio
async def test_on_lead_qualified_logs():
    event = LeadQualifiedEvent(
        aggregate_id="lead-002",
        occurred_at=_now(),
        score=85,
    )
    await on_lead_qualified(event)


@pytest.mark.asyncio
async def test_on_lead_converted_logs():
    event = LeadConvertedEvent(
        aggregate_id="lead-003",
        occurred_at=_now(),
        account_id="acct-001",
        contact_id="contact-001",
        opportunity_id="opp-001",
    )
    await on_lead_converted(event)
