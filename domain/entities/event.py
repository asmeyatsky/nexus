"""
Event/Webinar Entity

Architectural Intent:
- Event and webinar management
- Registration tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from enum import Enum


class EventStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(Enum):
    WEBINAR = "webinar"
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    MEETUP = "meetup"


@dataclass(frozen=True)
class Event:
    id: str
    name: str
    event_type: EventType
    status: EventStatus
    start_date: datetime
    end_date: datetime
    location: str
    max_attendees: int
    campaign_id: Optional[str]
    owner_id: str
    org_id: str
    description: str = ""
    registered_count: int = 0
    attended_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        name: str,
        event_type: EventType,
        start_date: datetime,
        end_date: datetime,
        location: str,
        max_attendees: int,
        owner_id: str,
        org_id: str,
        campaign_id: Optional[str] = None,
        description: str = "",
    ) -> "Event":
        return Event(
            id=id,
            name=name,
            event_type=event_type,
            status=EventStatus.DRAFT,
            start_date=start_date,
            end_date=end_date,
            location=location,
            max_attendees=max_attendees,
            campaign_id=campaign_id,
            owner_id=owner_id,
            org_id=org_id,
            description=description,
        )
