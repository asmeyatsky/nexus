"""
Domain Entity Tests

Tests for all domain entities — immutability, factory methods, state transitions.
"""

import pytest
from uuid import uuid4


class TestAccount:
    def test_create_account(self):
        from domain.entities.account import Account
        from domain.value_objects import Industry, Territory

        account = Account.create(
            name="Acme Corp",
            industry=Industry.from_string("technology"),
            territory=Territory(region="north_america"),
            owner_id=uuid4(),
        )
        assert account.name == "Acme Corp"
        assert account.is_active is True

    def test_account_is_frozen(self):
        from domain.entities.account import Account
        from domain.value_objects import Industry, Territory

        account = Account.create(
            name="Test",
            industry=Industry.from_string("technology"),
            territory=Territory(region="europe"),
            owner_id=uuid4(),
        )
        with pytest.raises(AttributeError):
            account.name = "Changed"


class TestActivity:
    def test_create_activity(self):
        from domain.entities.activity import Activity, ActivityType, ActivityStatus

        activity = Activity.create(
            id="act-1",
            activity_type=ActivityType.CALL,
            subject="Follow-up call",
            description="Discuss proposal",
            owner_id="user-1",
            related_entity_type="account",
            related_entity_id="acc-1",
            org_id="org-1",
        )
        assert activity.status == ActivityStatus.OPEN
        assert activity.activity_type == ActivityType.CALL

    def test_complete_activity(self):
        from domain.entities.activity import Activity, ActivityType, ActivityStatus

        activity = Activity.create(
            id="act-1",
            activity_type=ActivityType.TASK,
            subject="Task",
            description="Do it",
            owner_id="u1",
            related_entity_type="lead",
            related_entity_id="l1",
            org_id="org-1",
        )
        completed = activity.complete()
        assert completed.status == ActivityStatus.COMPLETED
        assert completed.completed_at is not None


class TestCampaign:
    def test_create_campaign(self):
        from domain.entities.campaign import Campaign, CampaignType, CampaignStatus

        campaign = Campaign.create(
            id="camp-1",
            name="Q1 Email Blast",
            campaign_type=CampaignType.EMAIL,
            budget=10000.0,
            currency="USD",
            owner_id="user-1",
            org_id="org-1",
        )
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.budget == 10000.0

    def test_activate_campaign(self):
        from domain.entities.campaign import Campaign, CampaignType, CampaignStatus

        campaign = Campaign.create(
            id="camp-1",
            name="Test",
            campaign_type=CampaignType.WEBINAR,
            budget=5000.0,
            currency="USD",
            owner_id="u1",
            org_id="org-1",
        )
        active = campaign.activate()
        assert active.status == CampaignStatus.ACTIVE


class TestCSAT:
    def test_create_csat(self):
        from domain.entities.csat import CSATSurvey

        survey = CSATSurvey.create(
            id="csat-1",
            case_id="case-1",
            contact_id="ct-1",
            score=4,
            comment="Good support",
            org_id="org-1",
        )
        assert survey.score == 4

    def test_invalid_score(self):
        from domain.entities.csat import CSATSurvey

        with pytest.raises(ValueError):
            CSATSurvey.create(
                id="csat-1",
                case_id="case-1",
                contact_id="ct-1",
                score=6,
                comment="",
                org_id="org-1",
            )


class TestHealthScore:
    def test_calculate_health_score(self):
        from domain.entities.health_score import AccountHealthScore, HealthGrade

        score = AccountHealthScore.calculate(
            id="hs-1",
            account_id="acc-1",
            engagement_score=80,
            revenue_score=90,
            support_score=70,
            org_id="org-1",
        )
        assert score.grade == HealthGrade.EXCELLENT
        assert score.overall_score > 0


class TestRelationship:
    def test_create_relationship(self):
        from domain.entities.relationship import Relationship, RelationshipType

        rel = Relationship.create(
            id="rel-1",
            from_entity_type="account",
            from_entity_id="acc-1",
            to_entity_type="account",
            to_entity_id="acc-2",
            relationship_type=RelationshipType.PARTNER,
            strength=8,
            org_id="org-1",
        )
        assert rel.strength == 8

    def test_invalid_strength(self):
        from domain.entities.relationship import Relationship, RelationshipType

        with pytest.raises(ValueError):
            Relationship.create(
                id="rel-1",
                from_entity_type="account",
                from_entity_id="acc-1",
                to_entity_type="account",
                to_entity_id="acc-2",
                relationship_type=RelationshipType.PARTNER,
                strength=11,
                org_id="org-1",
            )


class TestPipeline:
    def test_create_pipeline(self):
        from domain.entities.pipeline import Pipeline

        pipeline = Pipeline.create(
            id="pipe-1",
            name="Enterprise Sales",
            stages=Pipeline.default_stages(),
            org_id="org-1",
            is_default=True,
        )
        assert len(pipeline.stages) == 7
        assert pipeline.is_default is True


class TestProduct:
    def test_create_product(self):
        from domain.entities.product import Product

        product = Product.create(
            id="prod-1",
            name="CRM License",
            code="CRM-ENT",
            description="Enterprise license",
            family="Software",
            unit_price=99.99,
            currency="USD",
            org_id="org-1",
        )
        assert product.is_active is True
        assert product.unit_price == 99.99


class TestQuote:
    def test_create_quote_with_line_items(self):
        from domain.entities.quote import Quote, QuoteLineItem

        items = [
            QuoteLineItem(
                id="li-1",
                product_id="p1",
                product_name="License",
                quantity=10,
                unit_price=100.0,
                discount_percent=10,
            ),
        ]
        quote = Quote.create(
            id="q-1",
            opportunity_id="opp-1",
            name="Q1 Quote",
            line_items=items,
            currency="USD",
            owner_id="u1",
            org_id="org-1",
        )
        assert quote.total_amount == 900.0


class TestKnowledgeArticle:
    def test_create_and_publish(self):
        from domain.entities.knowledge_article import KnowledgeArticle, ArticleStatus

        article = KnowledgeArticle.create(
            id="ka-1",
            title="How to reset password",
            body="Steps to reset...",
            category="self-service",
            author_id="u1",
            org_id="org-1",
        )
        assert article.status == ArticleStatus.DRAFT
        published = article.publish()
        assert published.status == ArticleStatus.PUBLISHED
