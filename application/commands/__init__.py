"""
Application Commands

Architectural Intent:
- Command handlers for write operations
- Each command is a use case that orchestrates domain entities
"""

from application.commands.account_commands import (
    CreateAccountCommand,
    UpdateAccountCommand,
    DeactivateAccountCommand,
)
from application.commands.contact_commands import (
    CreateContactCommand,
    UpdateContactCommand,
)
from application.commands.opportunity_commands import (
    CreateOpportunityCommand,
    UpdateOpportunityStageCommand,
    UpdateOpportunityCommand,
)
from application.commands.lead_commands import (
    CreateLeadCommand,
    QualifyLeadCommand,
    ConvertLeadCommand,
)
from application.commands.case_commands import (
    CreateCaseCommand,
    UpdateCaseStatusCommand,
    ResolveCaseCommand,
    CloseCaseCommand,
)

__all__ = [
    "CreateAccountCommand",
    "UpdateAccountCommand",
    "DeactivateAccountCommand",
    "CreateContactCommand",
    "UpdateContactCommand",
    "CreateOpportunityCommand",
    "UpdateOpportunityStageCommand",
    "UpdateOpportunityCommand",
    "CreateLeadCommand",
    "QualifyLeadCommand",
    "ConvertLeadCommand",
    "CreateCaseCommand",
    "UpdateCaseStatusCommand",
    "ResolveCaseCommand",
    "CloseCaseCommand",
]
