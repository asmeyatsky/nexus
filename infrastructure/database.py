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
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncGenerator,
)
from sqlalchemy.orm import declarative_base


DATABASE_URL = os.environ.get("DATABASE_URL", "")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

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


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
