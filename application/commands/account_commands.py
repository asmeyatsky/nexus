"""
Account Commands

Architectural Intent:
- Application layer commands for account operations
- Orchestrate domain entities through repository ports
- Handle domain events and publish to event bus
"""

from dataclasses import dataclass
from uuid import UUID

from domain import Account, Industry, Territory, Money
from domain.ports.repository_ports import AccountRepositoryPort
from domain.ports import EventBusPort, AuditLogPort
from application.dtos import AccountDTO, CreateAccountDTO


@dataclass
class CreateAccountCommand:
    repository: AccountRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, dto: CreateAccountDTO) -> AccountDTO:
        account = Account.create(
            name=dto.name,
            industry=Industry.from_string(dto.industry),
            territory=Territory(
                region=dto.territory,
            ),
            owner_id=UUID(dto.owner_id),
            website=dto.website,
            phone=dto.phone,
        )

        if dto.annual_revenue:
            account = account.update(
                annual_revenue=Money.from_float(dto.annual_revenue, dto.currency),
                billing_address=dto.billing_address,
                employee_count=dto.employee_count,
            )

        saved_account = await self.repository.save(account)

        await self.event_bus.publish(list(saved_account.domain_events))

        await self.audit_log.log(
            user_id=dto.owner_id,
            action="CREATE",
            resource_type="Account",
            resource_id=str(saved_account.id),
            details={"name": saved_account.name},
        )

        return AccountDTO.from_entity(saved_account)


@dataclass
class UpdateAccountCommand:
    repository: AccountRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(
        self,
        account_id: str,
        dto: CreateAccountDTO,
        user_id: str,
    ) -> AccountDTO:
        account = await self.repository.get_by_id(UUID(account_id))
        if not account:
            raise ValueError(f"Account {account_id} not found")

        updated = account.update(
            name=dto.name,
            industry=Industry.from_string(dto.industry),
            territory=Territory(region=dto.territory),
            website=dto.website,
            phone=dto.phone,
            billing_address=dto.billing_address,
            annual_revenue=Money.from_float(dto.annual_revenue, dto.currency)
            if dto.annual_revenue
            else None,
            employee_count=dto.employee_count,
        )

        saved_account = await self.repository.save(updated)

        await self.event_bus.publish(list(saved_account.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="UPDATE",
            resource_type="Account",
            resource_id=str(saved_account.id),
        )

        return AccountDTO.from_entity(saved_account)


@dataclass
class DeactivateAccountCommand:
    repository: AccountRepositoryPort
    event_bus: EventBusPort
    audit_log: AuditLogPort

    async def execute(self, account_id: str, user_id: str) -> AccountDTO:
        account = await self.repository.get_by_id(UUID(account_id))
        if not account:
            raise ValueError(f"Account {account_id} not found")

        deactivated = account.deactivate()
        saved_account = await self.repository.save(deactivated)

        await self.event_bus.publish(list(saved_account.domain_events))

        await self.audit_log.log(
            user_id=user_id,
            action="DEACTIVATE",
            resource_type="Account",
            resource_id=str(saved_account.id),
        )

        return AccountDTO.from_entity(saved_account)
