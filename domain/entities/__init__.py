"""
Domain Entities

Architectural Intent:
- Core domain entities following DDD principles
- Immutable state with domain methods for state transitions
- Domain events emitted for state changes
"""

from domain.entities.account import Account
from domain.entities.contact import Contact
from domain.entities.opportunity import Opportunity, OpportunityStage, OpportunitySource
from domain.entities.lead import Lead, LeadStatus, LeadRating
from domain.entities.case import Case, CaseStatus, CasePriority, CaseOrigin

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
]
