"""
Domain Entities

Architectural Intent:
- Core domain entities following DDD principles
- Immutable state with domain methods for state transitions
- Domain events emitted for state changes
"""

from domain.entities.account import Account
from domain.entities.contact import Contact
from domain.entities.opportunity import Opportunity, OpportunityStage, OpportunitySource
from domain.entities.lead import Lead, LeadStatus, LeadRating
from domain.entities.case import Case, CaseStatus, CasePriority, CaseOrigin
from domain.entities.activity import Activity, ActivityType, ActivityStatus
from domain.entities.campaign import Campaign, CampaignStatus, CampaignType
from domain.entities.product import Product, PriceBookEntry
from domain.entities.quote import Quote, QuoteStatus, QuoteLineItem
from domain.entities.knowledge_article import KnowledgeArticle, ArticleStatus
from domain.entities.csat import CSATSurvey
from domain.entities.custom_field import CustomFieldDefinition, CustomFieldValue, FieldType
from domain.entities.pipeline import Pipeline, PipelineStage
from domain.entities.event import Event, EventStatus, EventType
from domain.entities.health_score import AccountHealthScore, HealthGrade
from domain.entities.relationship import Relationship, RelationshipType
from domain.entities.attachment import Attachment

__all__ = [
    "Account",
    "Contact",
    "Opportunity", "OpportunityStage", "OpportunitySource",
    "Lead", "LeadStatus", "LeadRating",
    "Case", "CaseStatus", "CasePriority", "CaseOrigin",
    "Activity", "ActivityType", "ActivityStatus",
    "Campaign", "CampaignStatus", "CampaignType",
    "Product", "PriceBookEntry",
    "Quote", "QuoteStatus", "QuoteLineItem",
    "KnowledgeArticle", "ArticleStatus",
    "CSATSurvey",
    "CustomFieldDefinition", "CustomFieldValue", "FieldType",
    "Pipeline", "PipelineStage",
    "Event", "EventStatus", "EventType",
    "AccountHealthScore", "HealthGrade",
    "Relationship", "RelationshipType",
    "Attachment",
]
