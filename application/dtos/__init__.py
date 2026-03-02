"""
Application DTOs

Architectural Intent:
- Data Transfer Objects for application layer
- Used for API requests and responses
- Separates domain entities from presentation layer
"""

import domain
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AccountDTO:
    id: str
    name: str
    industry: str
    territory: str
    website: Optional[str]
    phone: Optional[str]
    billing_address: Optional[str]
    annual_revenue: Optional[float]
    currency: Optional[str]
    employee_count: Optional[int]
    owner_id: str
    parent_account_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(
        account: "domain.Account",
    ) -> "AccountDTO":
        return AccountDTO(
            id=str(account.id),
            name=account.name,
            industry=account.industry.display_name,
            territory=account.territory.display_name,
            website=account.website,
            phone=account.phone,
            billing_address=account.billing_address,
            annual_revenue=account.annual_revenue.amount_float
            if account.annual_revenue
            else None,
            currency=account.annual_revenue.currency
            if account.annual_revenue
            else None,
            employee_count=account.employee_count,
            owner_id=str(account.owner_id),
            parent_account_id=str(account.parent_account_id)
            if account.parent_account_id
            else None,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


@dataclass
class CreateAccountDTO:
    name: str
    industry: str
    territory: str
    owner_id: str
    website: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    annual_revenue: Optional[float] = None
    currency: str = "USD"
    employee_count: Optional[int] = None


@dataclass
class ContactDTO:
    id: str
    account_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    title: Optional[str]
    department: Optional[str]
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(contact: "domain.Contact") -> "ContactDTO":
        return ContactDTO(
            id=str(contact.id),
            account_id=str(contact.account_id),
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=str(contact.email),
            phone=str(contact.phone) if contact.phone else None,
            title=contact.title,
            department=contact.department,
            owner_id=str(contact.owner_id),
            is_active=contact.is_active,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )


@dataclass
class CreateContactDTO:
    account_id: str
    first_name: str
    last_name: str
    email: str
    owner_id: str
    phone: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None


@dataclass
class OpportunityDTO:
    id: str
    account_id: str
    name: str
    stage: str
    amount: float
    currency: str
    probability: int
    close_date: datetime
    owner_id: str
    contact_id: Optional[str]
    source: Optional[str]
    description: Optional[str]
    is_active: bool
    is_won: bool
    is_lost: bool
    is_closed: bool
    weighted_value: float
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(opportunity: "domain.Opportunity") -> "OpportunityDTO":
        return OpportunityDTO(
            id=str(opportunity.id),
            account_id=str(opportunity.account_id),
            name=opportunity.name,
            stage=opportunity.stage.value,
            amount=opportunity.amount.amount_float,
            currency=opportunity.amount.currency,
            probability=opportunity.probability,
            close_date=opportunity.close_date,
            owner_id=str(opportunity.owner_id),
            contact_id=str(opportunity.contact_id) if opportunity.contact_id else None,
            source=opportunity.source.value if opportunity.source else None,
            description=opportunity.description,
            is_active=opportunity.is_active,
            is_won=opportunity.is_won,
            is_lost=opportunity.is_lost,
            is_closed=opportunity.is_closed,
            weighted_value=opportunity.weighted_value.amount_float,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )


@dataclass
class CreateOpportunityDTO:
    account_id: str
    name: str
    amount: float
    currency: str
    close_date: datetime
    owner_id: str
    source: Optional[str] = None
    contact_id: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LeadDTO:
    id: str
    first_name: str
    last_name: str
    email: str
    company: str
    status: str
    rating: str
    owner_id: str
    source: Optional[str]
    phone: Optional[str]
    title: Optional[str]
    website: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(lead: "domain.Lead") -> "LeadDTO":
        return LeadDTO(
            id=str(lead.id),
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=str(lead.email),
            company=lead.company,
            status=lead.status.value,
            rating=lead.rating.value,
            owner_id=str(lead.owner_id),
            source=lead.source,
            phone=str(lead.phone) if lead.phone else None,
            title=lead.title,
            website=lead.website,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )


@dataclass
class CreateLeadDTO:
    first_name: str
    last_name: str
    email: str
    company: str
    owner_id: str
    source: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None


@dataclass
class CaseDTO:
    id: str
    case_number: str
    subject: str
    description: str
    account_id: str
    contact_id: Optional[str]
    status: str
    priority: str
    origin: str
    owner_id: str
    resolution_notes: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(case: "domain.Case") -> "CaseDTO":
        return CaseDTO(
            id=str(case.id),
            case_number=case.case_number,
            subject=case.subject,
            description=case.description,
            account_id=str(case.account_id),
            contact_id=str(case.contact_id) if case.contact_id else None,
            status=case.status.value,
            priority=case.priority.value,
            origin=case.origin.value,
            owner_id=str(case.owner_id),
            resolution_notes=case.resolution_notes,
            resolved_by=case.resolved_by,
            resolved_at=case.resolved_at,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )


@dataclass
class CreateCaseDTO:
    subject: str
    description: str
    account_id: str
    owner_id: str
    case_number: str
    contact_id: Optional[str] = None
    priority: str = "medium"
    origin: str = "web"
