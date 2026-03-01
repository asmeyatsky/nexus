"""
Case Commands

Architectural Intent:
- Application layer commands for case (customer support) operations
- Orchestrate domain entities through repository ports
"""

from dataclasses import dataclass
from uuid import UUID

from domain import Case, CaseStatus, CasePriority, CaseOrigin
from domain.ports.repository_ports import CaseRepositoryPort, AccountRepositoryPort
from domain.ports import EventBusPort, AuditLogPort
from application.dtos import CaseDTO, CreateCaseDTO


@dataclass
class CreateCaseCommand:
    repository: CaseRepositoryPort
    account_repository: AccountRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, dto: CreateCaseDTO) -> CaseDTO:
        account = await self.account_repository.get_by_id(UUID(dto.account_id))
        if not account:
            raise ValueError(f"Account {dto.account_id} not found")

        case = Case.create(
            subject=dto.subject,
            description=dto.description,
            account_id=UUID(dto.account_id),
            owner_id=UUID(dto.owner_id),
            case_number=dto.case_number,
            contact_id=UUID(dto.contact_id) if dto.contact_id else None,
            priority=CasePriority(dto.priority),
            origin=CaseOrigin(dto.origin),
        )

        saved_case = await self.repository.save(case)

        await self.event_bus.publish(list(saved_case.domain_events))

        await self.audit_log.log(
            user_id=dto.owner_id,
            action="CREATE",
            resource_type="Case",
            resource_id=str(saved_case.id),
            details={"case_number": dto.case_number, "subject": dto.subject},
        )

        return CaseDTO.from_entity(saved_case)


@dataclass
class UpdateCaseStatusCommand:
    repository: CaseRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        case_id: str,
        new_status: str,
        user_id: str,
    ) -> CaseDTO:
        case = await self.repository.get_by_id(UUID(case_id))
        if not case:
            raise ValueError(f"Case {case_id} not found")

        status = CaseStatus(new_status)
        updated = case.change_status(status)

        saved_case = await self.repository.save(updated)

        await self.event_bus.publish(list(saved_case.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="STATUS_CHANGE",
            resource_type="Case",
            resource_id=str(saved_case.id),
            details={"new_status": new_status},
        )

        return CaseDTO.from_entity(saved_case)


@dataclass
class ResolveCaseCommand:
    repository: CaseRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        case_id: str,
        resolution_notes: str,
        resolved_by: str,
        user_id: str,
    ) -> CaseDTO:
        case = await self.repository.get_by_id(UUID(case_id))
        if not case:
            raise ValueError(f"Case {case_id} not found")

        resolved = case.resolve(resolution_notes, resolved_by)

        saved_case = await self.repository.save(resolved)

        await self.event_bus.publish(list(saved_case.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="RESOLVE",
            resource_type="Case",
            resource_id=str(saved_case.id),
            details={"resolution_notes": resolution_notes},
        )

        return CaseDTO.from_entity(saved_case)


@dataclass
class CloseCaseCommand:
    repository: CaseRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, case_id: str, user_id: str) -> CaseDTO:
        case = await self.repository.get_by_id(UUID(case_id))
        if not case:
            raise ValueError(f"Case {case_id} not found")

        closed = case.close()

        saved_case = await self.repository.save(closed)

        await self.event_bus.publish(list(saved_case.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="CLOSE",
            resource_type="Case",
            resource_id=str(saved_case.id),
        )

        return CaseDTO.from_entity(saved_case)
