"""
Database Configuration - SECURED

Architectural Intent:
- SQLAlchemy database setup for PostgreSQL on GCP
- Uses Cloud SQL with proper connection pooling
- Secrets loaded from environment variables
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    Numeric,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base


DATABASE_URL = os.environ.get("DATABASE_URL", "")

_engine = None
_async_session = None


def _get_engine():
    global _engine
    if _engine is None and DATABASE_URL:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def async_session():
    global _async_session
    if _async_session is None:
        eng = _get_engine()
        if eng is None:
            raise RuntimeError("DATABASE_URL is not configured")
        _async_session = async_sessionmaker(
            eng,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session

Base = declarative_base()


class AccountModel(Base):
    __tablename__ = "accounts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False)
    territory = Column(String(100), nullable=False)
    website = Column(String(255))
    phone = Column(String(50))
    billing_address = Column(Text)
    annual_revenue = Column(Numeric(15, 2))
    currency = Column(String(3), default="USD")
    employee_count = Column(Integer)
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    parent_account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContactModel(Base):
    __tablename__ = "contacts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    title = Column(String(100))
    department = Column(String(100))
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OpportunityModel(Base):
    __tablename__ = "opportunities"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    name = Column(String(255), nullable=False)
    stage = Column(String(50), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    probability = Column(Integer, default=10)
    close_date = Column(DateTime, nullable=False)
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    contact_id = Column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    source = Column(String(50))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadModel(Base):
    __tablename__ = "leads"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    status = Column(String(50), default="new")
    rating = Column(String(50), default="cold")
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    source = Column(String(50))
    phone = Column(String(50))
    title = Column(String(100))
    website = Column(String(255))
    converted_account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"))
    converted_contact_id = Column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    converted_opportunity_id = Column(
        PGUUID(as_uuid=True), ForeignKey("opportunities.id")
    )
    converted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CaseModel(Base):
    __tablename__ = "cases"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    case_number = Column(String(50), unique=True, nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    contact_id = Column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    status = Column(String(50), default="new")
    priority = Column(String(50), default="medium")
    origin = Column(String(50), default="web")
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    resolution_notes = Column(Text)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    password_history = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityModel(Base):
    __tablename__ = "activities"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="open")
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    related_entity_type = Column(String(50))
    related_entity_id = Column(PGUUID(as_uuid=True))
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CampaignModel(Base):
    __tablename__ = "campaigns"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), default="draft")
    budget = Column(Numeric(15, 2))
    actual_cost = Column(Numeric(15, 2))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductModel(Base):
    __tablename__ = "products"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50))
    family = Column(String(100))
    description = Column(Text)
    unit_price = Column(Numeric(15, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PriceBookEntryModel(Base):
    __tablename__ = "price_book_entries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    price_book_id = Column(PGUUID(as_uuid=True), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuoteModel(Base):
    __tablename__ = "quotes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    opportunity_id = Column(PGUUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")
    currency = Column(String(3), default="USD")
    total_amount = Column(Numeric(15, 2))
    discount_percent = Column(Numeric(5, 2))
    owner_id = Column(PGUUID(as_uuid=True), nullable=False)
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuoteLineItemModel(Base):
    __tablename__ = "quote_line_items"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    quote_id = Column(PGUUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(15, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0)
    total_price = Column(Numeric(15, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeArticleModel(Base):
    __tablename__ = "knowledge_articles"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(100))
    status = Column(String(50), default="draft")
    author_id = Column(PGUUID(as_uuid=True), nullable=False)
    tags = Column(JSON, default=list)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CSATSurveyModel(Base):
    __tablename__ = "csat_surveys"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    case_id = Column(PGUUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    contact_id = Column(PGUUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    score = Column(Integer)
    comment = Column(Text)
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomFieldDefinitionModel(Base):
    __tablename__ = "custom_field_definitions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=False)
    default_value = Column(Text)
    options = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomFieldValueModel(Base):
    __tablename__ = "custom_field_values"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    field_definition_id = Column(PGUUID(as_uuid=True), ForeignKey("custom_field_definitions.id"), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PipelineModel(Base):
    __tablename__ = "pipelines"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    stages = Column(JSON, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EventModel(Base):
    __tablename__ = "events"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), default="planned")
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    campaign_id = Column(PGUUID(as_uuid=True), ForeignKey("campaigns.id"))
    location = Column(String(255))
    max_attendees = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HealthScoreModel(Base):
    __tablename__ = "health_scores"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    overall_score = Column(Integer, nullable=False)
    grade = Column(String(2), nullable=False)
    engagement_score = Column(Integer)
    adoption_score = Column(Integer)
    support_score = Column(Integer)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RelationshipModel(Base):
    __tablename__ = "relationships"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    from_entity_type = Column(String(50), nullable=False)
    from_entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    to_entity_type = Column(String(50), nullable=False)
    to_entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    type = Column(String(50), nullable=False)
    strength = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttachmentModel(Base):
    __tablename__ = "attachments"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100))
    size = Column(Integer)
    storage_path = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    uploaded_by = Column(PGUUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def init_db():
    engine = _get_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_session()
    async with session_factory() as session:
        yield session
