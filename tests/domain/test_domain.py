"""
Domain Tests

Architectural Intent:
- Unit tests for domain entities and value objects
- No mocks needed - pure domain logic
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from domain.entities.account import Account
from domain.entities.contact import Contact
from domain.entities.opportunity import Opportunity, OpportunityStage
from domain.entities.lead import Lead, LeadStatus, LeadRating
from domain.entities.case import Case, CaseStatus, CasePriority
from domain.value_objects import Industry, Territory, Money, Email


class TestAccount:
    def test_create_account_generates_event(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        assert account.name == "Test Corp"
        assert account.is_active is True
        assert len(account.domain_events) == 1
        assert account.domain_events[0].account_name == "Test Corp"

    def test_update_account_creates_new_instance(self):
        original = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        updated = original.update(name="Updated Corp")

        assert original.name == "Test Corp"
        assert updated.name == "Updated Corp"
        assert updated is not original

    def test_deactivate_account(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        deactivated = account.deactivate()

        assert account.is_active is True
        assert deactivated.is_active is False


class TestContact:
    def test_create_contact_generates_event(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        contact = Contact.create(
            account_id=account.id,
            first_name="John",
            last_name="Doe",
            email=Email.create("john@test.com"),
            owner_id=uuid4(),
        )

        assert contact.full_name == "John Doe"
        assert len(contact.domain_events) == 1

    def test_update_contact(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        contact = Contact.create(
            account_id=account.id,
            first_name="John",
            last_name="Doe",
            email=Email.create("john@test.com"),
            owner_id=uuid4(),
        )

        updated = contact.update(first_name="Jane")

        assert contact.first_name == "John"
        assert updated.first_name == "Jane"


class TestOpportunity:
    def test_create_opportunity_default_stage(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        opp = Opportunity.create(
            account_id=account.id,
            name="Test Deal",
            amount=Money.from_float(50000, "USD"),
            close_date=datetime.now() + timedelta(days=30),
            owner_id=uuid4(),
        )

        assert opp.stage == OpportunityStage.PROSPECTING
        assert opp.probability == 10
        assert opp.is_won is False
        assert opp.is_closed is False

    def test_stage_transition_valid(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        opp = Opportunity.create(
            account_id=account.id,
            name="Test Deal",
            amount=Money.from_float(50000, "USD"),
            close_date=datetime.now() + timedelta(days=30),
            owner_id=uuid4(),
        )

        qualified = opp.change_stage(OpportunityStage.QUALIFICATION)

        assert qualified.stage == OpportunityStage.QUALIFICATION
        assert qualified.probability > opp.probability

    def test_stage_transition_invalid_raises(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        opp = Opportunity.create(
            account_id=account.id,
            name="Test Deal",
            amount=Money.from_float(50000, "USD"),
            close_date=datetime.now() + timedelta(days=30),
            owner_id=uuid4(),
        )

        with pytest.raises(ValueError, match="Invalid stage transition"):
            opp.change_stage(OpportunityStage.PROPOSAL)

    def test_close_won_generates_event(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        opp = Opportunity.create(
            account_id=account.id,
            name="Test Deal",
            amount=Money.from_float(50000, "USD"),
            close_date=datetime.now() + timedelta(days=30),
            owner_id=uuid4(),
        )

        won = opp.change_stage(OpportunityStage.CLOSED_WON)

        assert won.is_won is True
        assert won.is_closed is True
        event_types = [e.__class__.__name__ for e in won.domain_events]
        assert "OpportunityWonEvent" in event_types


class TestLead:
    def test_create_lead_default_status(self):
        lead = Lead.create(
            first_name="John",
            last_name="Doe",
            email=Email.create("john@startup.com"),
            company="Startup Inc",
            owner_id=uuid4(),
        )

        assert lead.status == LeadStatus.NEW
        assert lead.rating == LeadRating.COLD

    def test_lead_qualification(self):
        lead = Lead.create(
            first_name="John",
            last_name="Doe",
            email=Email.create("john@enterprise.com"),
            company="Enterprise Corp",
            owner_id=uuid4(),
        )

        rated_lead = lead.update_rating(LeadRating.HOT)
        qualified = rated_lead.change_status(LeadStatus.QUALIFIED)

        assert qualified.rating == LeadRating.HOT
        assert qualified.status == LeadStatus.QUALIFIED

    def test_lead_convert(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        lead = Lead.create(
            first_name="John",
            last_name="Doe",
            email=Email.create("john@test.com"),
            company="Test Corp",
            owner_id=uuid4(),
        )

        lead = lead.change_status(LeadStatus.QUALIFIED)
        contact_id = uuid4()
        converted = lead.convert(
            account_id=account.id,
            contact_id=contact_id,
        )

        assert converted.status == LeadStatus.CONVERTED
        assert converted.converted_account_id == account.id
        assert converted.converted_contact_id == contact_id


class TestCase:
    def test_create_case_default_status(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        case = Case.create(
            subject="Login issue",
            description="Cannot login to system",
            account_id=account.id,
            owner_id=uuid4(),
            case_number="CASE-001",
        )

        assert case.status == CaseStatus.NEW
        assert case.priority == CasePriority.MEDIUM

    def test_case_escalation(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        case = Case.create(
            subject="Login issue",
            description="Cannot login",
            account_id=account.id,
            owner_id=uuid4(),
            case_number="CASE-001",
            priority=CasePriority.LOW,
        )

        escalated = case.escalate()

        assert escalated.priority == CasePriority.HIGH

    def test_case_resolve(self):
        account = Account.create(
            name="Test Corp",
            industry=Industry.technology(),
            territory=Territory.uk(),
            owner_id=uuid4(),
        )

        case = Case.create(
            subject="Login issue",
            description="Cannot login",
            account_id=account.id,
            owner_id=uuid4(),
            case_number="CASE-001",
        )

        case = case.change_status(CaseStatus.IN_PROGRESS)
        resolved = case.resolve(
            resolution_notes="Password reset completed",
            resolved_by="support@company.com",
        )

        assert resolved.status == CaseStatus.RESOLVED
        assert resolved.resolution_notes == "Password reset completed"


class TestValueObjects:
    def test_money_addition(self):
        m1 = Money.from_float(100.00, "USD")
        m2 = Money.from_float(50.00, "USD")

        result = m1 + m2

        assert result.amount_float == 150.00

    def test_money_different_currency_raises(self):
        m1 = Money.from_float(100.00, "USD")
        m2 = Money.from_float(50.00, "GBP")

        with pytest.raises(ValueError, match="different currencies"):
            m1 + m2

    def test_email_validation(self):
        valid = Email.create("test@example.com")
        assert str(valid) == "test@example.com"

    def test_email_invalid_raises(self):
        with pytest.raises(ValueError):
            Email.create("invalid-email")

    def test_territory_display(self):
        uk = Territory.uk()
        assert "United Kingdom" in uk.display_name

    def test_industry_from_string(self):
        tech = Industry.from_string("technology")
        assert tech.type.value == "technology"

        custom = Industry.from_string("custom industry")
        assert custom.type.value == "other"
        assert custom.custom_name == "custom industry"
