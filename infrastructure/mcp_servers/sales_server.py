"""
Nexus CRM Sales Context MCP Server

Architectural Intent:
- Per-context MCP server for the Sales bounded context
- Handles Opportunities and Pipeline operations
- Tools for write operations (commands)
- Resources for read operations (queries)
- Follows skill2026 MCP patterns

MCP Integration:
- Exposed as 'nexus-sales' MCP server
- Tools: create_opportunity, update_opportunity_stage, update_opportunity
- Resources: opportunity://{id}, opportunities, opportunities/open,
             opportunities/account/{account_id}

See also: nexus_crm_server.py for the unified facade server.
"""

import json
import re
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server

from application import (
    CreateOpportunityCommand,
    UpdateOpportunityStageCommand,
    UpdateOpportunityCommand,
    GetOpportunityQuery,
    ListOpportunitiesQuery,
    GetOpportunitiesByAccountQuery,
    GetOpenOpportunitiesQuery,
    CreateOpportunityDTO,
)
from infrastructure.adapters import (
    InMemoryEventBusAdapter,
    ConsoleAuditLogAdapter,
)
from infrastructure.mcp_servers.nexus_crm_server import (
    InMemoryOpportunityRepository,
    InMemoryAccountRepository,
)


_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

event_bus = InMemoryEventBusAdapter()
audit_log_adapter = ConsoleAuditLogAdapter()


def _validate_auth(arguments: dict) -> None:
    """Validate that auth_token is present and non-empty."""
    token = arguments.get("auth_token") if isinstance(arguments, dict) else None
    if not token:
        raise ValueError("Missing or invalid auth_token in request arguments")


def _validate_uuid(value: str, field_name: str = "id") -> None:
    """Validate that a string is a valid UUID format."""
    if not _UUID_PATTERN.match(value):
        raise ValueError(f"Invalid UUID format for {field_name}: {value}")


class SalesMCPServer:
    """MCP server for Sales context: Opportunities and Pipeline operations."""

    def __init__(self):
        self.server = Server("nexus-sales")
        self._opportunity_repo = InMemoryOpportunityRepository()
        self._account_repo = InMemoryAccountRepository()
        self._register_tools()
        self._register_resources()

    # ------------------------------------------------------------------ Tools

    def _register_tools(self):
        @self.server.tool()
        async def create_opportunity(
            account_id: str,
            name: str,
            amount: float,
            currency: str,
            close_date: str,
            owner_id: str,
            source: str = None,
            contact_id: str = None,
            description: str = None,
        ) -> dict:
            """Create a new sales opportunity."""
            _validate_uuid(account_id, "account_id")
            _validate_uuid(owner_id, "owner_id")
            if contact_id:
                _validate_uuid(contact_id, "contact_id")
            dto = CreateOpportunityDTO(
                account_id=account_id,
                name=name,
                amount=amount,
                currency=currency,
                close_date=datetime.fromisoformat(close_date),
                owner_id=owner_id,
                source=source,
                contact_id=contact_id,
                description=description,
            )
            command = CreateOpportunityCommand(
                repository=self._opportunity_repo,
                account_repository=self._account_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def update_opportunity_stage(
            opportunity_id: str,
            new_stage: str,
            user_id: str,
            reason: str = None,
        ) -> dict:
            """Update the stage of an opportunity in the pipeline."""
            _validate_uuid(opportunity_id, "opportunity_id")
            _validate_uuid(user_id, "user_id")
            command = UpdateOpportunityStageCommand(
                repository=self._opportunity_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(opportunity_id, new_stage, user_id, reason)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def update_opportunity(
            opportunity_id: str,
            user_id: str,
            name: str = None,
            amount: float = None,
            close_date: str = None,
            description: str = None,
        ) -> dict:
            """Update general fields on an existing opportunity."""
            _validate_uuid(opportunity_id, "opportunity_id")
            _validate_uuid(user_id, "user_id")
            command = UpdateOpportunityCommand(
                repository=self._opportunity_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            parsed_close_date = (
                datetime.fromisoformat(close_date) if close_date else None
            )
            result = await command.execute(
                opportunity_id,
                user_id,
                name=name,
                amount=amount,
                close_date=parsed_close_date,
                description=description,
            )
            return {"success": True, "data": result.__dict__}

    # -------------------------------------------------------------- Resources

    def _register_resources(self):
        @self.server.resource("opportunity://{opportunity_id}")
        async def get_opportunity(opportunity_id: str) -> str:
            """Get opportunity details by ID."""
            _validate_uuid(opportunity_id, "opportunity_id")
            query = GetOpportunityQuery(repository=self._opportunity_repo)
            result = await query.execute(opportunity_id)
            if result:
                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("opportunities")
        async def list_opportunities() -> str:
            """List all opportunities."""
            query = ListOpportunitiesQuery(repository=self._opportunity_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("opportunities/open")
        async def get_open_opportunities() -> str:
            """Get all open opportunities (pipeline view)."""
            query = GetOpenOpportunitiesQuery(repository=self._opportunity_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("opportunities/account/{account_id}")
        async def get_opportunities_by_account(account_id: str) -> str:
            """Get all opportunities for a specific account."""
            _validate_uuid(account_id, "account_id")
            query = GetOpportunitiesByAccountQuery(
                repository=self._opportunity_repo,
            )
            results = await query.execute(account_id)
            return json.dumps([r.__dict__ for r in results])


async def main():
    server = SalesMCPServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
