"""
Quote & Contract Entities

Architectural Intent:
- Quote generation and approval workflow
- Contract lifecycle management
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, List
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class QuoteLineItem:
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    discount_percent: float = 0.0

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price * (1 - self.discount_percent / 100)


@dataclass(frozen=True)
class Quote:
    id: str
    opportunity_id: str
    name: str
    status: QuoteStatus
    line_items: tuple
    currency: str
    owner_id: str
    org_id: str
    valid_until: Optional[datetime] = None
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_amount(self) -> float:
        return sum(item.total_price for item in self.line_items)

    @staticmethod
    def create(
        id: str,
        opportunity_id: str,
        name: str,
        line_items: List[QuoteLineItem],
        currency: str,
        owner_id: str,
        org_id: str,
        valid_until: Optional[datetime] = None,
    ) -> "Quote":
        return Quote(
            id=id,
            opportunity_id=opportunity_id,
            name=name,
            status=QuoteStatus.DRAFT,
            line_items=tuple(line_items),
            currency=currency,
            owner_id=owner_id,
            org_id=org_id,
            valid_until=valid_until,
        )
