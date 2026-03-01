"""
Case Domain Entity

Architectural Intent:
- Entity for customer support bounded context
- Tracks customer support tickets
- Managed through resolution workflow

Key Design Decisions:
1. Case status managed as state machine
2. Priority indicates urgency (high/medium/low)
3. Origin indicates how the case was created
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from domain.events import (
    DomainEvent,
    CaseCreatedEvent,
    CaseStatusChangedEvent,
    CaseResolvedEvent,
)


class CaseStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_THIRD_PARTY = "waiting_on_third_party"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseOrigin(Enum):
    EMAIL = "email"
    PHONE = "phone"
    WEB = "web"
    CHAT = "chat"
    SOCIAL = "social"
    PARTNER = "partner"


VALID_STATUS_TRANSITIONS = {
    CaseStatus.NEW: {CaseStatus.IN_PROGRESS, CaseStatus.CLOSED},
    CaseStatus.IN_PROGRESS: {
        CaseStatus.WAITING_ON_CUSTOMER,
        CaseStatus.WAITING_ON_THIRD_PARTY,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    },
    CaseStatus.WAITING_ON_CUSTOMER: {
        CaseStatus.IN_PROGRESS,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    },
    CaseStatus.WAITING_ON_THIRD_PARTY: {
        CaseStatus.IN_PROGRESS,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    },
    CaseStatus.RESOLVED: {CaseStatus.CLOSED, CaseStatus.IN_PROGRESS},
    CaseStatus.CLOSED: set(),
}


@dataclass(frozen=True)
class Case:
    id: UUID
    case_number: str
    subject: str
    description: str
    account_id: UUID
    contact_id: Optional[UUID]
    status: CaseStatus
    priority: CasePriority
    origin: CaseOrigin
    owner_id: UUID
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: Optional[datetime] = None
    domain_events: tuple[DomainEvent, ...] = field(default_factory=tuple)

    @staticmethod
    def create(
        subject: str,
        description: str,
        account_id: UUID,
        owner_id: UUID,
        case_number: str,
        contact_id: Optional[UUID] = None,
        priority: CasePriority = CasePriority.MEDIUM,
        origin: CaseOrigin = CaseOrigin.WEB,
    ) -> "Case":
        case_id = uuid4()
        now = datetime.now(UTC)
        return Case(
            id=case_id,
            case_number=case_number,
            subject=subject,
            description=description,
            account_id=account_id,
            contact_id=contact_id,
            status=CaseStatus.NEW,
            priority=priority,
            origin=origin,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            domain_events=(
                CaseCreatedEvent(
                    aggregate_id=str(case_id),
                    occurred_at=now,
                    case_number=case_number,
                    subject=subject,
                    account_id=str(account_id),
                ),
            ),
        )

    def change_status(self, new_status: CaseStatus) -> "Case":
        if new_status not in VALID_STATUS_TRANSITIONS.get(self.status, set()):
            raise ValueError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )

        now = datetime.now(UTC)
        return replace(
            self,
            status=new_status,
            updated_at=now,
            domain_events=self.domain_events
            + (
                CaseStatusChangedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    old_status=self.status.value,
                    new_status=new_status.value,
                    priority=self.priority.value,
                ),
            ),
        )

    def resolve(self, resolution_notes: str, resolved_by: str) -> "Case":
        now = datetime.now(UTC)
        return replace(
            self,
            status=CaseStatus.RESOLVED,
            resolution_notes=resolution_notes,
            resolved_by=resolved_by,
            resolved_at=now,
            updated_at=now,
            domain_events=self.domain_events
            + (
                CaseResolvedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    resolution_notes=resolution_notes,
                    resolved_by=resolved_by,
                ),
            ),
        )

    def close(self) -> "Case":
        now = datetime.now(UTC)
        return replace(
            self,
            status=CaseStatus.CLOSED,
            closed_at=now,
            updated_at=now,
        )

    def escalate(self) -> "Case":
        new_priority = (
            CasePriority.HIGH if self.priority != CasePriority.HIGH else self.priority
        )
        now = datetime.now(UTC)
        return replace(
            self,
            priority=new_priority,
            updated_at=now,
        )
