"""
Tests for Lead domain entity.
"""

import pytest
from uuid import uuid4

from domain.entities.lead import Lead, LeadStatus, LeadRating
from domain.value_objects import Email, PhoneNumber
from domain.events import LeadCreatedEvent, LeadStatusChangedEvent, LeadConvertedEvent


def make_lead(**kwargs) -> Lead:
    defaults = dict(
        first_name="Jane",
        last_name="Doe",
        email=Email.create("jane.doe@example.com"),
        company="Acme Corp",
        owner_id=uuid4(),
    )
    defaults.update(kwargs)
    return Lead.create(**defaults)


def test_create_with_required_fields():
    lead = make_lead()
    assert lead.first_name == "Jane"
    assert lead.last_name == "Doe"
    assert lead.company == "Acme Corp"
    assert lead.status == LeadStatus.NEW
    assert lead.rating == LeadRating.COLD


def test_create_emits_lead_created_event():
    lead = make_lead()
    assert len(lead.domain_events) == 1
    assert isinstance(lead.domain_events[0], LeadCreatedEvent)


def test_change_status_new_to_contacted():
    lead = make_lead()
    updated = lead.change_status(LeadStatus.CONTACTED)
    assert updated.status == LeadStatus.CONTACTED


def test_change_status_contacted_to_qualified():
    lead = make_lead().change_status(LeadStatus.CONTACTED)
    updated = lead.change_status(LeadStatus.QUALIFIED)
    assert updated.status == LeadStatus.QUALIFIED


def test_change_status_qualified_to_converted_via_change_status():
    lead = make_lead().change_status(LeadStatus.CONTACTED).change_status(LeadStatus.QUALIFIED)
    updated = lead.change_status(LeadStatus.CONVERTED)
    assert updated.status == LeadStatus.CONVERTED


def test_change_status_invalid_converted_to_anything_raises_value_error():
    lead = (
        make_lead()
        .change_status(LeadStatus.CONTACTED)
        .change_status(LeadStatus.QUALIFIED)
        .change_status(LeadStatus.CONVERTED)
    )
    with pytest.raises(ValueError, match="Invalid status transition"):
        lead.change_status(LeadStatus.NEW)


def test_convert_from_qualified_state():
    lead = make_lead().change_status(LeadStatus.CONTACTED).change_status(LeadStatus.QUALIFIED)
    account_id = uuid4()
    contact_id = uuid4()
    converted = lead.convert(account_id=account_id, contact_id=contact_id)
    assert converted.status == LeadStatus.CONVERTED
    assert converted.converted_account_id == account_id
    assert converted.converted_contact_id == contact_id
    assert converted.converted_at is not None


def test_convert_from_non_qualified_state_raises_value_error():
    lead = make_lead()  # status=NEW
    with pytest.raises(ValueError, match="Cannot convert lead"):
        lead.convert(account_id=uuid4(), contact_id=uuid4())


def test_update_rating_changes_rating():
    lead = make_lead()
    assert lead.rating == LeadRating.COLD
    updated = lead.update_rating(LeadRating.HOT)
    assert updated.rating == LeadRating.HOT


def test_full_name_property():
    lead = make_lead(first_name="John", last_name="Smith")
    assert lead.full_name == "John Smith"


def test_email_value_object_used_correctly():
    email = Email.create("test@example.com")
    lead = make_lead(email=email)
    assert str(lead.email) == "test@example.com"


def test_phone_number_value_object_optional():
    phone = PhoneNumber.create("4155551234")
    lead = make_lead(phone=phone)
    assert lead.phone is not None
    assert lead.phone.country_code == "+1"


def test_convert_emits_lead_converted_event():
    lead = make_lead().change_status(LeadStatus.CONTACTED).change_status(LeadStatus.QUALIFIED)
    account_id = uuid4()
    contact_id = uuid4()
    converted = lead.convert(account_id=account_id, contact_id=contact_id)
    events = [e for e in converted.domain_events if isinstance(e, LeadConvertedEvent)]
    assert len(events) == 1
    assert events[0].account_id == str(account_id)
