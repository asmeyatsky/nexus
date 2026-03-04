"""
Lead Repository Implementation

Implements LeadRepositoryPort with SQLAlchemy.
Enforces tenant isolation via org_id filtering.
"""

from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Lead, LeadStatus, LeadRating, Email, PhoneNumber
from infrastructure.database import LeadModel


def _get_column_value(model: Any, attr: str, default: Any = None) -> Any:
    """Extract value from SQLAlchemy model column at runtime."""
    value = getattr(model, attr, default)
    return value if value is not None else default


class LeadRepository:
    def __init__(self, session: AsyncSession, org_id: str):
        self.session = session
        self.org_id = org_id

    async def save(self, lead: Lead) -> Lead:
        model = LeadModel(
            id=lead.id,
            org_id=self.org_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=str(lead.email),
            company=lead.company,
            status=lead.status.value,
            rating=lead.rating.value,
            owner_id=lead.owner_id,
            source=lead.source,
            phone=str(lead.phone) if lead.phone else None,
            title=lead.title,
            website=lead.website,
            converted_account_id=lead.converted_account_id,
            converted_contact_id=lead.converted_contact_id,
            converted_opportunity_id=lead.converted_opportunity_id,
            converted_at=lead.converted_at,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )
        try:
            merged = await self.session.merge(model)
            await self.session.commit()
            await self.session.refresh(merged)
        except Exception:
            await self.session.rollback()
            raise
        return lead

    async def get_by_id(self, lead_id: UUID) -> Optional[Lead]:
        result = await self.session.execute(
            select(LeadModel).where(
                LeadModel.id == lead_id,
                LeadModel.org_id == self.org_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_email(self, email: str) -> Optional[Lead]:
        result = await self.session.execute(
            select(LeadModel).where(
                LeadModel.email == email,
                LeadModel.org_id == self.org_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Lead]:
        result = await self.session.execute(
            select(LeadModel)
            .where(LeadModel.org_id == self.org_id)
            .order_by(LeadModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_status(self, status: str) -> List[Lead]:
        result = await self.session.execute(
            select(LeadModel).where(
                LeadModel.status == status,
                LeadModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_owner(self, owner_id: UUID) -> List[Lead]:
        result = await self.session.execute(
            select(LeadModel).where(
                LeadModel.owner_id == owner_id,
                LeadModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_unqualified_leads(self) -> List[Lead]:
        result = await self.session.execute(
            select(LeadModel).where(
                LeadModel.status.notin_(["converted", "unqualified"]),
                LeadModel.org_id == self.org_id,
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, lead_id: UUID) -> None:
        result = await self.session.execute(
            select(LeadModel).where(
                LeadModel.id == lead_id,
                LeadModel.org_id == self.org_id,
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

    def _to_entity(self, model: LeadModel) -> Lead:
        phone_val = _get_column_value(model, "phone")
        return Lead(
            id=_get_column_value(model, "id"),
            first_name=str(_get_column_value(model, "first_name")),
            last_name=str(_get_column_value(model, "last_name")),
            email=Email.create(str(_get_column_value(model, "email"))),
            company=str(_get_column_value(model, "company")),
            status=LeadStatus(str(_get_column_value(model, "status", "new"))),
            rating=LeadRating(str(_get_column_value(model, "rating", "cold"))),
            owner_id=_get_column_value(model, "owner_id"),
            source=str(_get_column_value(model, "source"))
            if _get_column_value(model, "source")
            else None,
            phone=PhoneNumber.create(str(phone_val)) if phone_val else None,
            title=str(_get_column_value(model, "title"))
            if _get_column_value(model, "title")
            else None,
            website=str(_get_column_value(model, "website"))
            if _get_column_value(model, "website")
            else None,
            converted_account_id=_get_column_value(model, "converted_account_id"),
            converted_contact_id=_get_column_value(model, "converted_contact_id"),
            converted_opportunity_id=_get_column_value(
                model, "converted_opportunity_id"
            ),
            converted_at=_get_column_value(model, "converted_at"),
            created_at=_get_column_value(model, "created_at"),
            updated_at=_get_column_value(model, "updated_at"),
        )
