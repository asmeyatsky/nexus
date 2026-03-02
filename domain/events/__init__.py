"""
Domain Events Base

Architectural Intent:
- Base classes for domain events following DDD patterns
- Events are immutable and contain occurrence timestamp
- Used for cross-context communication
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    aggregate_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "event_type", self.__class__.__name__)


# Account Events
@dataclass(frozen=True)
class AccountCreatedEvent(DomainEvent):
    account_name: str = ""


@dataclass(frozen=True)
class AccountUpdatedEvent(DomainEvent):
    pass


@dataclass(frozen=True)
class AccountDeactivatedEvent(DomainEvent):
    pass


# Contact Events
@dataclass(frozen=True)
class ContactCreatedEvent(DomainEvent):
    contact_name: str = ""
    account_id: str = ""


@dataclass(frozen=True)
class ContactUpdatedEvent(DomainEvent):
    pass


# Opportunity Events
@dataclass(frozen=True)
class OpportunityCreatedEvent(DomainEvent):
    opportunity_name: str = ""
    account_id: str = ""
    amount: float = 0.0


@dataclass(frozen=True)
class OpportunityStageChangedEvent(DomainEvent):
    old_stage: str = ""
    new_stage: str = ""
    amount: float = 0.0


@dataclass(frozen=True)
class OpportunityWonEvent(DomainEvent):
    amount: float = 0.0
    closed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class OpportunityLostEvent(DomainEvent):
    amount: float = 0.0
    reason: str = ""


# Lead Events
@dataclass(frozen=True)
class LeadCreatedEvent(DomainEvent):
    lead_name: str = ""
    email: str = ""


@dataclass(frozen=True)
class LeadStatusChangedEvent(DomainEvent):
    old_status: str = ""
    new_status: str = ""


@dataclass(frozen=True)
class LeadQualifiedEvent(DomainEvent):
    score: int = 0


@dataclass(frozen=True)
class LeadConvertedEvent(DomainEvent):
    account_id: str = ""
    contact_id: str = ""
    opportunity_id: str = ""


# Case Events
@dataclass(frozen=True)
class CaseCreatedEvent(DomainEvent):
    case_number: str = ""
    subject: str = ""
    account_id: str = ""


@dataclass(frozen=True)
class CaseStatusChangedEvent(DomainEvent):
    old_status: str = ""
    new_status: str = ""
    priority: str = ""


@dataclass(frozen=True)
class CaseResolvedEvent(DomainEvent):
    resolution_notes: str = ""
    resolved_by: str = ""


@dataclass(frozen=True)
class CaseEscalatedEvent(DomainEvent):
    priority: str = ""
    reason: str = ""


# Campaign Events
@dataclass(frozen=True)
class CampaignCreatedEvent(DomainEvent):
    campaign_name: str = ""


@dataclass(frozen=True)
class CampaignActivatedEvent(DomainEvent):
    pass


@dataclass(frozen=True)
class CampaignCompletedEvent(DomainEvent):
    pass


# Activity Events
@dataclass(frozen=True)
class ActivityCreatedEvent(DomainEvent):
    activity_type: str = ""
    subject: str = ""


@dataclass(frozen=True)
class ActivityCompletedEvent(DomainEvent):
    pass


# Quote Events
@dataclass(frozen=True)
class QuoteCreatedEvent(DomainEvent):
    opportunity_id: str = ""
    amount: float = 0.0


@dataclass(frozen=True)
class QuoteAcceptedEvent(DomainEvent):
    amount: float = 0.0
