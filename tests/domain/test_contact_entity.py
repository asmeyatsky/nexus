"""
Tests for Contact domain entity.
"""

from uuid import uuid4

from domain.entities.contact import Contact
from domain.value_objects import Email, PhoneNumber
from domain.events import ContactCreatedEvent, ContactUpdatedEvent


def make_contact(**kwargs) -> Contact:
    defaults = dict(
        account_id=uuid4(),
        first_name="Alice",
        last_name="Smith",
        email=Email.create("alice.smith@example.com"),
        owner_id=uuid4(),
    )
    defaults.update(kwargs)
    return Contact.create(**defaults)


def test_create_with_required_fields():
    contact = make_contact()
    assert contact.first_name == "Alice"
    assert contact.last_name == "Smith"
    assert contact.is_active is True
    assert contact.phone is None
    assert contact.title is None
    assert contact.department is None


def test_full_name_property():
    contact = make_contact(first_name="Bob", last_name="Jones")
    assert contact.full_name == "Bob Jones"


def test_create_emits_contact_created_event():
    contact = make_contact()
    assert len(contact.domain_events) == 1
    event = contact.domain_events[0]
    assert isinstance(event, ContactCreatedEvent)
    assert event.contact_name == "Alice Smith"


def test_update_changes_first_name():
    contact = make_contact()
    updated = contact.update(first_name="Alicia")
    assert updated.first_name == "Alicia"
    assert updated.last_name == "Smith"


def test_update_changes_email():
    contact = make_contact()
    new_email = Email.create("newemail@example.com")
    updated = contact.update(email=new_email)
    assert str(updated.email) == "newemail@example.com"


def test_update_emits_contact_updated_event():
    contact = make_contact()
    updated = contact.update(first_name="Alicia")
    events = [e for e in updated.domain_events if isinstance(e, ContactUpdatedEvent)]
    assert len(events) == 1


def test_deactivate_sets_is_active_false():
    contact = make_contact()
    deactivated = contact.deactivate()
    assert deactivated.is_active is False


def test_deactivate_already_inactive_is_noop():
    contact = make_contact()
    deactivated = contact.deactivate()
    deactivated_again = deactivated.deactivate()
    # Should return same object (no-op), event count should not increase from double deactivate
    assert deactivated_again.is_active is False
    assert deactivated_again is deactivated


def test_optional_phone_field():
    phone = PhoneNumber.create("4155551234")
    contact = make_contact(phone=phone)
    assert contact.phone is not None
    assert contact.phone.country_code == "+1"


def test_optional_title_and_department():
    contact = make_contact(title="VP Engineering", department="Engineering")
    assert contact.title == "VP Engineering"
    assert contact.department == "Engineering"


def test_update_preserves_unchanged_fields():
    contact = make_contact(title="Director", department="Sales")
    updated = contact.update(first_name="NewName")
    assert updated.title == "Director"
    assert updated.department == "Sales"
