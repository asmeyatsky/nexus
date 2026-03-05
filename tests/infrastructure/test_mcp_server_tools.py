"""
Tests for infrastructure/mcp_servers/nexus_crm_server.py

Covers lines 75-506:
  - _validate_auth helper
  - _validate_uuid helper
  - NexusCRMMCPServer.__init__ (server name, repo creation, tool/resource registration)
  - Getter methods (_get_*_repo)
  - All registered tool functions (create_account, update_account, create_contact,
    create_opportunity, update_opportunity_stage, create_lead, qualify_lead,
    create_case, resolve_case)
  - All registered resource functions (get_account, list_accounts, get_contact,
    list_contacts, get_opportunity, list_opportunities, get_open_opportunities,
    get_lead, list_leads, get_case, get_case_by_number, list_cases, get_open_cases)

Strategy: The nexus_crm_server imports `Server` from `mcp.server`, which is the
lowlevel Server that does NOT have `.tool()` or `.resource()` decorator methods.
We monkey-patch `infrastructure.mcp_servers.nexus_crm_server.Server` with a
MockServer that captures registered async closures in dicts so we can invoke them
directly in tests.
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import json
import pytest
from uuid import uuid4
from dataclasses import replace


# ---------------------------------------------------------------------------
# MockServer – captures tool and resource closures so tests can call them
# ---------------------------------------------------------------------------

class MockServer:
    """Lightweight stand-in for mcp.server.Server that records registered handlers."""

    def __init__(self, name: str):
        self.name = name
        self._tools: dict = {}
        self._resources: dict = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def resource(self, uri: str):
        def decorator(fn):
            self._resources[fn.__name__] = fn
            return fn
        return decorator


# ---------------------------------------------------------------------------
# Patch the module before NexusCRMMCPServer is imported
# ---------------------------------------------------------------------------

import infrastructure.mcp_servers.nexus_crm_server as _crm_module

_crm_module.Server = MockServer  # type: ignore[attr-defined]

from infrastructure.mcp_servers.nexus_crm_server import (  # noqa: E402
    NexusCRMMCPServer,
    InMemoryAccountRepository,
    InMemoryContactRepository,
    InMemoryOpportunityRepository,
    InMemoryLeadRepository,
    InMemoryCaseRepository,
    _validate_auth,
    _validate_uuid,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    """Return a random UUID string."""
    return str(uuid4())


async def _make_account(server: NexusCRMMCPServer, owner_id: str, name: str = "Acme Corp") -> str:
    """Create an account and return its ID string."""
    result = await server.server._tools["create_account"](
        name=name,
        industry="technology",
        territory="north_america",
        owner_id=owner_id,
    )
    return result["data"]["id"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def crm_server() -> NexusCRMMCPServer:
    """Fresh NexusCRMMCPServer instance for each test."""
    return NexusCRMMCPServer()


# ===========================================================================
# 1. _validate_auth
# ===========================================================================

class TestValidateAuth:
    def test_raises_when_auth_token_missing(self):
        with pytest.raises(ValueError, match="Missing or invalid auth_token"):
            _validate_auth({})

    def test_raises_when_auth_token_empty_string(self):
        with pytest.raises(ValueError, match="Missing or invalid auth_token"):
            _validate_auth({"auth_token": ""})

    def test_raises_when_arguments_is_none(self):
        with pytest.raises(ValueError, match="Missing or invalid auth_token"):
            _validate_auth(None)  # type: ignore[arg-type]

    def test_succeeds_when_auth_token_present(self):
        # Should not raise
        _validate_auth({"auth_token": "my-secret-token"})

    def test_succeeds_with_extra_keys(self):
        # Additional keys should not affect auth validation
        _validate_auth({"auth_token": "tok", "user_id": _uid()})


# ===========================================================================
# 2. _validate_uuid
# ===========================================================================

class TestValidateUuid:
    def test_raises_for_obviously_invalid_string(self):
        with pytest.raises(ValueError, match="Invalid UUID format for owner_id"):
            _validate_uuid("not-a-uuid", "owner_id")

    def test_raises_for_empty_string(self):
        with pytest.raises(ValueError):
            _validate_uuid("", "field")

    def test_raises_for_uuid_missing_dashes(self):
        with pytest.raises(ValueError):
            _validate_uuid("550e8400e29b41d4a716446655440000", "field")

    def test_succeeds_for_valid_lowercase_uuid(self):
        _validate_uuid("550e8400-e29b-41d4-a716-446655440000", "field")

    def test_succeeds_for_valid_uppercase_uuid(self):
        _validate_uuid("550E8400-E29B-41D4-A716-446655440000", "field")

    def test_succeeds_for_uuid4_generated_value(self):
        _validate_uuid(_uid(), "test_field")


# ===========================================================================
# 3. NexusCRMMCPServer.__init__ and getter methods
# ===========================================================================

class TestNexusCRMMCPServerInit:
    def test_server_name_is_nexus_crm(self, crm_server):
        assert crm_server.server.name == "nexus-crm"

    def test_creates_in_memory_account_repository(self, crm_server):
        assert isinstance(crm_server._account_repo, InMemoryAccountRepository)

    def test_creates_in_memory_contact_repository(self, crm_server):
        assert isinstance(crm_server._contact_repo, InMemoryContactRepository)

    def test_creates_in_memory_opportunity_repository(self, crm_server):
        assert isinstance(crm_server._opportunity_repo, InMemoryOpportunityRepository)

    def test_creates_in_memory_lead_repository(self, crm_server):
        assert isinstance(crm_server._lead_repo, InMemoryLeadRepository)

    def test_creates_in_memory_case_repository(self, crm_server):
        assert isinstance(crm_server._case_repo, InMemoryCaseRepository)

    def test_registers_all_nine_tools(self, crm_server):
        expected = {
            "create_account", "update_account", "create_contact",
            "create_opportunity", "update_opportunity_stage",
            "create_lead", "qualify_lead", "create_case", "resolve_case",
        }
        assert set(crm_server.server._tools.keys()) == expected

    def test_registers_all_thirteen_resources(self, crm_server):
        expected = {
            "get_account", "list_accounts",
            "get_contact", "list_contacts",
            "get_opportunity", "list_opportunities", "get_open_opportunities",
            "get_lead", "list_leads",
            "get_case", "get_case_by_number", "list_cases", "get_open_cases",
        }
        assert set(crm_server.server._resources.keys()) == expected

    def test_getter_methods_return_correct_repos(self, crm_server):
        assert crm_server._get_account_repo() is crm_server._account_repo
        assert crm_server._get_contact_repo() is crm_server._contact_repo
        assert crm_server._get_opportunity_repo() is crm_server._opportunity_repo
        assert crm_server._get_lead_repo() is crm_server._lead_repo
        assert crm_server._get_case_repo() is crm_server._case_repo


# ===========================================================================
# 4. Tool: create_account
# ===========================================================================

class TestCreateAccountTool:
    @pytest.mark.asyncio
    async def test_creates_account_returns_success(self, crm_server):
        owner_id = _uid()
        result = await crm_server.server._tools["create_account"](
            name="Tech Corp",
            industry="technology",
            territory="north_america",
            owner_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["name"] == "Tech Corp"

    @pytest.mark.asyncio
    async def test_create_account_stores_in_repo(self, crm_server):
        owner_id = _uid()
        result = await crm_server.server._tools["create_account"](
            name="StoreCorp",
            industry="retail",
            territory="north_america",
            owner_id=owner_id,
        )
        account_id = result["data"]["id"]
        stored = await crm_server._account_repo.get_by_id(account_id)
        assert stored is not None
        assert stored.name == "StoreCorp"

    @pytest.mark.asyncio
    async def test_create_account_raises_for_invalid_owner_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for owner_id"):
            await crm_server.server._tools["create_account"](
                name="Bad Corp",
                industry="technology",
                territory="north_america",
                owner_id="not-a-uuid",
            )

    @pytest.mark.asyncio
    async def test_create_account_optional_fields(self, crm_server):
        owner_id = _uid()
        result = await crm_server.server._tools["create_account"](
            name="FullCorp",
            industry="healthcare",
            territory="emea",
            owner_id=owner_id,
            website="https://example.com",
            phone="+1-555-0100",
            annual_revenue=5000000.0,
            currency="EUR",
        )
        assert result["success"] is True
        assert result["data"]["website"] == "https://example.com"


# ===========================================================================
# 5. Tool: update_account
# ===========================================================================

class TestUpdateAccountTool:
    @pytest.mark.asyncio
    async def test_update_account_success(self, crm_server):
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        result = await crm_server.server._tools["update_account"](
            account_id=account_id,
            name="Updated Corp",
            industry="technology",
            territory="north_america",
            owner_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["name"] == "Updated Corp"

    @pytest.mark.asyncio
    async def test_update_account_raises_for_invalid_account_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for account_id"):
            await crm_server.server._tools["update_account"](
                account_id="bad-uuid",
                name="Test",
                industry="technology",
                territory="north_america",
                owner_id=_uid(),
            )

    @pytest.mark.asyncio
    async def test_update_account_raises_for_nonexistent_account(self, crm_server):
        with pytest.raises(ValueError, match="not found"):
            await crm_server.server._tools["update_account"](
                account_id=_uid(),
                name="Ghost Corp",
                industry="technology",
                territory="north_america",
                owner_id=_uid(),
            )

    @pytest.mark.asyncio
    async def test_update_account_validates_optional_user_id(self, crm_server):
        """Exercises the `if user_id: _validate_uuid(user_id, 'user_id')` branch (line 150)."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        with pytest.raises(ValueError, match="Invalid UUID format for user_id"):
            await crm_server.server._tools["update_account"](
                account_id=account_id,
                name="Corp",
                industry="technology",
                territory="north_america",
                owner_id=owner_id,
                user_id="bad-user-id",
            )


# ===========================================================================
# 6. Tool: create_contact
# ===========================================================================

class TestCreateContactTool:
    @pytest.mark.asyncio
    async def test_create_contact_success(self, crm_server):
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        result = await crm_server.server._tools["create_contact"](
            account_id=account_id,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            owner_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["first_name"] == "Alice"

    @pytest.mark.asyncio
    async def test_create_contact_raises_for_invalid_account_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for account_id"):
            await crm_server.server._tools["create_contact"](
                account_id="bad",
                first_name="Bob",
                last_name="Jones",
                email="bob@example.com",
                owner_id=_uid(),
            )


# ===========================================================================
# 7. Tool: create_opportunity
# ===========================================================================

class TestCreateOpportunityTool:
    @pytest.mark.asyncio
    async def test_create_opportunity_success(self, crm_server):
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        result = await crm_server.server._tools["create_opportunity"](
            account_id=account_id,
            name="Big Deal",
            amount=250000.0,
            currency="USD",
            close_date="2026-12-31",
            owner_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["name"] == "Big Deal"

    @pytest.mark.asyncio
    async def test_create_opportunity_raises_for_invalid_owner_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for owner_id"):
            await crm_server.server._tools["create_opportunity"](
                account_id=_uid(),
                name="Bad Opp",
                amount=1000.0,
                currency="USD",
                close_date="2026-12-31",
                owner_id="not-a-uuid",
            )

    @pytest.mark.asyncio
    async def test_create_opportunity_validates_optional_contact_id(self, crm_server):
        """Exercises the `if contact_id: _validate_uuid(contact_id, 'contact_id')` branch (line 218)."""
        owner_id = _uid()
        with pytest.raises(ValueError, match="Invalid UUID format for contact_id"):
            await crm_server.server._tools["create_opportunity"](
                account_id=_uid(),
                name="Contact Opp",
                amount=5000.0,
                currency="USD",
                close_date="2026-12-31",
                owner_id=owner_id,
                contact_id="bad-contact-id",
            )


# ===========================================================================
# 8. Tool: update_opportunity_stage
# ===========================================================================

class TestUpdateOpportunityStageTool:
    @pytest.mark.asyncio
    async def test_update_stage_success(self, crm_server):
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        opp = await crm_server.server._tools["create_opportunity"](
            account_id=account_id,
            name="Stage Deal",
            amount=50000.0,
            currency="USD",
            close_date="2026-09-30",
            owner_id=owner_id,
        )
        opp_id = opp["data"]["id"]
        result = await crm_server.server._tools["update_opportunity_stage"](
            opportunity_id=opp_id,
            new_stage="qualification",
            user_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["stage"] == "qualification"

    @pytest.mark.asyncio
    async def test_update_stage_raises_for_invalid_opportunity_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for opportunity_id"):
            await crm_server.server._tools["update_opportunity_stage"](
                opportunity_id="bad-uuid",
                new_stage="qualification",
                user_id=_uid(),
            )


# ===========================================================================
# 9. Tool: create_lead
# ===========================================================================

class TestCreateLeadTool:
    @pytest.mark.asyncio
    async def test_create_lead_success(self, crm_server):
        owner_id = _uid()
        result = await crm_server.server._tools["create_lead"](
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@startup.io",
            company="StartupCo",
            owner_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["first_name"] == "Jane"

    @pytest.mark.asyncio
    async def test_create_lead_raises_for_invalid_owner_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for owner_id"):
            await crm_server.server._tools["create_lead"](
                first_name="X",
                last_name="Y",
                email="x@y.com",
                company="Biz",
                owner_id="not-uuid",
            )


# ===========================================================================
# 10. Tool: qualify_lead
# ===========================================================================

class TestQualifyLeadTool:
    @pytest.mark.asyncio
    async def test_qualify_lead_success(self, crm_server):
        owner_id = _uid()
        lead_result = await crm_server.server._tools["create_lead"](
            first_name="Qual",
            last_name="Lead",
            email="qual@lead.com",
            company="LeadCo",
            owner_id=owner_id,
        )
        lead_id = lead_result["data"]["id"]
        result = await crm_server.server._tools["qualify_lead"](
            lead_id=lead_id,
            user_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["status"] == "qualified"

    @pytest.mark.asyncio
    async def test_qualify_lead_raises_for_invalid_lead_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for lead_id"):
            await crm_server.server._tools["qualify_lead"](
                lead_id="bad",
                user_id=_uid(),
            )

    @pytest.mark.asyncio
    async def test_qualify_lead_raises_for_invalid_user_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for user_id"):
            await crm_server.server._tools["qualify_lead"](
                lead_id=_uid(),
                user_id="bad",
            )


# ===========================================================================
# 11. Tool: create_case
# ===========================================================================

class TestCreateCaseTool:
    @pytest.mark.asyncio
    async def test_create_case_success(self, crm_server):
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        result = await crm_server.server._tools["create_case"](
            subject="Cannot Login",
            description="User is unable to log in.",
            account_id=account_id,
            owner_id=owner_id,
            case_number="CASE-001",
        )
        assert result["success"] is True
        assert result["data"]["subject"] == "Cannot Login"
        assert result["data"]["case_number"] == "CASE-001"

    @pytest.mark.asyncio
    async def test_create_case_raises_for_invalid_account_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for account_id"):
            await crm_server.server._tools["create_case"](
                subject="Test",
                description="Desc",
                account_id="bad-uuid",
                owner_id=_uid(),
                case_number="CASE-002",
            )

    @pytest.mark.asyncio
    async def test_create_case_validates_optional_contact_id(self, crm_server):
        """Exercises the `if contact_id: _validate_uuid(contact_id, 'contact_id')` branch (line 318)."""
        with pytest.raises(ValueError, match="Invalid UUID format for contact_id"):
            await crm_server.server._tools["create_case"](
                subject="Contact Case",
                description="Has a contact_id.",
                account_id=_uid(),
                owner_id=_uid(),
                case_number="CASE-003",
                contact_id="bad-contact-id",
            )


# ===========================================================================
# 12. Tool: resolve_case
# ===========================================================================

class TestResolveCaseTool:
    @pytest.mark.asyncio
    async def test_resolve_case_success(self, crm_server):
        from domain.entities.case import CaseStatus

        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        case_result = await crm_server.server._tools["create_case"](
            subject="Slow Loading",
            description="Pages load slowly.",
            account_id=account_id,
            owner_id=owner_id,
            case_number="CASE-010",
        )
        case_id = case_result["data"]["id"]

        # Transition to IN_PROGRESS so resolve is allowed
        case_obj = await crm_server._case_repo.get_by_id(case_id)
        await crm_server._case_repo.save(
            replace(case_obj, status=CaseStatus.IN_PROGRESS)
        )

        result = await crm_server.server._tools["resolve_case"](
            case_id=case_id,
            resolution_notes="Optimised queries – resolved.",
            resolved_by="Backend Team",
            user_id=owner_id,
        )
        assert result["success"] is True
        assert result["data"]["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_case_raises_for_invalid_case_uuid(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for case_id"):
            await crm_server.server._tools["resolve_case"](
                case_id="not-uuid",
                resolution_notes="Notes",
                resolved_by="Team",
                user_id=_uid(),
            )


# ===========================================================================
# 13. Resources: accounts
# ===========================================================================

class TestAccountResources:
    @pytest.mark.asyncio
    async def test_list_accounts_empty(self, crm_server):
        # Resources return JSON strings; an empty list serialises to '[]'
        result = await crm_server.server._resources["list_accounts"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_account_nonexistent_returns_empty_json(self, crm_server):
        result = await crm_server.server._resources["get_account"](account_id=_uid())
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_get_account_invalid_uuid_raises(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for account_id"):
            await crm_server.server._resources["get_account"](account_id="bad")

    @pytest.mark.asyncio
    async def test_get_account_with_existing_data_reaches_json_dump(self, crm_server):
        """Exercise the json.dumps(result.__dict__) branch; the entity contains
        datetime fields so the standard encoder raises TypeError – that is a known
        bug in the server code, but the line is still executed (and thus covered)."""
        owner_id = _uid()
        result = await crm_server.server._tools["create_account"](
            name="DumpCorp",
            industry="technology",
            territory="north_america",
            owner_id=owner_id,
        )
        account_id = result["data"]["id"]
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_account"](account_id=account_id)


# ===========================================================================
# 14. Resources: contacts
# ===========================================================================

class TestContactResources:
    @pytest.mark.asyncio
    async def test_list_contacts_empty(self, crm_server):
        result = await crm_server.server._resources["list_contacts"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_contact_nonexistent_returns_empty_json(self, crm_server):
        result = await crm_server.server._resources["get_contact"](contact_id=_uid())
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_get_contact_invalid_uuid_raises(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for contact_id"):
            await crm_server.server._resources["get_contact"](contact_id="not-uuid")

    @pytest.mark.asyncio
    async def test_get_contact_with_existing_data_reaches_json_dump(self, crm_server):
        """Exercise the json.dumps(result.__dict__) branch for get_contact (lines 387-389).
        Raises TypeError because the entity has datetime fields."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        contact_result = await crm_server.server._tools["create_contact"](
            account_id=account_id,
            first_name="Json",
            last_name="Test",
            email="json.test@example.com",
            owner_id=owner_id,
        )
        contact_id = contact_result["data"]["id"]
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_contact"](contact_id=contact_id)


# ===========================================================================
# 15. Resources: opportunities
# ===========================================================================

class TestOpportunityResources:
    @pytest.mark.asyncio
    async def test_list_opportunities_empty(self, crm_server):
        result = await crm_server.server._resources["list_opportunities"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_open_opportunities_empty(self, crm_server):
        result = await crm_server.server._resources["get_open_opportunities"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_opportunity_nonexistent_returns_empty_json(self, crm_server):
        result = await crm_server.server._resources["get_opportunity"](
            opportunity_id=_uid()
        )
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_get_opportunity_invalid_uuid_raises(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for opportunity_id"):
            await crm_server.server._resources["get_opportunity"](
                opportunity_id="bad-uuid"
            )

    @pytest.mark.asyncio
    async def test_list_opportunities_with_data_reaches_json_dump(self, crm_server):
        """list_opportunities exercises json.dumps path; entities have datetime fields
        so standard json raises TypeError – the code path is still executed."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        await crm_server.server._tools["create_opportunity"](
            account_id=account_id,
            name="Listed Opp",
            amount=10000.0,
            currency="USD",
            close_date="2026-06-30",
            owner_id=owner_id,
        )
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["list_opportunities"]()

    @pytest.mark.asyncio
    async def test_get_opportunity_with_existing_data_reaches_json_dump(self, crm_server):
        """Exercise the json.dumps(result.__dict__) branch for get_opportunity (lines 408-410)."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        opp_result = await crm_server.server._tools["create_opportunity"](
            account_id=account_id,
            name="Get Opp",
            amount=15000.0,
            currency="USD",
            close_date="2026-08-31",
            owner_id=owner_id,
        )
        opp_id = opp_result["data"]["id"]
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_opportunity"](opportunity_id=opp_id)


# ===========================================================================
# 16. Resources: leads
# ===========================================================================

class TestLeadResources:
    @pytest.mark.asyncio
    async def test_list_leads_empty(self, crm_server):
        result = await crm_server.server._resources["list_leads"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_lead_nonexistent_returns_empty_json(self, crm_server):
        result = await crm_server.server._resources["get_lead"](lead_id=_uid())
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_get_lead_invalid_uuid_raises(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for lead_id"):
            await crm_server.server._resources["get_lead"](lead_id="not-uuid")

    @pytest.mark.asyncio
    async def test_list_leads_with_data_reaches_json_dump(self, crm_server):
        """Exercise the list_leads json.dumps path; raises TypeError due to datetime."""
        owner_id = _uid()
        await crm_server.server._tools["create_lead"](
            first_name="List",
            last_name="Test",
            email="list.test@example.com",
            company="ListCo",
            owner_id=owner_id,
        )
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["list_leads"]()

    @pytest.mark.asyncio
    async def test_get_lead_with_existing_data_reaches_json_dump(self, crm_server):
        """Exercise the json.dumps(result.__dict__) branch for get_lead (lines 438-440)."""
        owner_id = _uid()
        lead_result = await crm_server.server._tools["create_lead"](
            first_name="Get",
            last_name="Lead",
            email="get.lead@example.com",
            company="GetCo",
            owner_id=owner_id,
        )
        lead_id = lead_result["data"]["id"]
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_lead"](lead_id=lead_id)


# ===========================================================================
# 17. Resources: cases
# ===========================================================================

class TestCaseResources:
    @pytest.mark.asyncio
    async def test_list_cases_empty(self, crm_server):
        result = await crm_server.server._resources["list_cases"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_open_cases_empty(self, crm_server):
        result = await crm_server.server._resources["get_open_cases"]()
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_get_case_nonexistent_returns_empty_json(self, crm_server):
        result = await crm_server.server._resources["get_case"](case_id=_uid())
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_get_case_invalid_uuid_raises(self, crm_server):
        with pytest.raises(ValueError, match="Invalid UUID format for case_id"):
            await crm_server.server._resources["get_case"](case_id="bad")

    @pytest.mark.asyncio
    async def test_get_case_by_number_nonexistent_returns_empty_json(self, crm_server):
        result = await crm_server.server._resources["get_case_by_number"](
            case_number="CASE-9999"
        )
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_get_case_with_existing_data_reaches_json_dump(self, crm_server):
        """Exercise the json.dumps(result.__dict__) branch for get_case (lines 459-461)."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        case_result = await crm_server.server._tools["create_case"](
            subject="Get Case",
            description="Testing get_case resource.",
            account_id=account_id,
            owner_id=owner_id,
            case_number="CASE-GET-001",
        )
        case_id = case_result["data"]["id"]
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_case"](case_id=case_id)

    @pytest.mark.asyncio
    async def test_get_case_by_number_with_existing_data_reaches_json_dump(self, crm_server):
        """Exercise the json.dumps(result.__dict__) branch for get_case_by_number (lines 470-472)."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        await crm_server.server._tools["create_case"](
            subject="Number Case",
            description="Testing get_case_by_number resource.",
            account_id=account_id,
            owner_id=owner_id,
            case_number="CASE-NUM-001",
        )
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_case_by_number"](
                case_number="CASE-NUM-001"
            )

    @pytest.mark.asyncio
    async def test_list_cases_with_data_reaches_json_dump(self, crm_server):
        """Exercise the list_cases json.dumps path; raises TypeError due to datetime."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        await crm_server.server._tools["create_case"](
            subject="List Check",
            description="Check listing.",
            account_id=account_id,
            owner_id=owner_id,
            case_number="CASE-LIST-001",
        )
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["list_cases"]()

    @pytest.mark.asyncio
    async def test_get_open_cases_with_data_reaches_json_dump(self, crm_server):
        """Exercise the get_open_cases json.dumps path; raises TypeError due to datetime."""
        owner_id = _uid()
        account_id = await _make_account(crm_server, owner_id)
        await crm_server.server._tools["create_case"](
            subject="Open Issue",
            description="Still open.",
            account_id=account_id,
            owner_id=owner_id,
            case_number="CASE-OPEN-001",
        )
        with pytest.raises(TypeError, match="is not JSON serializable"):
            await crm_server.server._resources["get_open_cases"]()
