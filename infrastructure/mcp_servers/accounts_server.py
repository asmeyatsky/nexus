"""
Nexus CRM Accounts Context MCP Server

Architectural Intent:
- Per-context MCP server for the Accounts bounded context
- Handles Accounts, Contacts, and Relationships
- Tools for write operations (commands)
- Resources for read operations (queries)
- Follows skill2026 MCP patterns

MCP Integration:
- Exposed as 'nexus-accounts' MCP server
- Tools: create_account, update_account, deactivate_account,
         create_contact, update_contact
- Resources: account://{id}, accounts, accounts/owner/{owner_id},
             contact://{id}, contacts, contacts/account/{account_id}

See also: nexus_crm_server.py for the unified facade server.
"""

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server

from application import (
    CreateAccountCommand,
    UpdateAccountCommand,
    DeactivateAccountCommand,
    CreateContactCommand,
    UpdateContactCommand,
    GetAccountQuery,
    ListAccountsQuery,
    GetAccountsByOwnerQuery,
    GetContactQuery,
    ListContactsQuery,
    GetContactsByAccountQuery,
    CreateAccountDTO,
    CreateContactDTO,
)
from infrastructure.adapters import (
    InMemoryEventBusAdapter,
    ConsoleAuditLogAdapter,
)
from infrastructure.mcp_servers.nexus_crm_server import (
    InMemoryAccountRepository,
    InMemoryContactRepository,
)


event_bus = InMemoryEventBusAdapter()
audit_log_adapter = ConsoleAuditLogAdapter()


class AccountsMCPServer:
    """MCP server for Accounts context: Accounts, Contacts, and Relationships."""

    def __init__(self):
        self.server = Server("nexus-accounts")
        self._account_repo = InMemoryAccountRepository()
        self._contact_repo = InMemoryContactRepository()
        self._register_tools()
        self._register_resources()

    # ------------------------------------------------------------------ Tools

    def _register_tools(self):
        @self.server.tool()
        async def create_account(
            name: str,
            industry: str,
            territory: str,
            owner_id: str,
            website: str = None,
            phone: str = None,
            annual_revenue: float = None,
            currency: str = "USD",
        ) -> dict:
            """Create a new account in the CRM."""
            dto = CreateAccountDTO(
                name=name,
                industry=industry,
                territory=territory,
                owner_id=owner_id,
                website=website,
                phone=phone,
                annual_revenue=annual_revenue,
                currency=currency,
            )
            command = CreateAccountCommand(
                repository=self._account_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def update_account(
            account_id: str,
            name: str,
            industry: str,
            territory: str,
            owner_id: str,
            website: str = None,
            phone: str = None,
            annual_revenue: float = None,
            currency: str = "USD",
            user_id: str = None,
        ) -> dict:
            """Update an existing account."""
            dto = CreateAccountDTO(
                name=name,
                industry=industry,
                territory=territory,
                owner_id=owner_id,
                website=website,
                phone=phone,
                annual_revenue=annual_revenue,
                currency=currency,
            )
            command = UpdateAccountCommand(
                repository=self._account_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(account_id, dto, user_id or owner_id)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def deactivate_account(
            account_id: str,
            user_id: str,
            reason: str = None,
        ) -> dict:
            """Deactivate an account."""
            command = DeactivateAccountCommand(
                repository=self._account_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(account_id, user_id, reason)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def create_contact(
            account_id: str,
            first_name: str,
            last_name: str,
            email: str,
            owner_id: str,
            phone: str = None,
            title: str = None,
            department: str = None,
        ) -> dict:
            """Create a new contact associated with an account."""
            dto = CreateContactDTO(
                account_id=account_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                owner_id=owner_id,
                phone=phone,
                title=title,
                department=department,
            )
            command = CreateContactCommand(
                repository=self._contact_repo,
                account_repository=self._account_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def update_contact(
            contact_id: str,
            user_id: str,
            first_name: str = None,
            last_name: str = None,
            email: str = None,
            phone: str = None,
            title: str = None,
            department: str = None,
        ) -> dict:
            """Update an existing contact."""
            command = UpdateContactCommand(
                repository=self._contact_repo,
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(
                contact_id,
                user_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                title=title,
                department=department,
            )
            return {"success": True, "data": result.__dict__}

    # -------------------------------------------------------------- Resources

    def _register_resources(self):
        @self.server.resource("account://{account_id}")
        async def get_account(account_id: str) -> str:
            """Get account details by ID."""
            query = GetAccountQuery(repository=self._account_repo)
            result = await query.execute(account_id)
            if result:
                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("accounts")
        async def list_accounts() -> str:
            """List all accounts."""
            query = ListAccountsQuery(repository=self._account_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("accounts/owner/{owner_id}")
        async def get_accounts_by_owner(owner_id: str) -> str:
            """Get all accounts owned by a specific user."""
            query = GetAccountsByOwnerQuery(repository=self._account_repo)
            results = await query.execute(owner_id)
            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("contact://{contact_id}")
        async def get_contact(contact_id: str) -> str:
            """Get contact details by ID."""
            query = GetContactQuery(repository=self._contact_repo)
            result = await query.execute(contact_id)
            if result:
                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("contacts")
        async def list_contacts() -> str:
            """List all contacts."""
            query = ListContactsQuery(repository=self._contact_repo)
            results = await query.execute()
            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("contacts/account/{account_id}")
        async def get_contacts_by_account(account_id: str) -> str:
            """Get all contacts for a specific account."""
            query = GetContactsByAccountQuery(repository=self._contact_repo)
            results = await query.execute(account_id)
            return json.dumps([r.__dict__ for r in results])


async def main():
    server = AccountsMCPServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
