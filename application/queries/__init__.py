"""
Application Queries

Architectural Intent:
- Query handlers for read operations
- Return DTOs for presentation layer
- No business logic, just data retrieval
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from domain.ports.repository_ports import (
    AccountRepositoryPort,
    ContactRepositoryPort,
    OpportunityRepositoryPort,
    LeadRepositoryPort,
    CaseRepositoryPort,
)
from application.dtos import (
    AccountDTO,
    ContactDTO,
    OpportunityDTO,
    LeadDTO,
    CaseDTO,
)


@dataclass
class GetAccountQuery:
    repository: AccountRepositoryPort

    async def execute(self, account_id: str) -> Optional[AccountDTO]:
        account = await self.repository.get_by_id(UUID(account_id))
        if not account:
            return None
        return AccountDTO.from_entity(account)


@dataclass
class ListAccountsQuery:
    repository: AccountRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[AccountDTO]:
        accounts = await self.repository.get_all(limit, offset)
        return [AccountDTO.from_entity(a) for a in accounts]


@dataclass
class GetAccountsByOwnerQuery:
    repository: AccountRepositoryPort

    async def execute(self, owner_id: str) -> List[AccountDTO]:
        accounts = await self.repository.get_by_owner(UUID(owner_id))
        return [AccountDTO.from_entity(a) for a in accounts]


@dataclass
class GetContactQuery:
    repository: ContactRepositoryPort

    async def execute(self, contact_id: str) -> Optional[ContactDTO]:
        contact = await self.repository.get_by_id(UUID(contact_id))
        if not contact:
            return None
        return ContactDTO.from_entity(contact)


@dataclass
class ListContactsQuery:
    repository: ContactRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[ContactDTO]:
        contacts = await self.repository.get_all(limit, offset)
        return [ContactDTO.from_entity(c) for c in contacts]


@dataclass
class GetContactsByAccountQuery:
    repository: ContactRepositoryPort

    async def execute(self, account_id: str) -> List[ContactDTO]:
        contacts = await self.repository.get_by_account(UUID(account_id))
        return [ContactDTO.from_entity(c) for c in contacts]


@dataclass
class GetOpportunityQuery:
    repository: OpportunityRepositoryPort

    async def execute(self, opportunity_id: str) -> Optional[OpportunityDTO]:
        opportunity = await self.repository.get_by_id(UUID(opportunity_id))
        if not opportunity:
            return None
        return OpportunityDTO.from_entity(opportunity)


@dataclass
class ListOpportunitiesQuery:
    repository: OpportunityRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[OpportunityDTO]:
        opportunities = await self.repository.get_all(limit, offset)
        return [OpportunityDTO.from_entity(o) for o in opportunities]


@dataclass
class GetOpportunitiesByAccountQuery:
    repository: OpportunityRepositoryPort

    async def execute(self, account_id: str) -> List[OpportunityDTO]:
        opportunities = await self.repository.get_by_account(UUID(account_id))
        return [OpportunityDTO.from_entity(o) for o in opportunities]


@dataclass
class GetOpenOpportunitiesQuery:
    repository: OpportunityRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[OpportunityDTO]:
        opportunities = await self.repository.get_open_opportunities()
        return [
            OpportunityDTO.from_entity(o)
            for o in opportunities[offset : offset + limit]
        ]


@dataclass
class GetLeadQuery:
    repository: LeadRepositoryPort

    async def execute(self, lead_id: str) -> Optional[LeadDTO]:
        lead = await self.repository.get_by_id(UUID(lead_id))
        if not lead:
            return None
        return LeadDTO.from_entity(lead)


@dataclass
class ListLeadsQuery:
    repository: LeadRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[LeadDTO]:
        leads = await self.repository.get_all(limit, offset)
        return [LeadDTO.from_entity(lead) for lead in leads]


@dataclass
class GetCaseQuery:
    repository: CaseRepositoryPort

    async def execute(self, case_id: str) -> Optional[CaseDTO]:
        case = await self.repository.get_by_id(UUID(case_id))
        if not case:
            return None
        return CaseDTO.from_entity(case)


@dataclass
class GetCaseByNumberQuery:
    repository: CaseRepositoryPort

    async def execute(self, case_number: str) -> Optional[CaseDTO]:
        case = await self.repository.get_by_case_number(case_number)
        if not case:
            return None
        return CaseDTO.from_entity(case)


@dataclass
class ListCasesQuery:
    repository: CaseRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[CaseDTO]:
        cases = await self.repository.get_all(limit, offset)
        return [CaseDTO.from_entity(c) for c in cases]


@dataclass
class GetOpenCasesQuery:
    repository: CaseRepositoryPort

    async def execute(self, limit: int = 100, offset: int = 0) -> List[CaseDTO]:
        cases = await self.repository.get_open_cases()
        return [CaseDTO.from_entity(c) for c in cases[offset : offset + limit]]


@dataclass
class SearchAccountsQuery:
    repository: AccountRepositoryPort

    async def execute(self, search=None, industry=None, territory=None,
                      owner_id=None, is_active=None, sort_by="created_at",
                      sort_order="desc", limit=100, offset=0) -> Tuple[List[AccountDTO], int]:
        items, total = await self.repository.search(
            search=search, industry=industry, territory=territory,
            owner_id=owner_id, is_active=is_active, sort_by=sort_by,
            sort_order=sort_order, limit=limit, offset=offset)
        return [AccountDTO.from_entity(a) for a in items], total


@dataclass
class SearchContactsQuery:
    repository: ContactRepositoryPort

    async def execute(self, search=None, account_id=None, owner_id=None,
                      is_active=None, sort_by="created_at", sort_order="desc",
                      limit=100, offset=0) -> Tuple[List[ContactDTO], int]:
        items, total = await self.repository.search(
            search=search, account_id=account_id, owner_id=owner_id,
            is_active=is_active, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset)
        return [ContactDTO.from_entity(c) for c in items], total


@dataclass
class SearchOpportunitiesQuery:
    repository: OpportunityRepositoryPort

    async def execute(self, search=None, stage=None, owner_id=None,
                      account_id=None, is_closed=None, close_date_start=None,
                      close_date_end=None, sort_by="created_at", sort_order="desc",
                      limit=100, offset=0) -> Tuple[List[OpportunityDTO], int]:
        items, total = await self.repository.search(
            search=search, stage=stage, owner_id=owner_id,
            account_id=account_id, is_closed=is_closed,
            close_date_start=close_date_start, close_date_end=close_date_end,
            sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset)
        return [OpportunityDTO.from_entity(o) for o in items], total


@dataclass
class SearchLeadsQuery:
    repository: LeadRepositoryPort

    async def execute(self, search=None, status=None, rating=None, owner_id=None,
                      source=None, sort_by="created_at", sort_order="desc",
                      limit=100, offset=0) -> Tuple[List[LeadDTO], int]:
        items, total = await self.repository.search(
            search=search, status=status, rating=rating, owner_id=owner_id,
            source=source, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset)
        return [LeadDTO.from_entity(l) for l in items], total


@dataclass
class SearchCasesQuery:
    repository: CaseRepositoryPort

    async def execute(self, search=None, status=None, priority=None, origin=None,
                      owner_id=None, account_id=None, sort_by="created_at",
                      sort_order="desc", limit=100, offset=0) -> Tuple[List[CaseDTO], int]:
        items, total = await self.repository.search(
            search=search, status=status, priority=priority, origin=origin,
            owner_id=owner_id, account_id=account_id, sort_by=sort_by,
            sort_order=sort_order, limit=limit, offset=offset)
        return [CaseDTO.from_entity(c) for c in items], total
