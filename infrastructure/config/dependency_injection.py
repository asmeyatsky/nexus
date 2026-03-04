"""
Composition Root / Dependency Injection

Architectural Intent:
- Single place where all dependencies are wired together
- Clean separation of construction from use
- Easy swapping of implementations (test vs production)
"""

from infrastructure.config.settings import settings


class Container:
    """Dependency injection container — composition root."""

    def __init__(self, use_database: bool = None):
        self._singletons = {}
        if use_database is None:
            # Auto-detect: use DB when DATABASE_URL is set and not empty/sqlite
            db_url = settings.database_url
            self._use_database = bool(db_url and "sqlite" not in db_url)
        else:
            self._use_database = use_database
        self._db_session = None

    def set_db_session(self, session):
        self._db_session = session

    def account_repository(self, org_id: str = None, session=None):
        if self._use_database:
            db_session = session or self._db_session
            if db_session:
                from infrastructure.repositories.account_repository import AccountRepository

                return AccountRepository(db_session)
        from infrastructure.mcp_servers.nexus_crm_server import (
            InMemoryAccountRepository,
        )

        return self._singleton("account_repo", InMemoryAccountRepository)

    def contact_repository(self, org_id: str = None, session=None):
        if self._use_database:
            db_session = session or self._db_session
            if db_session:
                from infrastructure.repositories.contact_repository import ContactRepository

                return ContactRepository(db_session)
        from infrastructure.mcp_servers.nexus_crm_server import (
            InMemoryContactRepository,
        )

        return self._singleton("contact_repo", InMemoryContactRepository)

    def opportunity_repository(self, org_id: str = None, session=None):
        if self._use_database:
            db_session = session or self._db_session
            if db_session:
                from infrastructure.repositories.opportunity_repository import (
                    OpportunityRepository,
                )

                return OpportunityRepository(db_session)
        from infrastructure.mcp_servers.nexus_crm_server import (
            InMemoryOpportunityRepository,
        )

        return self._singleton("opportunity_repo", InMemoryOpportunityRepository)

    def lead_repository(self, org_id: str = None, session=None):
        if self._use_database:
            db_session = session or self._db_session
            if db_session:
                from infrastructure.repositories.lead_repository import LeadRepository

                return LeadRepository(db_session)
        from infrastructure.mcp_servers.nexus_crm_server import InMemoryLeadRepository

        return self._singleton("lead_repo", InMemoryLeadRepository)

    def case_repository(self, org_id: str = None, session=None):
        if self._use_database:
            db_session = session or self._db_session
            if db_session:
                from infrastructure.repositories.case_repository import CaseRepository

                return CaseRepository(db_session)
        from infrastructure.mcp_servers.nexus_crm_server import InMemoryCaseRepository

        return self._singleton("case_repo", InMemoryCaseRepository)

    def event_bus(self):
        from infrastructure.adapters import InMemoryEventBusAdapter

        return self._singleton("event_bus", InMemoryEventBusAdapter)

    def audit_log(self):
        from infrastructure.adapters import ConsoleAuditLogAdapter

        return self._singleton("audit_log", ConsoleAuditLogAdapter)

    def cache(self):
        from infrastructure.adapters.cache import RedisCache

        return self._singleton("cache", lambda: RedisCache(settings.redis_url))

    def rbac_service(self):
        from infrastructure.adapters.rbac import RBACService

        return self._singleton("rbac_service", RBACService)

    def webhook_service(self):
        from infrastructure.adapters.webhooks import WebhookService

        return self._singleton("webhook_service", WebhookService)

    def workflow_engine(self):
        from infrastructure.adapters.workflow import workflow_engine

        return workflow_engine

    def analytics(self):
        from infrastructure.adapters.analytics import BigQueryReporter

        return self._singleton(
            "analytics", lambda: BigQueryReporter(settings.gcp_project_id)
        )

    def pricing_service(self):
        from domain.services import PricingService

        return self._singleton("pricing_service", PricingService)

    def dedup_service(self):
        from domain.services import DeduplicationService

        return self._singleton("dedup_service", DeduplicationService)

    def lead_scoring_service(self):
        from domain.services import LeadScoringService

        return self._singleton("lead_scoring_service", LeadScoringService)

    def forecasting_service(self):
        from domain.services import ForecastingService

        return self._singleton("forecasting_service", ForecastingService)

    def _singleton(self, key: str, factory):
        if key not in self._singletons:
            self._singletons[key] = factory() if callable(factory) else factory
        return self._singletons[key]

    def reset(self):
        """Reset all singletons — useful for testing."""
        self._singletons.clear()


container = Container()
