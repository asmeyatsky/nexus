"""
Tests for Opportunity domain entity.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta
from decimal import Decimal

from domain.entities.opportunity import Opportunity, OpportunityStage
from domain.value_objects import Money
from domain.events import (
    OpportunityCreatedEvent,
    OpportunityWonEvent,
    OpportunityLostEvent,
    OpportunityUpdatedEvent,
)


def make_opportunity(**kwargs) -> Opportunity:
    defaults = dict(
        account_id=uuid4(),
        name="Big Deal",
        amount=Money.from_float(50000.0, "USD"),
        close_date=datetime.now(UTC) + timedelta(days=30),
        owner_id=uuid4(),
    )
    defaults.update(kwargs)
    return Opportunity.create(**defaults)


def test_create_with_defaults():
    opp = make_opportunity()
    assert opp.stage == OpportunityStage.PROSPECTING
    assert opp.probability == 10
    assert opp.is_active is True


def test_create_emits_opportunity_created_event():
    opp = make_opportunity(name="New Opp")
    assert len(opp.domain_events) == 1
    assert isinstance(opp.domain_events[0], OpportunityCreatedEvent)
    assert opp.domain_events[0].opportunity_name == "New Opp"


def test_change_stage_prospecting_to_qualification():
    opp = make_opportunity()
    updated = opp.change_stage(OpportunityStage.QUALIFICATION)
    assert updated.stage == OpportunityStage.QUALIFICATION
    assert updated.probability == 20


def test_change_stage_invalid_transition_raises_value_error():
    opp = make_opportunity()
    with pytest.raises(ValueError, match="Invalid stage transition"):
        opp.change_stage(OpportunityStage.NEGOTIATION)


def test_change_stage_closed_won_raises_on_further_transition():
    opp = make_opportunity().change_stage(OpportunityStage.CLOSED_WON)
    with pytest.raises(ValueError):
        opp.change_stage(OpportunityStage.QUALIFICATION)


def test_change_stage_to_closed_won_emits_opportunity_won_event():
    opp = make_opportunity()
    won = opp.change_stage(OpportunityStage.CLOSED_WON)
    won_events = [e for e in won.domain_events if isinstance(e, OpportunityWonEvent)]
    assert len(won_events) == 1
    assert won_events[0].amount == 50000.0


def test_change_stage_to_closed_lost_emits_opportunity_lost_event():
    opp = make_opportunity()
    lost = opp.change_stage(OpportunityStage.CLOSED_LOST, reason="Budget cut")
    lost_events = [e for e in lost.domain_events if isinstance(e, OpportunityLostEvent)]
    assert len(lost_events) == 1
    assert lost_events[0].reason == "Budget cut"


def test_weighted_value_calculation():
    opp = make_opportunity(amount=Money.from_float(100000.0, "USD"))
    # probability=10 by default at PROSPECTING
    assert opp.weighted_value.amount == Decimal("10000.00") or opp.weighted_value.amount_float == pytest.approx(10000.0)


def test_is_won_property():
    opp = make_opportunity()
    assert opp.is_won is False
    won = opp.change_stage(OpportunityStage.CLOSED_WON)
    assert won.is_won is True


def test_is_lost_property():
    opp = make_opportunity()
    assert opp.is_lost is False
    lost = opp.change_stage(OpportunityStage.CLOSED_LOST)
    assert lost.is_lost is True


def test_is_closed_property():
    opp = make_opportunity()
    assert opp.is_closed is False
    won = opp.change_stage(OpportunityStage.CLOSED_WON)
    assert won.is_closed is True
    lost = make_opportunity().change_stage(OpportunityStage.CLOSED_LOST)
    assert lost.is_closed is True


def test_update_method_changes_fields():
    opp = make_opportunity()
    new_close = datetime.now(UTC) + timedelta(days=60)
    updated = opp.update(
        name="Updated Deal",
        amount=Money.from_float(75000.0, "USD"),
        close_date=new_close,
        description="Updated description",
    )
    assert updated.name == "Updated Deal"
    assert updated.amount.amount_float == 75000.0
    assert updated.description == "Updated description"


def test_update_emits_opportunity_updated_event():
    opp = make_opportunity()
    updated = opp.update(name="Changed Name")
    events = [e for e in updated.domain_events if isinstance(e, OpportunityUpdatedEvent)]
    assert len(events) == 1


def test_probability_updates_on_stage_change():
    opp = make_opportunity()
    qualified = opp.change_stage(OpportunityStage.QUALIFICATION)
    assert qualified.probability == 20
    proposal = qualified.change_stage(OpportunityStage.NEEDS_ANALYSIS).change_stage(
        OpportunityStage.VALUE_PROPOSITION
    ).change_stage(OpportunityStage.DECISION_MAKERS).change_stage(OpportunityStage.PROPOSAL)
    assert proposal.probability == 60


def test_events_accumulate_across_multiple_operations():
    opp = make_opportunity()
    opp2 = opp.change_stage(OpportunityStage.QUALIFICATION)
    opp3 = opp2.change_stage(OpportunityStage.CLOSED_WON)
    # OpportunityCreatedEvent + OpportunityStageChangedEvent (qual) + OpportunityStageChangedEvent (won) + OpportunityWonEvent
    assert len(opp3.domain_events) == 4
