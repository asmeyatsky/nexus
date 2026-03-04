"""
Account Domain Entity

Architectural Intent:
- Core aggregate for account management bounded context
- Immutable state - all modifications create new instances
- Domain events emitted for state changes

Key Design Decisions:
1. Account is the primary organizational entity in the CRM
2. Relations are managed through value objects
3. Industry and territory use standardized value objects
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects import Industry, Territory, Money
from domain.events import DomainEvent, AccountCreatedEvent, AccountUpdatedEvent


@dataclass(frozen=True)
class Account:
    id: UUID
    name: str
    industry: Industry
    territory: Territory
    owner_id: UUID
    website: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    annual_revenue: Optional[Money] = None
    employee_count: Optional[int] = None
    parent_account_id: Optional[UUID] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple[DomainEvent, ...] = field(default_factory=tuple)

    @staticmethod
    def create(
        name: str,
        industry: Industry,
        territory: Territory,
        owner_id: UUID,
        website: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> "Account":
        account_id = uuid4()
        now = datetime.now(UTC)
        account = Account(
            id=account_id,
            name=name,
            industry=industry,
            territory=territory,
            website=website,
            phone=phone,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            domain_events=(
                AccountCreatedEvent(
                    aggregate_id=str(account_id),
                    occurred_at=now,
                    account_name=name,
                ),
            ),
        )
        return account

    def update(
        self,
        name: Optional[str] = None,
        industry: Optional[Industry] = None,
        territory: Optional[Territory] = None,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        billing_address: Optional[str] = None,
        annual_revenue: Optional[Money] = None,
        employee_count: Optional[int] = None,
        owner_id: Optional[UUID] = None,
    ) -> "Account":
        now = datetime.now(UTC)
        events = list(self.domain_events)

        events.append(
            AccountUpdatedEvent(
                aggregate_id=str(self.id),
                occurred_at=now,
            )
        )

        return replace(
            self,
            name=name if name is not None else self.name,
            industry=industry if industry is not None else self.industry,
            territory=territory if territory is not None else self.territory,
            website=website if website is not None else self.website,
            phone=phone if phone is not None else self.phone,
            billing_address=billing_address
            if billing_address is not None
            else self.billing_address,
            annual_revenue=annual_revenue
            if annual_revenue is not None
            else self.annual_revenue,
            employee_count=employee_count
            if employee_count is not None
            else self.employee_count,
            owner_id=owner_id if owner_id is not None else self.owner_id,
            updated_at=now,
            domain_events=tuple(events),
        )

    def deactivate(self) -> "Account":
        if not self.is_active:
            return self
        now = datetime.now(UTC)
        return replace(
            self,
            is_active=False,
            updated_at=now,
            domain_events=self.domain_events
            + (
                AccountUpdatedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                ),
            ),
        )

    def activate(self) -> "Account":
        if not self.is_active:
            now = datetime.now(UTC)
            return replace(
                self,
                is_active=True,
                updated_at=now,
                domain_events=self.domain_events
                + (
                    AccountUpdatedEvent(
                        aggregate_id=str(self.id),
                        occurred_at=now,
                    ),
                ),
            )
        return self
