"""
Lead Commands

Architectural Intent:
- Application layer commands for lead (marketing) operations
- Orchestrate domain entities through repository ports
"""

from dataclasses import dataclass
from uuid import UUID

from domain import Lead, LeadStatus, Email, PhoneNumber
from domain.ports.repository_ports import (
    LeadRepositoryPort,
    AccountRepositoryPort,
    ContactRepositoryPort,
    OpportunityRepositoryPort,
)
from domain.ports import EventBusPort, AuditLogPort
from application.dtos import LeadDTO, CreateLeadDTO


@dataclass
class CreateLeadCommand:
    repository: LeadRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, dto: CreateLeadDTO) -> LeadDTO:
        lead = Lead.create(
            first_name=dto.first_name,
            last_name=dto.last_name,
            email=Email.create(dto.email),
            company=dto.company,
            owner_id=UUID(dto.owner_id),
            source=dto.source,
            phone=PhoneNumber.create(dto.phone) if dto.phone else None,
            title=dto.title,
            website=dto.website,
        )

        saved_lead = await self.repository.save(lead)

        await self.event_bus.publish(list(saved_lead.domain_events))

        await self.audit_log.log(
            user_id=dto.owner_id,
            action="CREATE",
            resource_type="Lead",
            resource_id=str(saved_lead.id),
            details={"name": saved_lead.full_name, "company": dto.company},
        )

        return LeadDTO.from_entity(saved_lead)


@dataclass
class QualifyLeadCommand:
    repository: LeadRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, lead_id: str, user_id: str) -> LeadDTO:
        lead = await self.repository.get_by_id(UUID(lead_id))
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        qualified = lead.change_status(LeadStatus.QUALIFIED)

        saved_lead = await self.repository.save(qualified)

        await self.event_bus.publish(list(saved_lead.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="QUALIFY",
            resource_type="Lead",
            resource_id=str(saved_lead.id),
        )

        return LeadDTO.from_entity(saved_lead)


@dataclass
class ConvertLeadCommand:
    lead_repository: LeadRepositoryPort
    account_repository: AccountRepositoryPort
    contact_repository: ContactRepositoryPort
    opportunity_repository: OpportunityRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        lead_id: str,
        account_id: str,
        contact_id: str,
        opportunity_id: str,
        user_id: str,
    ) -> dict:
        lead = await self.lead_repository.get_by_id(UUID(lead_id))
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        converted = lead.convert(
            account_id=UUID(account_id),
            contact_id=UUID(contact_id),
            opportunity_id=UUID(opportunity_id) if opportunity_id else None,
        )

        saved_lead = await self.lead_repository.save(converted)

        await self.event_bus.publish(list(saved_lead.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="CONVERT",
            resource_type="Lead",
            resource_id=str(saved_lead.id),
            details={"account_id": account_id, "contact_id": contact_id},
        )

        return {
            "lead": LeadDTO.from_entity(saved_lead),
            "account_id": account_id,
            "contact_id": contact_id,
        }
