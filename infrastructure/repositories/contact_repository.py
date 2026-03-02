"""
Contact Repository Implementation

Architectural Intent:
- Implements ContactRepositoryPort
- Adapter for PostgreSQL via SQLAlchemy
"""

from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import Contact, Email, PhoneNumber
from infrastructure.database import ContactModel


def _get_column_value(model: Any, attr: str, default: Any = None) -> Any:
    """Extract value from SQLAlchemy model column at runtime."""
    value = getattr(model, attr, default)
    return value if value is not None else default


class ContactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, contact: Contact) -> Contact:
        model = ContactModel(
            id=contact.id,
            account_id=contact.account_id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=str(contact.email),
            phone=str(contact.phone) if contact.phone else None,
            title=contact.title,
            department=contact.department,
            owner_id=contact.owner_id,
            is_active=contact.is_active,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return contact

    async def get_by_id(self, contact_id: UUID) -> Optional[Contact]:
        result = await self.session.execute(
            select(ContactModel).where(ContactModel.id == contact_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_email(self, email: str) -> Optional[Contact]:
        result = await self.session.execute(
            select(ContactModel).where(ContactModel.email == email)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    async def get_by_account(self, account_id: UUID) -> List[Contact]:
        result = await self.session.execute(
            select(ContactModel).where(ContactModel.account_id == account_id)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Contact]:
        result = await self.session.execute(
            select(ContactModel)
            .order_by(ContactModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_owner(self, owner_id: UUID) -> List[Contact]:
        result = await self.session.execute(
            select(ContactModel).where(ContactModel.owner_id == owner_id)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def delete(self, contact_id: UUID) -> None:
        result = await self.session.execute(
            select(ContactModel).where(ContactModel.id == contact_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()

    def _to_entity(self, model: ContactModel) -> Contact:
        phone_val = _get_column_value(model, "phone")
        return Contact(
            id=_get_column_value(model, "id"),
            account_id=_get_column_value(model, "account_id"),
            first_name=str(_get_column_value(model, "first_name")),
            last_name=str(_get_column_value(model, "last_name")),
            email=Email.create(str(_get_column_value(model, "email"))),
            phone=PhoneNumber.create(str(phone_val)) if phone_val else None,
            title=str(_get_column_value(model, "title"))
            if _get_column_value(model, "title")
            else None,
            department=str(_get_column_value(model, "department"))
            if _get_column_value(model, "department")
            else None,
            owner_id=_get_column_value(model, "owner_id"),
            is_active=bool(_get_column_value(model, "is_active", True)),
            created_at=_get_column_value(model, "created_at"),
            updated_at=_get_column_value(model, "updated_at"),
        )
