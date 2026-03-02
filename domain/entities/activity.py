"""
Activity Entity

Architectural Intent:
- Track all user activities (calls, emails, meetings, tasks)
- Immutable state with factory methods
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from enum import Enum


class ActivityType(Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"


class ActivityStatus(Enum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Activity:
    id: str
    activity_type: ActivityType
    subject: str
    description: str
    status: ActivityStatus
    owner_id: str
    related_entity_type: str
    related_entity_id: str
    org_id: str
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _events: list = field(default_factory=list, compare=False, repr=False)

    @staticmethod
    def create(
        id: str,
        activity_type: ActivityType,
        subject: str,
        description: str,
        owner_id: str,
        related_entity_type: str,
        related_entity_id: str,
        org_id: str,
        due_date: Optional[datetime] = None,
    ) -> "Activity":
        return Activity(
            id=id,
            activity_type=activity_type,
            subject=subject,
            description=description,
            status=ActivityStatus.OPEN,
            owner_id=owner_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            org_id=org_id,
            due_date=due_date,
        )

    def complete(self) -> "Activity":
        now = datetime.now(UTC)
        return Activity(
            id=self.id,
            activity_type=self.activity_type,
            subject=self.subject,
            description=self.description,
            status=ActivityStatus.COMPLETED,
            owner_id=self.owner_id,
            related_entity_type=self.related_entity_type,
            related_entity_id=self.related_entity_id,
            org_id=self.org_id,
            due_date=self.due_date,
            completed_at=now,
            created_at=self.created_at,
            updated_at=now,
        )
