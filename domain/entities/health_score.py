"""
Account Health Score Entity

Architectural Intent:
- Track account health metrics
- Composite scoring based on engagement, revenue, support
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum


class HealthGrade(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AccountHealthScore:
    id: str
    account_id: str
    overall_score: int  # 0-100
    grade: HealthGrade
    engagement_score: int
    revenue_score: int
    support_score: int
    org_id: str
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def calculate(
        id: str,
        account_id: str,
        engagement_score: int,
        revenue_score: int,
        support_score: int,
        org_id: str,
    ) -> "AccountHealthScore":
        overall = int(engagement_score * 0.4 + revenue_score * 0.35 + support_score * 0.25)
        if overall >= 80:
            grade = HealthGrade.EXCELLENT
        elif overall >= 60:
            grade = HealthGrade.GOOD
        elif overall >= 40:
            grade = HealthGrade.FAIR
        elif overall >= 20:
            grade = HealthGrade.AT_RISK
        else:
            grade = HealthGrade.CRITICAL

        return AccountHealthScore(
            id=id,
            account_id=account_id,
            overall_score=overall,
            grade=grade,
            engagement_score=engagement_score,
            revenue_score=revenue_score,
            support_score=support_score,
            org_id=org_id,
        )
