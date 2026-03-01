"""
Domain Layer

Architectural Intent:
- Core business logic and entities
- Zero dependencies on infrastructure or external frameworks
- Follows DDD principles with bounded contexts
"""

from domain.entities import (
    Account,
    Contact,
    Opportunity,
    OpportunityStage,
    OpportunitySource,
    Lead,
    LeadStatus,
    LeadRating,
    Case,
    CaseStatus,
    CasePriority,
    CaseOrigin,
)
from domain.value_objects import (
    Industry,
    IndustryType,
    Territory,
    Money,
    Email,
    PhoneNumber,
)
from domain.events import (
    DomainEvent,
    AccountCreatedEvent,
    AccountUpdatedEvent,
    ContactCreatedEvent,
    ContactUpdatedEvent,
    OpportunityCreatedEvent,
    OpportunityStageChangedEvent,
    OpportunityWonEvent,
    OpportunityLostEvent,
    LeadCreatedEvent,
    LeadStatusChangedEvent,
    LeadConvertedEvent,
    CaseCreatedEvent,
    CaseStatusChangedEvent,
    CaseResolvedEvent,
)
from domain.ports.repository_ports import (
    AccountRepositoryPort,
    ContactRepositoryPort,
    OpportunityRepositoryPort,
    LeadRepositoryPort,
    CaseRepositoryPort,
)
from domain.ports import (
    NotificationPort,
    EventBusPort,
    AuthenticationPort,
    AuditLogPort,
    SearchPort,
)

__all__ = [
    "Account",
    "Contact",
    "Opportunity",
    "OpportunityStage",
    "OpportunitySource",
    "Lead",
    "LeadStatus",
    "LeadRating",
    "Case",
    "CaseStatus",
    "CasePriority",
    "CaseOrigin",
    "Industry",
    "IndustryType",
    "Territory",
    "Money",
    "Email",
    "PhoneNumber",
    "DomainEvent",
    "AccountCreatedEvent",
    "AccountUpdatedEvent",
    "ContactCreatedEvent",
    "ContactUpdatedEvent",
    "OpportunityCreatedEvent",
    "OpportunityStageChangedEvent",
    "OpportunityWonEvent",
    "OpportunityLostEvent",
    "LeadCreatedEvent",
    "LeadStatusChangedEvent",
    "LeadConvertedEvent",
    "CaseCreatedEvent",
    "CaseStatusChangedEvent",
    "CaseResolvedEvent",
    "AccountRepositoryPort",
    "ContactRepositoryPort",
    "OpportunityRepositoryPort",
    "LeadRepositoryPort",
    "CaseRepositoryPort",
    "NotificationPort",
    "EventBusPort",
    "AuthenticationPort",
    "AuditLogPort",
    "SearchPort",
]
