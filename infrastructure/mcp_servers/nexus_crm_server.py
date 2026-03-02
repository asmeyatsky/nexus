"""
Nexus CRM MCP Server (Unified Facade)

Architectural Intent:
- MCP server exposing CRM domain capabilities
- Tools for write operations (commands)
- Resources for read operations (queries)
- Follows skill2026 MCP patterns
- Serves as a unified facade; all functionality is also available via
  dedicated per-context servers for finer-grained deployment:
    - sales_server.py      -- Opportunities, Pipeline operations
    - accounts_server.py   -- Accounts, Contacts, Relationships
    - marketing_server.py  -- Leads, Campaigns
    - support_server.py    -- Cases, Knowledge Articles, CSAT

MCP Integration:
- Exposed as 'nexus-crm' MCP server
- Tools: create_account, update_account, create_opportunity, etc.
- Resources: account://{id}, opportunity://{id}, etc.
"""

from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server

from application import (
    CreateAccountCommand,
    UpdateAccountCommand,
    CreateContactCommand,
    CreateOpportunityCommand,
    UpdateOpportunityStageCommand,
    CreateLeadCommand,
    QualifyLeadCommand,
    CreateCaseCommand,
    ResolveCaseCommand,
    GetAccountQuery,
    ListAccountsQuery,
    GetContactQuery,
    ListContactsQuery,
    GetOpportunityQuery,
    ListOpportunitiesQuery,
    GetOpenOpportunitiesQuery,
    GetLeadQuery,
    ListLeadsQuery,
    GetCaseQuery,
    GetCaseByNumberQuery,
    ListCasesQuery,
    GetOpenCasesQuery,
    CreateAccountDTO,
    CreateContactDTO,
    CreateOpportunityDTO,
    CreateLeadDTO,
    CreateCaseDTO,
)
from infrastructure.adapters import (
    ConsoleNotificationAdapter,
    InMemoryEventBusAdapter,
    ConsoleAuditLogAdapter,
    MockAuthenticationAdapter,
)


event_bus = InMemoryEventBusAdapter()
notification_adapter = ConsoleNotificationAdapter()
audit_log_adapter = ConsoleAuditLogAdapter()
auth_adapter = MockAuthenticationAdapter()


class NexusCRMMCPServer:
    """MCP server for Nexus CRM operations."""

    def __init__(self):
        self.server = Server("nexus-crm")
        self._register_tools()
        self._register_resources()

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
                repository=self._get_account_repo(),
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
                repository=self._get_account_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(account_id, dto, user_id or owner_id)
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
                repository=self._get_contact_repo(),
                account_repository=self._get_account_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

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
                repository=self._get_opportunity_repo(),
                account_repository=self._get_account_repo(),
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
            """Update the stage of an opportunity."""
            command = UpdateOpportunityStageCommand(
                repository=self._get_opportunity_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(opportunity_id, new_stage, user_id, reason)
            return {"success": True, "data": result.__dict__}

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
                repository=self._get_lead_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def qualify_lead(lead_id: str, user_id: str) -> dict:
            """Qualify a lead for conversion."""
            command = QualifyLeadCommand(
                repository=self._get_lead_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(lead_id, user_id)
            return {"success": True, "data": result.__dict__}

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
                repository=self._get_case_repo(),
                account_repository=self._get_account_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(dto)
            return {"success": True, "data": result.__dict__}

        @self.server.tool()
        async def resolve_case(
            case_id: str,
            resolution_notes: str,
            resolved_by: str,
            user_id: str,
        ) -> dict:
            """Resolve a support case."""
            command = ResolveCaseCommand(
                repository=self._get_case_repo(),
                event_bus=event_bus,
                audit_log=audit_log_adapter,
            )
            result = await command.execute(
                case_id, resolution_notes, resolved_by, user_id
            )
            return {"success": True, "data": result.__dict__}

    def _register_resources(self):
        @self.server.resource("account://{account_id}")
        async def get_account(account_id: str) -> str:
            """Get account details by ID."""
            query = GetAccountQuery(repository=self._get_account_repo())
            result = await query.execute(account_id)
            if result:
                import json

                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("accounts")
        async def list_accounts() -> str:
            """List all accounts."""
            query = ListAccountsQuery(repository=self._get_account_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("contact://{contact_id}")
        async def get_contact(contact_id: str) -> str:
            """Get contact details by ID."""
            query = GetContactQuery(repository=self._get_contact_repo())
            result = await query.execute(contact_id)
            if result:
                import json

                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("contacts")
        async def list_contacts() -> str:
            """List all contacts."""
            query = ListContactsQuery(repository=self._get_contact_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("opportunity://{opportunity_id}")
        async def get_opportunity(opportunity_id: str) -> str:
            """Get opportunity details by ID."""
            query = GetOpportunityQuery(repository=self._get_opportunity_repo())
            result = await query.execute(opportunity_id)
            if result:
                import json

                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("opportunities")
        async def list_opportunities() -> str:
            """List all opportunities."""
            query = ListOpportunitiesQuery(repository=self._get_opportunity_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("opportunities/open")
        async def get_open_opportunities() -> str:
            """Get all open opportunities."""
            query = GetOpenOpportunitiesQuery(repository=self._get_opportunity_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("lead://{lead_id}")
        async def get_lead(lead_id: str) -> str:
            """Get lead details by ID."""
            query = GetLeadQuery(repository=self._get_lead_repo())
            result = await query.execute(lead_id)
            if result:
                import json

                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("leads")
        async def list_leads() -> str:
            """List all leads."""
            query = ListLeadsQuery(repository=self._get_lead_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("case://{case_id}")
        async def get_case(case_id: str) -> str:
            """Get case details by ID."""
            query = GetCaseQuery(repository=self._get_case_repo())
            result = await query.execute(case_id)
            if result:
                import json

                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("case/number/{case_number}")
        async def get_case_by_number(case_number: str) -> str:
            """Get case details by case number."""
            query = GetCaseByNumberQuery(repository=self._get_case_repo())
            result = await query.execute(case_number)
            if result:
                import json

                return json.dumps(result.__dict__)
            return "{}"

        @self.server.resource("cases")
        async def list_cases() -> str:
            """List all cases."""
            query = ListCasesQuery(repository=self._get_case_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

        @self.server.resource("cases/open")
        async def get_open_cases() -> str:
            """Get all open cases."""
            query = GetOpenCasesQuery(repository=self._get_case_repo())
            results = await query.execute()
            import json

            return json.dumps([r.__dict__ for r in results])

    def _get_account_repo(self):

        return InMemoryAccountRepository()

    def _get_contact_repo(self):

        return InMemoryContactRepository()

    def _get_opportunity_repo(self):
        return InMemoryOpportunityRepository()

    def _get_lead_repo(self):
        return InMemoryLeadRepository()

    def _get_case_repo(self):
        return InMemoryCaseRepository()


class InMemoryAccountRepository:
    """In-memory account repository for development."""

    def __init__(self):
        self._accounts = {}

    async def save(self, account):
        self._accounts[str(account.id)] = account
        return account

    async def get_by_id(self, account_id):

        return self._accounts.get(str(account_id))

    async def get_by_name(self, name):
        for account in self._accounts.values():
            if account.name == name:
                return account
        return None

    async def get_all(self, limit=100, offset=0):
        return list(self._accounts.values())[offset : offset + limit]

    async def get_by_owner(self, owner_id):

        return [a for a in self._accounts.values() if str(a.owner_id) == str(owner_id)]

    async def get_by_industry(self, industry):
        return [a for a in self._accounts.values() if a.industry.type.value == industry]

    async def delete(self, account_id):
        self._accounts.pop(str(account_id), None)


class InMemoryContactRepository:
    """In-memory contact repository for development."""

    def __init__(self):
        self._contacts = {}

    async def save(self, contact):
        self._contacts[str(contact.id)] = contact
        return contact

    async def get_by_id(self, contact_id):
        return self._contacts.get(str(contact_id))

    async def get_by_email(self, email):
        for contact in self._contacts.values():
            if str(contact.email) == email:
                return contact
        return None

    async def get_by_account(self, account_id):

        return [
            c for c in self._contacts.values() if str(c.account_id) == str(account_id)
        ]

    async def get_all(self, limit=100, offset=0):
        return list(self._contacts.values())[offset : offset + limit]

    async def get_by_owner(self, owner_id):
        return [c for c in self._contacts.values() if str(c.owner_id) == str(owner_id)]

    async def delete(self, contact_id):
        self._contacts.pop(str(contact_id), None)


class InMemoryOpportunityRepository:
    """In-memory opportunity repository for development."""

    def __init__(self):
        self._opportunities = {}

    async def save(self, opportunity):
        self._opportunities[str(opportunity.id)] = opportunity
        return opportunity

    async def get_by_id(self, opportunity_id):
        return self._opportunities.get(str(opportunity_id))

    async def get_by_account(self, account_id):
        return [
            o
            for o in self._opportunities.values()
            if str(o.account_id) == str(account_id)
        ]

    async def get_all(self, limit=100, offset=0):
        return list(self._opportunities.values())[offset : offset + limit]

    async def get_by_owner(self, owner_id):
        return [
            o for o in self._opportunities.values() if str(o.owner_id) == str(owner_id)
        ]

    async def get_by_stage(self, stage):
        return [o for o in self._opportunities.values() if o.stage.value == stage]

    async def get_open_opportunities(self):
        return [o for o in self._opportunities.values() if not o.is_closed]

    async def get_by_close_date_range(self, start_date, end_date):
        return [
            o
            for o in self._opportunities.values()
            if start_date <= o.close_date <= end_date
        ]

    async def delete(self, opportunity_id):
        self._opportunities.pop(str(opportunity_id), None)


class InMemoryLeadRepository:
    """In-memory lead repository for development."""

    def __init__(self):
        self._leads = {}

    async def save(self, lead):
        self._leads[str(lead.id)] = lead
        return lead

    async def get_by_id(self, lead_id):
        return self._leads.get(str(lead_id))

    async def get_by_email(self, email):
        for lead in self._leads.values():
            if str(lead.email) == email:
                return lead
        return None

    async def get_all(self, limit=100, offset=0):
        return list(self._leads.values())[offset : offset + limit]

    async def get_by_status(self, status):
        return [lead for lead in self._leads.values() if lead.status.value == status]

    async def get_by_owner(self, owner_id):
        return [
            lead for lead in self._leads.values() if str(lead.owner_id) == str(owner_id)
        ]

    async def get_unqualified_leads(self):
        from domain.entities.lead import LeadStatus

        return [
            lead
            for lead in self._leads.values()
            if lead.status not in (LeadStatus.CONVERTED, LeadStatus.UNQUALIFIED)
        ]

    async def delete(self, lead_id):
        self._leads.pop(str(lead_id), None)


class InMemoryCaseRepository:
    """In-memory case repository for development."""

    def __init__(self):
        self._cases = {}

    async def save(self, case):
        self._cases[str(case.id)] = case
        return case

    async def get_by_id(self, case_id):
        return self._cases.get(str(case_id))

    async def get_by_case_number(self, case_number):
        for case in self._cases.values():
            if case.case_number == case_number:
                return case
        return None

    async def get_by_account(self, account_id):
        return [c for c in self._cases.values() if str(c.account_id) == str(account_id)]

    async def get_all(self, limit=100, offset=0):
        return list(self._cases.values())[offset : offset + limit]

    async def get_by_status(self, status):
        return [c for c in self._cases.values() if c.status.value == status]

    async def get_by_owner(self, owner_id):
        return [c for c in self._cases.values() if str(c.owner_id) == str(owner_id)]

    async def get_open_cases(self):
        from domain.entities.case import CaseStatus

        return [
            c
            for c in self._cases.values()
            if c.status not in (CaseStatus.RESOLVED, CaseStatus.CLOSED)
        ]

    async def delete(self, case_id):
        self._cases.pop(str(case_id), None)


async def main():
    server = NexusCRMMCPServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
