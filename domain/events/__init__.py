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


@dataclass(frozen=True)
class AccountCreatedEvent(DomainEvent):
    account_name: str = ""


@dataclass(frozen=True)
class AccountUpdatedEvent(DomainEvent):
    pass


@dataclass(frozen=True)
class ContactCreatedEvent(DomainEvent):
    contact_name: str = ""
    account_id: str = ""


@dataclass(frozen=True)
class ContactUpdatedEvent(DomainEvent):
    pass


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


@dataclass(frozen=True)
class LeadCreatedEvent(DomainEvent):
    lead_name: str = ""
    email: str = ""


@dataclass(frozen=True)
class LeadStatusChangedEvent(DomainEvent):
    old_status: str = ""
    new_status: str = ""


@dataclass(frozen=True)
class LeadConvertedEvent(DomainEvent):
    account_id: str = ""
    contact_id: str = ""
    opportunity_id: str = ""


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
