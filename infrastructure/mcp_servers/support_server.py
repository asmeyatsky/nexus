"""
Nexus CRM Support Context MCP Server

Architectural Intent:
- Per-context MCP server for the Support bounded context
- Handles Cases, Knowledge Articles, and CSAT
- Tools for write operations (commands)
- Resources for read operations (queries)
- Follows skill2026 MCP patterns

MCP Integration:
- Exposed as 'nexus-support' MCP server
- Tools: create_case, update_case_status, resolve_case, close_case
- Resources: case://{id}, case/number/{number}, cases, cases/open

See also: nexus_crm_server.py for the unified facade server.
"""

import json
import re

from mcp.server import Server
from mcp.server.stdio import stdio_server

from application import (
    CreateCaseCommand,
    UpdateCaseStatusCommand,
    ResolveCaseCommand,
    CloseCaseCommand,
    GetCaseQuery,
    GetCaseByNumberQuery,
    ListCasesQuery,
    GetOpenCasesQuery,
    CreateCaseDTO,
)
from infrastructure.adapters import (
    InMemoryEventBusAdapter,
    ConsoleAuditLogAdapter,
)
from infrastructure.mcp_servers.nexus_crm_server import (
    InMemoryCaseRepository,
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


class SupportMCPServer:
    """MCP server for Support context: Cases, Knowledge Articles, and CSAT."""

    def __init__(self):
        self.server = Server("nexus-support")
        self._case_repo = InMemoryCaseRepository()
        self._account_repo = InMemoryAccountRepository()
        self._register_tools()
        self._register_resources()

    # ------------------------------------------------------------------ Tools

    def _register_tools(self):
        @self.server.tool()
        async def create_case(
            subject: str,
            description: str,
            account_id: str,
            owner_id: str,
            case_number: str,
            contact_id: str = None,
            priority: str = "medium",
            origin: str = "web",
        ) -> dict:
            """Create a new support case."""
            _validate_uuid(account_id, "account_id")
            _validate_uuid(owner_id, "owner_id")
            if contact_id:
                _validate_uuid(contact_id, "contact_id")
            dto = CreateCaseDTO(
                subject=subject,
                description=description,
                account_id=account_id,
                owner_id=owner_id,
                case_number=case_number,
                contact_id=contact_id,
                priority=priority,
                origin=origin,
            )
            command = CreateCaseCommand(
                repository=self._case_repo,
                account_repository=self._account_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def update_case_status(
            case_id: str,
            new_status: str,
            user_id: str,
            reason: str = None,
        ) -> dict:
            """Update the status of an existing support case."""
            _validate_uuid(case_id, "case_id")
            _validate_uuid(user_id, "user_id")
            command = UpdateCaseStatusCommand(
                repository=self._case_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(case_id, new_status, user_id, reason)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def resolve_case(
            case_id: str,
            resolution_notes: str,
            resolved_by: str,
            user_id: str,
        ) -> dict:
            """Resolve a support case with resolution notes."""
            _validate_uuid(case_id, "case_id")
            _validate_uuid(user_id, "user_id")
            command = ResolveCaseCommand(
                repository=self._case_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(
                case_id, resolution_notes, resolved_by, user_id
            )
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def close_case(
            case_id: str,
            user_id: str,
            satisfaction_rating: int = None,
            feedback: str = None,
        ) -> dict:
            """Close a resolved case, optionally with CSAT feedback."""
            _validate_uuid(case_id, "case_id")
            _validate_uuid(user_id, "user_id")
            command = CloseCaseCommand(
                repository=self._case_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(
                case_id, user_id, satisfaction_rating, feedback
            )
            return {"success": True, "data": result.__dict__}

    # -------------------------------------------------------------- Resources

    def _register_resources(self):
        @self.server.resource("case://{case_id}")
        async def get_case(case_id: str) -> str:
            """Get case details by ID."""
            _validate_uuid(case_id, "case_id")
            query = GetCaseQuery(repository=self._case_repo)
            result = await query.execute(case_id)
            if result:
                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("case/number/{case_number}")
        async def get_case_by_number(case_number: str) -> str:
            """Get case details by case number."""
            query = GetCaseByNumberQuery(repository=self._case_repo)
            result = await query.execute(case_number)
            if result:
                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("cases")
        async def list_cases() -> str:
            """List all support cases."""
            query = ListCasesQuery(repository=self._case_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("cases/open")
        async def get_open_cases() -> str:
            """Get all open support cases."""
            query = GetOpenCasesQuery(repository=self._case_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])


async def main():
    server = SupportMCPServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
