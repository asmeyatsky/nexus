"""
Contact Commands

Architectural Intent:
- Application layer commands for contact operations
- Orchestrate domain entities through repository ports
"""

from dataclasses import dataclass
from uuid import UUID

from domain import Contact, Email, PhoneNumber
from domain.ports.repository_ports import ContactRepositoryPort, AccountRepositoryPort
from domain.ports import EventBusPort, AuditLogPort
from application.dtos import ContactDTO, CreateContactDTO


@dataclass
class CreateContactCommand:
    repository: ContactRepositoryPort
    account_repository: AccountRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, dto: CreateContactDTO) -> ContactDTO:
        account = await self.account_repository.get_by_id(UUID(dto.account_id))
        if not account:
            raise ValueError(f"Account {dto.account_id} not found")

        contact = Contact.create(
            account_id=UUID(dto.account_id),
            first_name=dto.first_name,
            last_name=dto.last_name,
            email=Email.create(dto.email),
            owner_id=UUID(dto.owner_id),
            phone=PhoneNumber.create(dto.phone) if dto.phone else None,
            title=dto.title,
            department=dto.department,
        )

        saved_contact = await self.repository.save(contact)

        await self.event_bus.publish(list(saved_contact.domain_events))

        await self.audit_log.log(
            user_id=dto.owner_id,
            action="CREATE",
            resource_type="Contact",
            resource_id=str(saved_contact.id),
            details={"name": saved_contact.full_name},
        )

        return ContactDTO.from_entity(saved_contact)


@dataclass
class UpdateContactCommand:
    repository: ContactRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        contact_id: str,
        dto: CreateContactDTO,
        user_id: str,
    ) -> ContactDTO:
        contact = await self.repository.get_by_id(UUID(contact_id))
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")

        updated = contact.update(
            first_name=dto.first_name,
            last_name=dto.last_name,
            email=Email.create(dto.email),
            phone=PhoneNumber.create(dto.phone) if dto.phone else None,
            title=dto.title,
            department=dto.department,
        )

        saved_contact = await self.repository.save(updated)

        await self.event_bus.publish(list(saved_contact.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="UPDATE",
            resource_type="Contact",
            resource_id=str(saved_contact.id),
        )

        return ContactDTO.from_entity(saved_contact)
