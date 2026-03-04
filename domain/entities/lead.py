"""
Lead Domain Entity

Architectural Intent:
- Entity for marketing lead management bounded context
- Tracks lead through qualification process
- Converted to Account/Contact/Opportunity upon qualification

Key Design Decisions:
1. Lead status managed as state machine
2. Rating indicates lead quality (hot/warm/cold)
3. Conversion creates new Account, Contact, and optionally Opportunity
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects import Email, PhoneNumber
from domain.events import (
    DomainEvent,
    LeadCreatedEvent,
    LeadStatusChangedEvent,
    LeadConvertedEvent,
)


class LeadStatus(Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    UNQUALIFIED = "unqualified"
    RECYCLED = "recycled"


class LeadRating(Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


VALID_STATUS_TRANSITIONS = {
    LeadStatus.NEW: {
        LeadStatus.CONTACTED,
        LeadStatus.QUALIFIED,
        LeadStatus.UNQUALIFIED,
        LeadStatus.RECYCLED,
    },
    LeadStatus.CONTACTED: {
        LeadStatus.QUALIFIED,
        LeadStatus.UNQUALIFIED,
        LeadStatus.RECYCLED,
    },
    LeadStatus.QUALIFIED: {
        LeadStatus.CONVERTED,
        LeadStatus.UNQUALIFIED,
        LeadStatus.RECYCLED,
    },
    LeadStatus.CONVERTED: set(),
    LeadStatus.UNQUALIFIED: set(),
    LeadStatus.RECYCLED: {LeadStatus.NEW},
}


@dataclass(frozen=True)
class Lead:
    id: UUID
    first_name: str
    last_name: str
    email: Email
    company: str
    status: LeadStatus
    rating: LeadRating
    owner_id: UUID
    source: Optional[str] = None
    phone: Optional[PhoneNumber] = None
    title: Optional[str] = None
    website: Optional[str] = None
    converted_account_id: Optional[UUID] = None
    converted_contact_id: Optional[UUID] = None
    converted_opportunity_id: Optional[UUID] = None
    converted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple[DomainEvent, ...] = field(default_factory=tuple)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @staticmethod
    def create(
        first_name: str,
        last_name: str,
        email: Email,
        company: str,
        owner_id: UUID,
        source: Optional[str] = None,
        phone: Optional[PhoneNumber] = None,
        title: Optional[str] = None,
        website: Optional[str] = None,
    ) -> "Lead":
        lead_id = uuid4()
        now = datetime.now(UTC)
        return Lead(
            id=lead_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            company=company,
            status=LeadStatus.NEW,
            rating=LeadRating.COLD,
            owner_id=owner_id,
            source=source,
            phone=phone,
            title=title,
            website=website,
            created_at=now,
            updated_at=now,
            domain_events=(
                LeadCreatedEvent(
                    aggregate_id=str(lead_id),
                    occurred_at=now,
                    lead_name=f"{first_name} {last_name}",
                    email=str(email),
                ),
            ),
        )

    def change_status(self, new_status: LeadStatus) -> "Lead":
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
                LeadStatusChangedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    old_status=self.status.value,
                    new_status=new_status.value,
                ),
            ),
        )

    def convert(
        self,
        account_id: UUID,
        contact_id: UUID,
        opportunity_id: Optional[UUID] = None,
    ) -> "Lead":
        if LeadStatus.CONVERTED not in VALID_STATUS_TRANSITIONS.get(self.status, set()):
            raise ValueError(
                f"Cannot convert lead from {self.status.value} status. Lead must be QUALIFIED first."
            )
        now = datetime.now(UTC)
        return replace(
            self,
            status=LeadStatus.CONVERTED,
            converted_account_id=account_id,
            converted_contact_id=contact_id,
            converted_opportunity_id=opportunity_id,
            converted_at=now,
            updated_at=now,
            domain_events=self.domain_events
            + (
                LeadConvertedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    account_id=str(account_id),
                    contact_id=str(contact_id),
                    opportunity_id=str(opportunity_id) if opportunity_id else "",
                ),
            ),
        )

    def update_rating(self, rating: LeadRating) -> "Lead":
        now = datetime.now(UTC)
        return replace(
            self,
            rating=rating,
            updated_at=now,
            domain_events=self.domain_events
            + (
                LeadStatusChangedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    old_status=self.status.value,
                    new_status=self.status.value,
                ),
            ),
        )
