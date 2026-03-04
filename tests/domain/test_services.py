"""Tests for domain services: Pricing, Deduplication, LeadScoring, Forecasting."""

from dataclasses import dataclass
from domain.services import (
    PricingService,
    DeduplicationService,
    LeadScoringService,
    ForecastingService,
)
from domain.value_objects import Money


# ---------- PricingService ----------


class TestPricingService:
    def setup_method(self):
        self.svc = PricingService()

    def test_line_total_no_discount(self):
        assert self.svc.calculate_line_total(100.0, 5) == 500.0

    def test_line_total_with_discount(self):
        assert self.svc.calculate_line_total(100.0, 10, 10.0) == 900.0

    def test_line_total_full_discount(self):
        assert self.svc.calculate_line_total(100.0, 10, 100.0) == 0.0

    def test_quote_total_multiple_items(self):
        @dataclass
        class LineItem:
            unit_price: float
            quantity: int
            discount_percent: float

        items = [
            LineItem(100.0, 2, 0.0),  # 200
            LineItem(50.0, 3, 10.0),  # 135
            LineItem(200.0, 1, 25.0),  # 150
        ]
        assert self.svc.calculate_quote_total(items) == 485.0

    def test_quote_total_empty(self):
        assert self.svc.calculate_quote_total([]) == 0.0


# ---------- DeduplicationService ----------


class TestDeduplicationService:
    def setup_method(self):
        self.svc = DeduplicationService()

    def test_exact_match(self):
        @dataclass
        class FakeAccount:
            name: str

        accounts = [FakeAccount("Acme Corp")]
        matches = self.svc.find_duplicate_accounts("Acme Corp", accounts)
        assert len(matches) == 1

    def test_fuzzy_match(self):
        @dataclass
        class FakeAccount:
            name: str

        accounts = [FakeAccount("Acme Corporation")]
        matches = self.svc.find_duplicate_accounts("Acme Corp", accounts, threshold=0.5)
        assert len(matches) == 1

    def test_below_threshold(self):
        @dataclass
        class FakeAccount:
            name: str

        accounts = [FakeAccount("Completely Different")]
        matches = self.svc.find_duplicate_accounts("Acme Corp", accounts)
        assert len(matches) == 0

    def test_empty_existing_list(self):
        matches = self.svc.find_duplicate_accounts("Acme", [])
        assert len(matches) == 0

    def test_similarity_identical(self):
        assert self.svc._similarity("hello", "hello") == 1.0

    def test_similarity_empty(self):
        assert self.svc._similarity("", "hello") == 0.0


# ---------- LeadScoringService ----------


class TestLeadScoringService:
    def setup_method(self):
        self.svc = LeadScoringService()

    def test_full_fit_score(self):
        @dataclass
        class FakeLead:
            company: str = "Acme"
            email: str = "a@b.com"
            phone: str = "555"
            title: str = "CTO"

        lead = FakeLead()
        score = self.svc.score(lead)
        assert score == 45  # 20 + 10 + 5 + 10

    def test_empty_lead_score(self):
        @dataclass
        class FakeLead:
            company: str = ""
            email: str = ""
            phone: str = ""
            title: str = ""

        lead = FakeLead()
        score = self.svc.score(lead)
        assert score == 0

    def test_engagement_signals(self):
        @dataclass
        class FakeLead:
            company: str = "Acme"
            email: str = "a@b.com"
            phone: str = ""
            title: str = ""

        lead = FakeLead()
        signals = {"email_opens": 5, "page_views": 3, "form_submissions": 1}
        score = self.svc.score(lead, signals)
        # 20 + 10 + 5*2 + 3*1 + 1*15 = 58
        assert score == 58

    def test_score_capped_at_100(self):
        @dataclass
        class FakeLead:
            company: str = "Acme"
            email: str = "a@b.com"
            phone: str = "555"
            title: str = "CEO"

        lead = FakeLead()
        signals = {"demo_requests": 10}  # 250 points from demos alone
        score = self.svc.score(lead, signals)
        assert score == 100


# ---------- ForecastingService ----------


class TestForecastingService:
    def setup_method(self):
        self.svc = ForecastingService()

    def test_weighted_pipeline_empty(self):
        assert self.svc.calculate_weighted_pipeline([]) == 0.0

    def test_weighted_pipeline(self):
        @dataclass
        class FakeOpp:
            weighted_value: Money
            is_closed: bool

        opps = [
            FakeOpp(Money.from_float(1000.0, "USD"), False),
            FakeOpp(Money.from_float(2000.0, "USD"), False),
            FakeOpp(Money.from_float(500.0, "USD"), True),  # closed, excluded
        ]
        assert self.svc.calculate_weighted_pipeline(opps) == 3000.0

    def test_forecast_by_stage(self):
        @dataclass
        class FakeOpp:
            stage: str
            amount: Money
            weighted_value: Money
            is_closed: bool

        opps = [
            FakeOpp("prospecting", Money.from_float(1000.0, "USD"), Money.from_float(100.0, "USD"), False),
            FakeOpp("prospecting", Money.from_float(2000.0, "USD"), Money.from_float(200.0, "USD"), False),
            FakeOpp("negotiation", Money.from_float(5000.0, "USD"), Money.from_float(4000.0, "USD"), False),
            FakeOpp("closed_won", Money.from_float(3000.0, "USD"), Money.from_float(3000.0, "USD"), True),
        ]
        result = self.svc.forecast_by_stage(opps)
        assert result["prospecting"]["count"] == 2
        assert result["prospecting"]["total"] == 3000.0
        assert result["negotiation"]["weighted"] == 4000.0
        assert "closed_won" not in result

    def test_forecast_by_stage_empty(self):
        result = self.svc.forecast_by_stage([])
        assert result == {}
