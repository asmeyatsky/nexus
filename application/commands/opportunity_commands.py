"""
Opportunity Commands

Architectural Intent:
- Application layer commands for opportunity (sales pipeline) operations
- Orchestrate domain entities through repository ports
- Handle stage transitions and business rules
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from domain import Opportunity, OpportunityStage, OpportunitySource, Money
from domain.ports.repository_ports import (
    OpportunityRepositoryPort,
    AccountRepositoryPort,
)
from domain.ports import EventBusPort, AuditLogPort
from application.dtos import OpportunityDTO, CreateOpportunityDTO


@dataclass
class CreateOpportunityCommand:
    repository: OpportunityRepositoryPort
    account_repository: AccountRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, dto: CreateOpportunityDTO) -> OpportunityDTO:
        account = await self.account_repository.get_by_id(UUID(dto.account_id))
        if not account:
            raise ValueError(f"Account {dto.account_id} not found")

        opportunity = Opportunity.create(
            account_id=UUID(dto.account_id),
            name=dto.name,
            amount=Money.from_float(dto.amount, dto.currency),
            close_date=dto.close_date,
            owner_id=UUID(dto.owner_id),
            source=OpportunitySource(dto.source) if dto.source else None,
            contact_id=UUID(dto.contact_id) if dto.contact_id else None,
            description=dto.description,
        )

        saved_opportunity = await self.repository.save(opportunity)

        await self.event_bus.publish(list(saved_opportunity.domain_events))

        await self.audit_log.log(
            user_id=dto.owner_id,
            action="CREATE",
            resource_type="Opportunity",
            resource_id=str(saved_opportunity.id),
            details={"name": saved_opportunity.name, "amount": dto.amount},
        )

        return OpportunityDTO.from_entity(saved_opportunity)


@dataclass
class UpdateOpportunityStageCommand:
    repository: OpportunityRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        opportunity_id: str,
        new_stage: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> OpportunityDTO:
        opportunity = await self.repository.get_by_id(UUID(opportunity_id))
        if not opportunity:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        old_stage = opportunity.stage.value
        stage = OpportunityStage(new_stage)
        updated = opportunity.change_stage(stage, reason)

        saved_opportunity = await self.repository.save(updated)

        await self.event_bus.publish(list(saved_opportunity.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="STAGE_CHANGE",
            resource_type="Opportunity",
            resource_id=str(saved_opportunity.id),
            details={"old_stage": old_stage, "new_stage": new_stage},
        )

        return OpportunityDTO.from_entity(saved_opportunity)


@dataclass
class UpdateOpportunityCommand:
    repository: OpportunityRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        opportunity_id: str,
        dto: CreateOpportunityDTO,
        user_id: str,
    ) -> OpportunityDTO:
        opportunity = await self.repository.get_by_id(UUID(opportunity_id))
        if not opportunity:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        updated = opportunity.update(
            name=dto.name,
            amount=Money.from_float(dto.amount, dto.currency),
            close_date=dto.close_date,
            description=dto.description,
        )

        saved_opportunity = await self.repository.save(updated)

        await self.event_bus.publish(list(saved_opportunity.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="UPDATE",
            resource_type="Opportunity",
            resource_id=str(saved_opportunity.id),
        )

        return OpportunityDTO.from_entity(saved_opportunity)
