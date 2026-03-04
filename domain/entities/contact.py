"""
Contact Domain Entity

Architectural Intent:
- Entity within the Accounts bounded context
- Associated with accounts through account_id
- Immutable state - all modifications create new instances

Key Design Decisions:
1. Contact is always associated with an account (required)
2. Email is unique per account
3. Lead status tracked for marketing qualification
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects import Email, PhoneNumber
from domain.events import DomainEvent, ContactCreatedEvent, ContactUpdatedEvent


@dataclass(frozen=True)
class Contact:
    id: UUID
    account_id: UUID
    first_name: str
    last_name: str
    email: Email
    owner_id: UUID
    phone: Optional[PhoneNumber] = None
    title: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple[DomainEvent, ...] = field(default_factory=tuple)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @staticmethod
    def create(
        account_id: UUID,
        first_name: str,
        last_name: str,
        email: Email,
        owner_id: UUID,
        phone: Optional[PhoneNumber] = None,
        title: Optional[str] = None,
        department: Optional[str] = None,
    ) -> "Contact":
        contact_id = uuid4()
        now = datetime.now(UTC)
        return Contact(
            id=contact_id,
            account_id=account_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            title=title,
            department=department,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            domain_events=(
                ContactCreatedEvent(
                    aggregate_id=str(contact_id),
                    occurred_at=now,
                    contact_name=f"{first_name} {last_name}",
                    account_id=str(account_id),
                ),
            ),
        )

    def update(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[Email] = None,
        phone: Optional[PhoneNumber] = None,
        title: Optional[str] = None,
        department: Optional[str] = None,
        owner_id: Optional[UUID] = None,
    ) -> "Contact":
        now = datetime.now(UTC)
        return replace(
            self,
            first_name=first_name if first_name is not None else self.first_name,
            last_name=last_name if last_name is not None else self.last_name,
            email=email if email is not None else self.email,
            phone=phone if phone is not None else self.phone,
            title=title if title is not None else self.title,
            department=department if department is not None else self.department,
            owner_id=owner_id if owner_id is not None else self.owner_id,
            updated_at=now,
            domain_events=self.domain_events
            + (
                ContactUpdatedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                ),
            ),
        )

    def deactivate(self) -> "Contact":
        if not self.is_active:
            return self
        now = datetime.now(UTC)
        return replace(
            self,
            is_active=False,
            updated_at=now,
            domain_events=self.domain_events
            + (
                ContactUpdatedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                ),
            ),
        )
