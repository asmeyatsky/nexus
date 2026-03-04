"""
Opportunity Repository Implementation

Implements OpportunityRepositoryPort with SQLAlchemy.
Enforces tenant isolation via org_id filtering.
"""

from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Opportunity, OpportunityStage, OpportunitySource, Money
from infrastructure.database import OpportunityModel


def _get_column_value(model: Any, attr: str, default: Any = None) -> Any:
    """Extract value from SQLAlchemy model column at runtime."""
    value = getattr(model, attr, default)
    return value if value is not None else default


class OpportunityRepository:
    def __init__(self, session: AsyncSession, org_id: str):
        self.session = session
        self.org_id = org_id

    async def save(self, opportunity: Opportunity) -> Opportunity:
        model = OpportunityModel(
            id=opportunity.id,
            org_id=self.org_id,
            account_id=opportunity.account_id,
            name=opportunity.name,
            stage=opportunity.stage.value,
            amount=opportunity.amount.amount_float,
            currency=opportunity.amount.currency,
            probability=opportunity.probability,
            close_date=opportunity.close_date,
            owner_id=opportunity.owner_id,
            contact_id=opportunity.contact_id,
            source=opportunity.source.value if opportunity.source else None,
            description=opportunity.description,
            is_active=opportunity.is_active,
            closed_at=opportunity.closed_at,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )
        try:
            merged = await self.session.merge(model)
            await self.session.commit()
            await self.session.refresh(merged)
        except Exception:
            await self.session.rollback()
            raise
        return opportunity

    async def get_by_id(self, opportunity_id: UUID) -> Optional[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.id == opportunity_id,
                OpportunityModel.org_id == self.org_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_account(self, account_id: UUID) -> List[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.account_id == account_id,
                OpportunityModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel)
            .where(OpportunityModel.org_id == self.org_id)
            .order_by(OpportunityModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_owner(self, owner_id: UUID) -> List[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.owner_id == owner_id,
                OpportunityModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_stage(self, stage: str) -> List[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.stage == stage,
                OpportunityModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_open_opportunities(self) -> List[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.stage.notin_(["closed_won", "closed_lost"]),
                OpportunityModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_close_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Opportunity]:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.close_date.between(start_date, end_date),
                OpportunityModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, opportunity_id: UUID) -> None:
        result = await self.session.execute(
            select(OpportunityModel).where(
                OpportunityModel.id == opportunity_id,
                OpportunityModel.org_id == self.org_id,
            )
        )
        model = result.scalar_one_or_none()
        if model:
            try:
                await self.session.delete(model)
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

    def _to_entity(self, model: OpportunityModel) -> Opportunity:
        amount = Money.from_float(
            float(_get_column_value(model, "amount", 0)),
            str(_get_column_value(model, "currency", "USD")),
        )
        source_val = _get_column_value(model, "source")
        source = None
        if source_val:
            try:
                source = OpportunitySource(source_val)
            except ValueError:
                pass

        return Opportunity(
            id=_get_column_value(model, "id"),
            account_id=_get_column_value(model, "account_id"),
            name=str(_get_column_value(model, "name")),
            stage=OpportunityStage(str(_get_column_value(model, "stage"))),
            amount=amount,
            probability=int(_get_column_value(model, "probability", 10)),
            close_date=_get_column_value(model, "close_date"),
            owner_id=_get_column_value(model, "owner_id"),
            contact_id=_get_column_value(model, "contact_id"),
            source=source,
            description=str(_get_column_value(model, "description"))
            if _get_column_value(model, "description")
            else None,
            is_active=bool(_get_column_value(model, "is_active", True)),
            closed_at=_get_column_value(model, "closed_at"),
            created_at=_get_column_value(model, "created_at"),
            updated_at=_get_column_value(model, "updated_at"),
        )
