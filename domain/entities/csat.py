"""
Customer Satisfaction Entity

Architectural Intent:
- CSAT survey tracking
- NPS score calculation
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from enum import Enum


@dataclass(frozen=True)
class CSATSurvey:
    id: str
    case_id: str
    contact_id: str
    score: int  # 1-5
    comment: str
    org_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        case_id: str,
        contact_id: str,
        score: int,
        comment: str,
        org_id: str,
    ) -> "CSATSurvey":
        if not 1 <= score <= 5:
            raise ValueError("CSAT score must be between 1 and 5")
        return CSATSurvey(
            id=id,
            case_id=case_id,
            contact_id=contact_id,
            score=score,
            comment=comment,
            org_id=org_id,
        )
