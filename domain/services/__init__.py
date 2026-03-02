"""
Domain Services

Architectural Intent:
- Business logic that spans multiple entities
- Stateless operations on domain objects
- No infrastructure dependencies
"""

from typing import List, Dict
from domain.entities import Account, Lead, Opportunity


class PricingService:
    """Calculate prices with discounts, taxes, and multi-currency support."""

    def calculate_line_total(
        self, unit_price: float, quantity: int, discount_percent: float = 0.0
    ) -> float:
        return unit_price * quantity * (1 - discount_percent / 100)

    def calculate_quote_total(self, line_items: list) -> float:
        return sum(
            self.calculate_line_total(
                item.unit_price, item.quantity, item.discount_percent
            )
            for item in line_items
        )


class DeduplicationService:
    """Detect duplicate records using fuzzy matching."""

    def find_duplicate_accounts(
        self, name: str, existing: List[Account], threshold: float = 0.8
    ) -> List[Account]:
        matches = []
        normalized = name.lower().strip()
        for account in existing:
            similarity = self._similarity(normalized, account.name.lower().strip())
            if similarity >= threshold:
                matches.append(account)
        return matches

    def _similarity(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        # Simple Jaccard similarity on character bigrams
        bigrams_a = set(a[i : i + 2] for i in range(len(a) - 1))
        bigrams_b = set(b[i : i + 2] for i in range(len(b) - 1))
        if not bigrams_a or not bigrams_b:
            return 0.0
        intersection = bigrams_a & bigrams_b
        union = bigrams_a | bigrams_b
        return len(intersection) / len(union)


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


class ForecastingService:
    """Revenue forecasting based on pipeline data."""

    def calculate_weighted_pipeline(self, opportunities: List[Opportunity]) -> float:
        return sum(opp.weighted_value for opp in opportunities if not opp.is_closed)

    def forecast_by_stage(
        self, opportunities: List[Opportunity]
    ) -> Dict[str, Dict[str, float]]:
        stages: Dict[str, Dict[str, float]] = {}
        for opp in opportunities:
            if opp.is_closed:
                continue
            stage = opp.stage.value if hasattr(opp.stage, "value") else str(opp.stage)
            if stage not in stages:
                stages[stage] = {"count": 0, "total": 0.0, "weighted": 0.0}
            stages[stage]["count"] += 1
            stages[stage]["total"] += opp.amount
            stages[stage]["weighted"] += opp.weighted_value
        return stages
