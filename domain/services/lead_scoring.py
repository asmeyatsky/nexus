"""Lead Scoring Service — score leads based on engagement and fit criteria."""

from typing import Dict
from domain.entities import Lead


class LeadScoringService:
    """Score leads based on engagement and fit criteria."""

    def score(self, lead: Lead, engagement_signals: Dict[str, int] = None) -> int:
        score = 0
        # Fit scoring
        if lead.company:
            score += 20
        if lead.email:
            score += 10
        if lead.phone:
            score += 5
        if lead.title:
            score += 10

        # Engagement scoring
        if engagement_signals:
            score += engagement_signals.get("email_opens", 0) * 2
            score += engagement_signals.get("page_views", 0) * 1
            score += engagement_signals.get("form_submissions", 0) * 15
            score += engagement_signals.get("demo_requests", 0) * 25

        return min(score, 100)
