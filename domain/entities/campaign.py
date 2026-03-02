"""
Campaign Entity

Architectural Intent:
- Marketing campaign management
- Immutable state with factory methods
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from enum import Enum


class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class CampaignType(Enum):
    EMAIL = "email"
    WEBINAR = "webinar"
    CONFERENCE = "conference"
    ADVERTISEMENT = "advertisement"
    SOCIAL = "social"
    OTHER = "other"


@dataclass(frozen=True)
class Campaign:
    id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    budget: float
    currency: str
    owner_id: str
    org_id: str
    description: str = ""
    expected_revenue: float = 0.0
    actual_cost: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        name: str,
        campaign_type: CampaignType,
        budget: float,
        currency: str,
        owner_id: str,
        org_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        description: str = "",
    ) -> "Campaign":
        return Campaign(
            id=id,
            name=name,
            campaign_type=campaign_type,
            status=CampaignStatus.DRAFT,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            currency=currency,
            owner_id=owner_id,
            org_id=org_id,
            description=description,
        )

    def activate(self) -> "Campaign":
        return Campaign(
            id=self.id,
            name=self.name,
            campaign_type=self.campaign_type,
            status=CampaignStatus.ACTIVE,
            start_date=self.start_date,
            end_date=self.end_date,
            budget=self.budget,
            currency=self.currency,
            owner_id=self.owner_id,
            org_id=self.org_id,
            description=self.description,
            expected_revenue=self.expected_revenue,
            actual_cost=self.actual_cost,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )
