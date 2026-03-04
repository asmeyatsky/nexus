"""
Account Repository Implementation

Architectural Intent:
- Implements AccountRepositoryPort
- Adapter for PostgreSQL via SQLAlchemy
- Converts between domain entities and database models
- Enforces tenant isolation via org_id filtering
"""

from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Account, Industry, Territory, Money
from infrastructure.database import AccountModel


def _get_column_value(model: Any, attr: str, default: Any = None) -> Any:
    """Extract value from SQLAlchemy model column at runtime."""
    value = getattr(model, attr, default)
    return value if value is not None else default


class AccountRepository:
    def __init__(self, session: AsyncSession, org_id: str):
        self.session = session
        self.org_id = org_id

    async def save(self, account: Account) -> Account:
        model = AccountModel(
            id=account.id,
            org_id=self.org_id,
            name=account.name,
            industry=account.industry.type.value,
            territory=account.territory.region,
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
            owner_id=account.owner_id,
            parent_account_id=account.parent_account_id,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

        try:
            merged = await self.session.merge(model)
            await self.session.commit()
            await self.session.refresh(merged)
        except Exception:
            await self.session.rollback()
            raise
        return account

    async def get_by_id(self, account_id: UUID) -> Optional[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.id == account_id,
                AccountModel.org_id == self.org_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_name(self, name: str) -> Optional[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.name == name,
                AccountModel.org_id == self.org_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Account]:
        result = await self.session.execute(
            select(AccountModel)
            .where(AccountModel.org_id == self.org_id)
            .order_by(AccountModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_owner(self, owner_id: UUID) -> List[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.owner_id == owner_id,
                AccountModel.org_id == self.org_id,
            )
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_industry(self, industry: str) -> List[Account]:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.industry == industry,
                AccountModel.org_id == self.org_id,
            )
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def delete(self, account_id: UUID) -> None:
        result = await self.session.execute(
            select(AccountModel).where(
                AccountModel.id == account_id,
                AccountModel.org_id == self.org_id,
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

    def _to_entity(self, model: AccountModel) -> Account:
        annual_revenue = None
        revenue = _get_column_value(model, "annual_revenue")
        currency = _get_column_value(model, "currency", "USD")
        if revenue is not None:
            annual_revenue = Money.from_float(float(revenue), str(currency))

        return Account(
            id=_get_column_value(model, "id"),
            name=str(_get_column_value(model, "name")),
            industry=Industry.from_string(str(_get_column_value(model, "industry"))),
            territory=Territory(region=str(_get_column_value(model, "territory"))),
            website=str(_get_column_value(model, "website"))
            if _get_column_value(model, "website")
            else None,
            phone=str(_get_column_value(model, "phone"))
            if _get_column_value(model, "phone")
            else None,
            billing_address=str(_get_column_value(model, "billing_address"))
            if _get_column_value(model, "billing_address")
            else None,
            annual_revenue=annual_revenue,
            employee_count=int(_get_column_value(model, "employee_count"))
            if _get_column_value(model, "employee_count")
            else None,
            owner_id=_get_column_value(model, "owner_id"),
            parent_account_id=_get_column_value(model, "parent_account_id"),
            is_active=bool(_get_column_value(model, "is_active", True)),
            created_at=_get_column_value(model, "created_at"),
            updated_at=_get_column_value(model, "updated_at"),
        )
