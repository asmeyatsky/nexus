"""
Tests for Case domain entity.
"""

import pytest
from uuid import uuid4

from domain.entities.case import Case, CaseStatus, CasePriority, CaseOrigin
from domain.events import CaseCreatedEvent, CaseStatusChangedEvent, CaseResolvedEvent


def make_case(**kwargs) -> Case:
    defaults = dict(
        subject="Test Issue",
        description="Something is broken",
        account_id=uuid4(),
        owner_id=uuid4(),
        case_number="CASE-001",
        priority=CasePriority.MEDIUM,
        origin=CaseOrigin.WEB,
    )
    defaults.update(kwargs)
    return Case.create(**defaults)


def test_create_sets_new_status():
    case = make_case()
    assert case.status == CaseStatus.NEW


def test_create_emits_case_created_event():
    case = make_case(case_number="CASE-001", subject="My Subject")
    assert len(case.domain_events) == 1
    event = case.domain_events[0]
    assert isinstance(event, CaseCreatedEvent)
    assert event.case_number == "CASE-001"
    assert event.subject == "My Subject"


def test_change_status_new_to_in_progress():
    case = make_case()
    updated = case.change_status(CaseStatus.IN_PROGRESS)
    assert updated.status == CaseStatus.IN_PROGRESS


def test_change_status_in_progress_to_resolved():
    case = make_case().change_status(CaseStatus.IN_PROGRESS)
    updated = case.change_status(CaseStatus.RESOLVED)
    assert updated.status == CaseStatus.RESOLVED


def test_change_status_in_progress_to_waiting_on_customer():
    case = make_case().change_status(CaseStatus.IN_PROGRESS)
    updated = case.change_status(CaseStatus.WAITING_ON_CUSTOMER)
    assert updated.status == CaseStatus.WAITING_ON_CUSTOMER


def test_change_status_invalid_transition_raises_value_error():
    case = make_case()
    with pytest.raises(ValueError, match="Invalid status transition"):
        case.change_status(CaseStatus.RESOLVED)


def test_change_status_closed_to_anything_raises_value_error():
    case = make_case().change_status(CaseStatus.IN_PROGRESS)
    closed = case.change_status(CaseStatus.CLOSED)
    with pytest.raises(ValueError):
        closed.change_status(CaseStatus.IN_PROGRESS)


def test_resolve_from_in_progress():
    case = make_case().change_status(CaseStatus.IN_PROGRESS)
    resolved = case.resolve("Fixed the issue", "agent@company.com")
    assert resolved.status == CaseStatus.RESOLVED
    assert resolved.resolution_notes == "Fixed the issue"
    assert resolved.resolved_by == "agent@company.com"
    assert resolved.resolved_at is not None


def test_resolve_from_waiting_on_customer():
    case = (
        make_case()
        .change_status(CaseStatus.IN_PROGRESS)
        .change_status(CaseStatus.WAITING_ON_CUSTOMER)
    )
    resolved = case.resolve("Customer confirmed fix", "agent@company.com")
    assert resolved.status == CaseStatus.RESOLVED


def test_resolve_from_invalid_state_raises_value_error():
    case = make_case()  # status=NEW, which cannot go to RESOLVED directly
    with pytest.raises(ValueError, match="Cannot resolve case"):
        case.resolve("Notes", "agent@company.com")


def test_close_from_resolved():
    case = make_case().change_status(CaseStatus.IN_PROGRESS)
    resolved = case.resolve("Fixed", "agent@company.com")
    closed = resolved.close()
    assert closed.status == CaseStatus.CLOSED
    assert closed.closed_at is not None


def test_close_from_new():
    case = make_case()
    closed = case.close()
    assert closed.status == CaseStatus.CLOSED


def test_close_from_closed_raises_value_error():
    case = make_case().change_status(CaseStatus.IN_PROGRESS)
    closed = case.resolve("Done", "agent").close()
    with pytest.raises(ValueError):
        closed.close()


def test_escalate_changes_priority_to_high():
    case = make_case(priority=CasePriority.LOW)
    escalated = case.escalate()
    assert escalated.priority == CasePriority.HIGH


def test_escalate_already_high_stays_high():
    case = make_case(priority=CasePriority.HIGH)
    escalated = case.escalate()
    assert escalated.priority == CasePriority.HIGH


def test_domain_events_accumulate():
    case = make_case()
    updated = case.change_status(CaseStatus.IN_PROGRESS)
    resolved = updated.resolve("All done", "agent@company.com")
    assert len(resolved.domain_events) == 3
    assert isinstance(resolved.domain_events[0], CaseCreatedEvent)
    assert isinstance(resolved.domain_events[1], CaseStatusChangedEvent)
    assert isinstance(resolved.domain_events[2], CaseResolvedEvent)


def test_case_number_preserved_through_transitions():
    case = make_case(case_number="CASE-XYZ-42")
    updated = case.change_status(CaseStatus.IN_PROGRESS)
    assert updated.case_number == "CASE-XYZ-42"
