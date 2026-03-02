"""
Case Repository Implementation

Implements CaseRepositoryPort with SQLAlchemy.
"""

from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Case, CaseStatus, CasePriority, CaseOrigin
from infrastructure.database import CaseModel


def _get_column_value(model: Any, attr: str, default: Any = None) -> Any:
    value = getattr(model, attr, default)
    return value if value is not None else default


class CaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, case: Case) -> Case:
        model = CaseModel(
            id=case.id,
            case_number=case.case_number,
            subject=case.subject,
            description=case.description,
            account_id=case.account_id,
            contact_id=case.contact_id,
            status=case.status.value,
            priority=case.priority.value,
            origin=case.origin.value,
            owner_id=case.owner_id,
            resolution_notes=case.resolution_notes,
            resolved_by=case.resolved_by,
            resolved_at=case.resolved_at,
            closed_at=case.closed_at,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
        merged = await self.session.merge(model)
        await self.session.commit()
        await self.session.refresh(merged)
        return case

    async def get_by_id(self, case_id: UUID) -> Optional[Case]:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.id == case_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_case_number(self, case_number: str) -> Optional[Case]:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.case_number == case_number)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_account(self, account_id: UUID) -> List[Case]:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.account_id == account_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Case]:
        result = await self.session.execute(
            select(CaseModel)
            .order_by(CaseModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_status(self, status: str) -> List[Case]:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.status == status)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_owner(self, owner_id: UUID) -> List[Case]:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.owner_id == owner_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_open_cases(self) -> List[Case]:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.status.notin_(["resolved", "closed"]))
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, case_id: UUID) -> None:
        result = await self.session.execute(
            select(CaseModel).where(CaseModel.id == case_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()

    def _to_entity(self, model: CaseModel) -> Case:
        return Case(
            id=_get_column_value(model, "id"),
            case_number=str(_get_column_value(model, "case_number")),
            subject=str(_get_column_value(model, "subject")),
            description=str(_get_column_value(model, "description")),
            account_id=_get_column_value(model, "account_id"),
            contact_id=_get_column_value(model, "contact_id"),
            status=CaseStatus(str(_get_column_value(model, "status", "new"))),
            priority=CasePriority(str(_get_column_value(model, "priority", "medium"))),
            origin=CaseOrigin(str(_get_column_value(model, "origin", "web"))),
            owner_id=_get_column_value(model, "owner_id"),
            resolution_notes=str(_get_column_value(model, "resolution_notes"))
            if _get_column_value(model, "resolution_notes")
            else None,
            resolved_by=str(_get_column_value(model, "resolved_by"))
            if _get_column_value(model, "resolved_by")
            else None,
            resolved_at=_get_column_value(model, "resolved_at"),
            created_at=_get_column_value(model, "created_at"),
            updated_at=_get_column_value(model, "updated_at"),
            closed_at=_get_column_value(model, "closed_at"),
        )
