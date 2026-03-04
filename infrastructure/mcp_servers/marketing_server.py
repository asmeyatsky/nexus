"""
Nexus CRM Marketing Context MCP Server

Architectural Intent:
- Per-context MCP server for the Marketing bounded context
- Handles Leads and Campaigns
- Tools for write operations (commands)
- Resources for read operations (queries)
- Follows skill2026 MCP patterns

MCP Integration:
- Exposed as 'nexus-marketing' MCP server
- Tools: create_lead, qualify_lead, convert_lead
- Resources: lead://{id}, leads

See also: nexus_crm_server.py for the unified facade server.
"""

import json
import re

from mcp.server import Server
from mcp.server.stdio import stdio_server

from application import (
    CreateLeadCommand,
    QualifyLeadCommand,
    ConvertLeadCommand,
    GetLeadQuery,
    ListLeadsQuery,
    CreateLeadDTO,
)
from infrastructure.adapters import (
    InMemoryEventBusAdapter,
    ConsoleAuditLogAdapter,
)
from infrastructure.mcp_servers.nexus_crm_server import (
    InMemoryLeadRepository,
    InMemoryAccountRepository,
    InMemoryContactRepository,
    InMemoryOpportunityRepository,
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


class MarketingMCPServer:
    """MCP server for Marketing context: Leads and Campaigns."""

    def __init__(self):
        self.server = Server("nexus-marketing")
        self._lead_repo = InMemoryLeadRepository()
        self._account_repo = InMemoryAccountRepository()
        self._contact_repo = InMemoryContactRepository()
        self._opportunity_repo = InMemoryOpportunityRepository()
        self._register_tools()
        self._register_resources()

    # ------------------------------------------------------------------ Tools

    def _register_tools(self):
        @self.server.tool()
        async def create_lead(
            first_name: str,
            last_name: str,
            email: str,
            company: str,
            owner_id: str,
            source: str = None,
            phone: str = None,
            title: str = None,
            website: str = None,
        ) -> dict:
            """Create a new marketing lead."""
            _validate_uuid(owner_id, "owner_id")
            dto = CreateLeadDTO(
                first_name=first_name,
                last_name=last_name,
                email=email,
                company=company,
                owner_id=owner_id,
                source=source,
                phone=phone,
                title=title,
                website=website,
            )
            command = CreateLeadCommand(
                repository=self._lead_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def qualify_lead(lead_id: str, user_id: str) -> dict:
            """Qualify a lead, marking it ready for conversion."""
            _validate_uuid(lead_id, "lead_id")
            _validate_uuid(user_id, "user_id")
            command = QualifyLeadCommand(
                repository=self._lead_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(lead_id, user_id)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def convert_lead(
            lead_id: str,
            user_id: str,
            account_name: str = None,
        ) -> dict:
            """Convert a qualified lead into an Account, Contact, and Opportunity."""
            _validate_uuid(lead_id, "lead_id")
            _validate_uuid(user_id, "user_id")
            command = ConvertLeadCommand(
                repository=self._lead_repo,
                account_repository=self._account_repo,
                contact_repository=self._contact_repo,
                opportunity_repository=self._opportunity_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(lead_id, user_id, account_name)
            return {"success": True, "data": result.__dict__}

    # -------------------------------------------------------------- Resources

    def _register_resources(self):
        @self.server.resource("lead://{lead_id}")
        async def get_lead(lead_id: str) -> str:
            """Get lead details by ID."""
            _validate_uuid(lead_id, "lead_id")
            query = GetLeadQuery(repository=self._lead_repo)
            result = await query.execute(lead_id)
            if result:
                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("leads")
        async def list_leads() -> str:
            """List all leads."""
            query = ListLeadsQuery(repository=self._lead_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])


async def main():
    server = MarketingMCPServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
