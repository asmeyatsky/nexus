"""
Salesforce Data Migration Tool

Architectural Intent:
- Bulk data import from Salesforce to Nexus CRM
- Maps Salesforce objects to Nexus domain entities with proper field-level transforms
- Handles ID remapping from Salesforce 18-char IDs to Nexus UUIDs
- Preserves relationships (account_id, contact_id references) across entities
- Supports both live Salesforce API and offline CSV/JSON file imports
- Dry-run mode for validation without persistence

Key Design Decisions:
1. Migration order respects entity dependencies: Accounts -> Contacts -> Opportunities -> Leads -> Cases
2. IDRemapper provides a central registry for old-to-new ID translation
3. SalesforceObjectMapper handles field-level transforms per object type
4. SalesforceMigrator orchestrates the full pipeline with progress tracking
5. All errors are collected rather than failing fast, enabling partial migrations
"""

import csv
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Migration status tracking
# ---------------------------------------------------------------------------


class MigrationPhase(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    LOADING = "loading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MigrationProgress:
    """Tracks progress for a single object type migration."""

    object_type: str
    phase: MigrationPhase = MigrationPhase.PENDING
    total_records: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return (self.succeeded / self.processed) * 100.0

    def record_success(self) -> None:
        self.processed += 1
        self.succeeded += 1

    def record_failure(self, sf_id: str, error: str) -> None:
        self.processed += 1
        self.failed += 1
        self.errors.append(
            {
                "sf_id": sf_id,
                "error": error,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def record_skip(self, sf_id: str, reason: str) -> None:
        self.processed += 1
        self.skipped += 1
        logger.info("Skipped %s record %s: %s", self.object_type, sf_id, reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "phase": self.phase.value,
            "total_records": self.total_records,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": f"{self.success_rate:.1f}%",
            "error_count": len(self.errors),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


# ---------------------------------------------------------------------------
# ID Remapper: SF 18-char IDs  ->  Nexus UUIDs
# ---------------------------------------------------------------------------


class IDRemapper:
    """
    Central registry for mapping Salesforce IDs to Nexus UUIDs.

    Salesforce uses 15/18-character case-sensitive alphanumeric IDs.
    Nexus uses UUID4. This class creates and tracks the mapping so that
    relationship fields (e.g. AccountId on Contact) can be resolved after
    the parent entity has been migrated.
    """

    def __init__(self) -> None:
        # Keyed by object type for namespacing, then sf_id -> nexus uuid
        self._mappings: dict[str, dict[str, UUID]] = {}

    def register(
        self, object_type: str, sf_id: str, nexus_id: Optional[UUID] = None
    ) -> UUID:
        """Register a Salesforce ID and return the corresponding Nexus UUID."""
        if object_type not in self._mappings:
            self._mappings[object_type] = {}

        if sf_id in self._mappings[object_type]:
            return self._mappings[object_type][sf_id]

        new_id = nexus_id if nexus_id is not None else uuid4()
        self._mappings[object_type][sf_id] = new_id
        return new_id

    def get(self, object_type: str, sf_id: str) -> Optional[UUID]:
        """Look up the Nexus UUID for a given Salesforce ID."""
        return self._mappings.get(object_type, {}).get(sf_id)

    def get_or_raise(self, object_type: str, sf_id: str) -> UUID:
        """Look up the Nexus UUID, raising KeyError if not found."""
        result = self.get(object_type, sf_id)
        if result is None:
            raise KeyError(f"No Nexus UUID found for {object_type} SF ID: {sf_id}")
        return result

    def get_all(self, object_type: str) -> dict[str, UUID]:
        """Return all mappings for a given object type."""
        return dict(self._mappings.get(object_type, {}))

    def count(self, object_type: Optional[str] = None) -> int:
        """Count registered mappings, optionally filtered by object type."""
        if object_type:
            return len(self._mappings.get(object_type, {}))
        return sum(len(m) for m in self._mappings.values())

    def export_mappings(self) -> dict[str, dict[str, str]]:
        """Export all mappings as serialisable dict (UUID -> str)."""
        return {
            obj_type: {sf_id: str(nexus_id) for sf_id, nexus_id in mapping.items()}
            for obj_type, mapping in self._mappings.items()
        }

    def save_to_file(self, path: str) -> None:
        """Persist mappings to a JSON file for audit / rollback."""
        with open(path, "w") as f:
            json.dump(self.export_mappings(), f, indent=2)
        logger.info("ID mappings saved to %s", path)

    def load_from_file(self, path: str) -> None:
        """Load previously saved mappings (e.g. for incremental migration)."""
        with open(path) as f:
            data = json.load(f)
        for obj_type, mapping in data.items():
            if obj_type not in self._mappings:
                self._mappings[obj_type] = {}
            for sf_id, nexus_id_str in mapping.items():
                self._mappings[obj_type][sf_id] = UUID(nexus_id_str)
        logger.info("Loaded ID mappings from %s (%d total)", path, self.count())


# ---------------------------------------------------------------------------
# Field-level mapping definitions
# ---------------------------------------------------------------------------


@dataclass
class FieldMap:
    """Defines how a single Salesforce field maps to a Nexus field."""

    sf_field: str
    nexus_field: str
    transform: Optional[Callable[[Any], Any]] = None
    required: bool = False
    default: Any = None


# ---------------------------------------------------------------------------
# Salesforce -> Nexus territory inference from billing address
# ---------------------------------------------------------------------------

_TERRITORY_REGION_MAP: dict[str, str] = {
    "US": "Americas",
    "USA": "Americas",
    "United States": "Americas",
    "Canada": "Americas",
    "Brazil": "Americas",
    "Mexico": "Americas",
    "UK": "EMEA",
    "United Kingdom": "EMEA",
    "Germany": "EMEA",
    "France": "EMEA",
    "UAE": "EMEA",
    "India": "APAC",
    "China": "APAC",
    "Japan": "APAC",
    "Australia": "APAC",
    "Singapore": "APAC",
    "South Korea": "APAC",
}


def _infer_territory_region(billing_country: Optional[str]) -> str:
    """Best-effort mapping of a billing country to a Nexus territory region."""
    if not billing_country:
        return "Americas"
    return _TERRITORY_REGION_MAP.get(billing_country, "Americas")


def _normalise_stage(sf_stage: Optional[str]) -> str:
    """
    Map Salesforce opportunity stage names to Nexus OpportunityStage enum values.

    Salesforce stages like 'Prospecting', 'Closed Won', 'Needs Analysis'
    are normalised to the Nexus snake_case enum values.
    """
    if not sf_stage:
        return "prospecting"

    stage_map = {
        "prospecting": "prospecting",
        "qualification": "qualification",
        "needs analysis": "needs_analysis",
        "value proposition": "value_proposition",
        "id. decision makers": "decision_makers",
        "decision makers": "decision_makers",
        "proposal/price quote": "proposal",
        "proposal": "proposal",
        "negotiation/review": "negotiation",
        "negotiation": "negotiation",
        "closed won": "closed_won",
        "closed lost": "closed_lost",
    }
    normalised = sf_stage.strip().lower()
    return stage_map.get(normalised, "prospecting")


def _normalise_lead_status(sf_status: Optional[str]) -> str:
    """Map Salesforce lead status to Nexus LeadStatus enum values."""
    if not sf_status:
        return "new"
    status_map = {
        "open - not contacted": "new",
        "new": "new",
        "working - contacted": "contacted",
        "contacted": "contacted",
        "qualified": "qualified",
        "converted": "converted",
        "unqualified": "unqualified",
        "recycled": "recycled",
    }
    return status_map.get(sf_status.strip().lower(), "new")


def _normalise_lead_rating(sf_rating: Optional[str]) -> str:
    """Map Salesforce lead rating to Nexus LeadRating enum values."""
    if not sf_rating:
        return "cold"
    rating_map = {"hot": "hot", "warm": "warm", "cold": "cold"}
    return rating_map.get(sf_rating.strip().lower(), "cold")


def _normalise_case_status(sf_status: Optional[str]) -> str:
    """Map Salesforce case status to Nexus CaseStatus enum values."""
    if not sf_status:
        return "new"
    status_map = {
        "new": "new",
        "working": "in_progress",
        "in progress": "in_progress",
        "escalated": "in_progress",
        "waiting on customer": "waiting_on_customer",
        "waiting on third party": "waiting_on_third_party",
        "resolved": "resolved",
        "closed": "closed",
    }
    return status_map.get(sf_status.strip().lower(), "new")


def _normalise_case_priority(sf_priority: Optional[str]) -> str:
    """Map Salesforce case priority to Nexus CasePriority enum values."""
    if not sf_priority:
        return "medium"
    priority_map = {"high": "high", "medium": "medium", "low": "low"}
    return priority_map.get(sf_priority.strip().lower(), "medium")


def _normalise_case_origin(sf_origin: Optional[str]) -> str:
    """Map Salesforce case origin to Nexus CaseOrigin enum values."""
    if not sf_origin:
        return "web"
    origin_map = {
        "email": "email",
        "phone": "phone",
        "web": "web",
        "chat": "chat",
        "social": "social",
        "partner": "partner",
    }
    return origin_map.get(sf_origin.strip().lower(), "web")


def _parse_date(value: Optional[str]) -> Optional[str]:
    """Parse a Salesforce date string to ISO format."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").isoformat()
    except ValueError:
        return value


def _parse_amount(value: Any) -> float:
    """Safely parse an amount to float."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# SalesforceObjectMapper: field-level mapping per SF object type
# ---------------------------------------------------------------------------


class SalesforceObjectMapper:
    """
    Handles field-level mapping from Salesforce objects to Nexus entity dicts.

    Each object type (Account, Contact, Opportunity, Lead, Case) has a
    defined set of FieldMap entries that specify:
      - which SF field maps to which Nexus field
      - optional transform function
      - whether the field is required
      - default values for missing data
    """

    ACCOUNT_FIELDS: list[FieldMap] = [
        FieldMap("Id", "_sf_id", required=True),
        FieldMap("Name", "name", required=True),
        FieldMap("Industry", "industry", transform=lambda v: v if v else "Other"),
        FieldMap("Website", "website"),
        FieldMap("Phone", "phone"),
        FieldMap("BillingStreet", "billing_street"),
        FieldMap("BillingCity", "billing_city"),
        FieldMap("BillingState", "billing_state"),
        FieldMap("BillingPostalCode", "billing_postal_code"),
        FieldMap("BillingCountry", "billing_country"),
        FieldMap("AnnualRevenue", "annual_revenue", transform=_parse_amount),
        FieldMap(
            "NumberOfEmployees",
            "employee_count",
            transform=lambda v: int(v) if v else None,
        ),
        FieldMap("OwnerId", "_sf_owner_id"),
        FieldMap("ParentId", "_sf_parent_id"),
    ]

    CONTACT_FIELDS: list[FieldMap] = [
        FieldMap("Id", "_sf_id", required=True),
        FieldMap("FirstName", "first_name", required=True, default="Unknown"),
        FieldMap("LastName", "last_name", required=True),
        FieldMap("Email", "email", required=True),
        FieldMap("Phone", "phone"),
        FieldMap("Title", "title"),
        FieldMap("Department", "department"),
        FieldMap("AccountId", "_sf_account_id", required=True),
        FieldMap("OwnerId", "_sf_owner_id"),
    ]

    OPPORTUNITY_FIELDS: list[FieldMap] = [
        FieldMap("Id", "_sf_id", required=True),
        FieldMap("Name", "name", required=True),
        FieldMap("StageName", "stage", transform=_normalise_stage, required=True),
        FieldMap("Amount", "amount", transform=_parse_amount, default=0.0),
        FieldMap(
            "Probability", "probability", transform=lambda v: int(v) if v else None
        ),
        FieldMap("CloseDate", "close_date", transform=_parse_date, required=True),
        FieldMap("Description", "description"),
        FieldMap("LeadSource", "source"),
        FieldMap("AccountId", "_sf_account_id", required=True),
        FieldMap("ContactId", "_sf_contact_id"),
        FieldMap("OwnerId", "_sf_owner_id"),
    ]

    LEAD_FIELDS: list[FieldMap] = [
        FieldMap("Id", "_sf_id", required=True),
        FieldMap("FirstName", "first_name", required=True, default="Unknown"),
        FieldMap("LastName", "last_name", required=True),
        FieldMap("Email", "email", required=True),
        FieldMap("Company", "company", required=True),
        FieldMap("Status", "status", transform=_normalise_lead_status),
        FieldMap("Rating", "rating", transform=_normalise_lead_rating),
        FieldMap("Phone", "phone"),
        FieldMap("Title", "title"),
        FieldMap("Website", "website"),
        FieldMap("LeadSource", "source"),
        FieldMap("OwnerId", "_sf_owner_id"),
    ]

    CASE_FIELDS: list[FieldMap] = [
        FieldMap("Id", "_sf_id", required=True),
        FieldMap("CaseNumber", "case_number"),
        FieldMap("Subject", "subject", required=True),
        FieldMap("Description", "description", required=True, default=""),
        FieldMap("Status", "status", transform=_normalise_case_status),
        FieldMap("Priority", "priority", transform=_normalise_case_priority),
        FieldMap("Origin", "origin", transform=_normalise_case_origin),
        FieldMap("AccountId", "_sf_account_id", required=True),
        FieldMap("ContactId", "_sf_contact_id"),
        FieldMap("OwnerId", "_sf_owner_id"),
    ]

    _OBJECT_FIELDS: dict[str, list[FieldMap]] = {
        "Account": ACCOUNT_FIELDS,
        "Contact": CONTACT_FIELDS,
        "Opportunity": OPPORTUNITY_FIELDS,
        "Lead": LEAD_FIELDS,
        "Case": CASE_FIELDS,
    }

    @classmethod
    def get_field_maps(cls, sf_object_type: str) -> list[FieldMap]:
        """Return the field mappings for a given Salesforce object type."""
        maps = cls._OBJECT_FIELDS.get(sf_object_type)
        if maps is None:
            raise ValueError(
                f"No field mappings defined for SF object: {sf_object_type}"
            )
        return maps

    @classmethod
    def map_record(
        cls, sf_object_type: str, sf_record: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Transform a single Salesforce record dict into a Nexus-compatible dict.

        Returns the mapped dict. Raises ValueError if a required field is
        missing and has no default.
        """
        field_maps = cls.get_field_maps(sf_object_type)
        result: dict[str, Any] = {}

        for fm in field_maps:
            raw_value = sf_record.get(fm.sf_field)

            # Apply default if value is missing
            if raw_value is None:
                if fm.default is not None:
                    raw_value = fm.default
                elif fm.required:
                    raise ValueError(
                        f"Required field '{fm.sf_field}' missing in {sf_object_type} "
                        f"record (SF Id: {sf_record.get('Id', 'unknown')})"
                    )
                else:
                    continue  # Optional field, skip

            # Apply transform
            if fm.transform is not None:
                try:
                    raw_value = fm.transform(raw_value)
                except Exception as exc:
                    logger.warning(
                        "Transform failed for %s.%s: %s (value=%r)",
                        sf_object_type,
                        fm.sf_field,
                        exc,
                        raw_value,
                    )
                    if fm.required:
                        raise ValueError(
                            f"Transform failed for required field '{fm.sf_field}': {exc}"
                        ) from exc
                    continue

            result[fm.nexus_field] = raw_value

        return result

    @classmethod
    def supported_objects(cls) -> list[str]:
        """Return list of supported Salesforce object types."""
        return list(cls._OBJECT_FIELDS.keys())


# ---------------------------------------------------------------------------
# Data source: reads SF data from API or exported files
# ---------------------------------------------------------------------------


class SalesforceDataSource:
    """
    Abstraction over where Salesforce data comes from.

    Supports:
    - Live Salesforce API via simple_salesforce or httpx
    - Exported CSV files (one per object, named Account.csv, Contact.csv, etc.)
    - Exported JSON files (one per object, named Account.json, etc.)
    """

    def __init__(
        self,
        *,
        sf_instance_url: Optional[str] = None,
        sf_access_token: Optional[str] = None,
        sf_client_id: Optional[str] = None,
        sf_client_secret: Optional[str] = None,
        sf_username: Optional[str] = None,
        sf_password: Optional[str] = None,
        export_dir: Optional[str] = None,
    ) -> None:
        self.sf_instance_url = sf_instance_url
        self.sf_access_token = sf_access_token
        self.sf_client_id = sf_client_id
        self.sf_client_secret = sf_client_secret
        self.sf_username = sf_username
        self.sf_password = sf_password
        self.export_dir = export_dir
        self._authenticated = False

    @property
    def is_file_source(self) -> bool:
        return self.export_dir is not None

    def _authenticate_api(self) -> None:
        """Authenticate with Salesforce REST API (OAuth 2.0 client credentials)."""
        if self._authenticated:
            return

        if self.sf_access_token:
            self._authenticated = True
            return

        import httpx

        token_url = f"{self.sf_instance_url}/services/oauth2/token"
        payload = {
            "grant_type": "password",
            "client_id": self.sf_client_id,
            "client_secret": self.sf_client_secret,
            "username": self.sf_username,
            "password": self.sf_password,
        }
        response = httpx.post(token_url, data=payload, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        self.sf_access_token = token_data["access_token"]
        if not self.sf_instance_url:
            self.sf_instance_url = token_data.get("instance_url", self.sf_instance_url)
        self._authenticated = True
        logger.info("Authenticated with Salesforce API at %s", self.sf_instance_url)

    def _query_api(self, soql: str) -> list[dict[str, Any]]:
        """Execute a SOQL query and return all records (handles pagination)."""
        import httpx

        self._authenticate_api()

        headers = {"Authorization": f"Bearer {self.sf_access_token}"}
        url = f"{self.sf_instance_url}/services/data/v59.0/query"
        records: list[dict[str, Any]] = []

        response = httpx.get(url, headers=headers, params={"q": soql}, timeout=60)
        response.raise_for_status()
        data = response.json()
        records.extend(data.get("records", []))

        # Handle Salesforce pagination via nextRecordsUrl
        while data.get("nextRecordsUrl"):
            next_url = f"{self.sf_instance_url}{data['nextRecordsUrl']}"
            response = httpx.get(next_url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            records.extend(data.get("records", []))

        return records

    def _read_csv(self, object_type: str) -> list[dict[str, Any]]:
        """Read records from a CSV export file."""
        file_path = Path(self.export_dir) / f"{object_type}.csv"
        if not file_path.exists():
            logger.warning("CSV file not found: %s", file_path)
            return []

        records = []
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert empty strings to None for consistency
                cleaned = {k: (v if v != "" else None) for k, v in row.items()}
                records.append(cleaned)

        logger.info("Read %d records from %s", len(records), file_path)
        return records

    def _read_json(self, object_type: str) -> list[dict[str, Any]]:
        """Read records from a JSON export file."""
        file_path = Path(self.export_dir) / f"{object_type}.json"
        if not file_path.exists():
            logger.warning("JSON file not found: %s", file_path)
            return []

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        records = data if isinstance(data, list) else data.get("records", [])
        logger.info("Read %d records from %s", len(records), file_path)
        return records

    def _build_soql(self, object_type: str) -> str:
        """Build a SOQL query to fetch all relevant fields for the object type."""
        field_maps = SalesforceObjectMapper.get_field_maps(object_type)
        sf_fields = [fm.sf_field for fm in field_maps]
        # Ensure Id is always included
        if "Id" not in sf_fields:
            sf_fields.insert(0, "Id")
        fields_str = ", ".join(sf_fields)
        return f"SELECT {fields_str} FROM {object_type}"

    def fetch_records(self, object_type: str) -> list[dict[str, Any]]:
        """
        Fetch all records for a given Salesforce object type.

        Automatically chooses between API, CSV, or JSON based on configuration.
        """
        if self.is_file_source:
            # Try JSON first, fall back to CSV
            json_path = Path(self.export_dir) / f"{object_type}.json"
            if json_path.exists():
                return self._read_json(object_type)
            return self._read_csv(object_type)

        soql = self._build_soql(object_type)
        logger.info("Querying Salesforce: %s", soql)
        return self._query_api(soql)


# ---------------------------------------------------------------------------
# SalesforceMigrator: main orchestrator
# ---------------------------------------------------------------------------


@dataclass
class MigrationConfig:
    """Configuration for a Salesforce migration run."""

    # Salesforce API credentials (optional if using file export)
    sf_instance_url: Optional[str] = None
    sf_access_token: Optional[str] = None
    sf_client_id: Optional[str] = None
    sf_client_secret: Optional[str] = None
    sf_username: Optional[str] = None
    sf_password: Optional[str] = None

    # File-based import (alternative to API)
    export_dir: Optional[str] = None

    # Migration behaviour
    dry_run: bool = False
    batch_size: int = 500
    default_owner_id: UUID = field(default_factory=uuid4)
    output_dir: str = "./migration_output"

    # Which objects to migrate (None = all)
    objects: Optional[list[str]] = None


class SalesforceMigrator:
    """
    Orchestrates bulk data migration from Salesforce to Nexus CRM.

    Usage:
        config = MigrationConfig(export_dir="/path/to/sf_exports", dry_run=True)
        migrator = SalesforceMigrator(config)
        results = migrator.migrate_all()
    """

    # Migration order respects FK dependencies
    MIGRATION_ORDER = ["Account", "Contact", "Opportunity", "Lead", "Case"]

    def __init__(self, config: MigrationConfig) -> None:
        self.config = config
        self.id_remapper = IDRemapper()
        self.mapper = SalesforceObjectMapper()
        self.data_source = SalesforceDataSource(
            sf_instance_url=config.sf_instance_url,
            sf_access_token=config.sf_access_token,
            sf_client_id=config.sf_client_id,
            sf_client_secret=config.sf_client_secret,
            sf_username=config.sf_username,
            sf_password=config.sf_password,
            export_dir=config.export_dir,
        )
        self.progress: dict[str, MigrationProgress] = {}
        self._migrated_records: dict[str, list[dict[str, Any]]] = {}
        self._case_counter = 0

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def migrate_all(self) -> dict[str, MigrationProgress]:
        """
        Execute the full migration pipeline.

        Returns a dict of object_type -> MigrationProgress with results.
        """
        objects_to_migrate = self.config.objects or self.MIGRATION_ORDER
        # Enforce dependency order
        ordered = [obj for obj in self.MIGRATION_ORDER if obj in objects_to_migrate]

        logger.info(
            "Starting Salesforce migration (dry_run=%s, objects=%s)",
            self.config.dry_run,
            ordered,
        )

        for object_type in ordered:
            self._migrate_object(object_type)

        # Save ID mappings for audit trail
        if not self.config.dry_run:
            os.makedirs(self.config.output_dir, exist_ok=True)
            mapping_path = os.path.join(self.config.output_dir, "id_mappings.json")
            self.id_remapper.save_to_file(mapping_path)

        # Save results summary
        self._save_summary()

        logger.info("Migration complete. Summary:\n%s", self.format_summary())
        return self.progress

    def migrate_object(self, object_type: str) -> MigrationProgress:
        """Migrate a single object type (public convenience wrapper)."""
        self._migrate_object(object_type)
        return self.progress[object_type]

    def format_summary(self) -> str:
        """Return a human-readable migration summary."""
        lines = ["=" * 60, "SALESFORCE MIGRATION SUMMARY", "=" * 60]
        if self.config.dry_run:
            lines.append("[DRY RUN - no records were persisted]")
        lines.append("")

        total_succeeded = 0
        total_failed = 0
        total_skipped = 0

        for obj_type, prog in self.progress.items():
            total_succeeded += prog.succeeded
            total_failed += prog.failed
            total_skipped += prog.skipped
            lines.append(
                f"  {obj_type:15s}  "
                f"total={prog.total_records:>6d}  "
                f"ok={prog.succeeded:>6d}  "
                f"fail={prog.failed:>4d}  "
                f"skip={prog.skipped:>4d}  "
                f"({prog.success_rate:.1f}%)"
            )

        lines.append("-" * 60)
        grand_total = total_succeeded + total_failed + total_skipped
        lines.append(
            f"  {'TOTAL':15s}  "
            f"total={grand_total:>6d}  "
            f"ok={total_succeeded:>6d}  "
            f"fail={total_failed:>4d}  "
            f"skip={total_skipped:>4d}"
        )
        lines.append("=" * 60)
        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Internal: per-object migration
    # -------------------------------------------------------------------

    def _migrate_object(self, object_type: str) -> None:
        """Run extraction, transformation, and loading for one object type."""
        progress = MigrationProgress(object_type=object_type)
        progress.started_at = datetime.now(UTC)
        self.progress[object_type] = progress

        # --- Extract ---
        progress.phase = MigrationPhase.EXTRACTING
        try:
            sf_records = self.data_source.fetch_records(object_type)
        except Exception as exc:
            logger.error("Failed to extract %s records: %s", object_type, exc)
            progress.phase = MigrationPhase.FAILED
            progress.errors.append({"phase": "extract", "error": str(exc)})
            progress.completed_at = datetime.now(UTC)
            return

        progress.total_records = len(sf_records)
        logger.info("Extracted %d %s records", len(sf_records), object_type)

        # --- Transform + Load ---
        progress.phase = MigrationPhase.TRANSFORMING
        migrated_batch: list[dict[str, Any]] = []

        for sf_record in sf_records:
            sf_id = sf_record.get("Id", "unknown")
            try:
                nexus_data = self._transform_record(object_type, sf_record)
                migrated_batch.append(nexus_data)
                progress.record_success()
            except Exception as exc:
                logger.warning(
                    "Failed to transform %s record %s: %s",
                    object_type,
                    sf_id,
                    exc,
                )
                progress.record_failure(sf_id, str(exc))

        self._migrated_records[object_type] = migrated_batch

        # --- Load (persist) ---
        if not self.config.dry_run and migrated_batch:
            progress.phase = MigrationPhase.LOADING
            try:
                self._load_records(object_type, migrated_batch)
            except Exception as exc:
                logger.error("Failed to load %s records: %s", object_type, exc)
                progress.phase = MigrationPhase.FAILED
                progress.errors.append({"phase": "load", "error": str(exc)})
                progress.completed_at = datetime.now(UTC)
                return

        progress.phase = MigrationPhase.COMPLETED
        progress.completed_at = datetime.now(UTC)
        logger.info(
            "Completed %s migration: %d/%d succeeded",
            object_type,
            progress.succeeded,
            progress.total_records,
        )

    def _transform_record(
        self, object_type: str, sf_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform a single SF record into a Nexus entity dict."""
        # Run the field-level mapper
        nexus_data = self.mapper.map_record(object_type, sf_record)

        sf_id = nexus_data.pop("_sf_id", sf_record.get("Id"))

        # Register the new Nexus UUID via ID remapper
        nexus_uuid = self.id_remapper.register(object_type, sf_id)
        nexus_data["id"] = str(nexus_uuid)

        # Resolve owner_id: remap if previously seen, else use default
        sf_owner_id = nexus_data.pop("_sf_owner_id", None)
        if sf_owner_id:
            owner_uuid = self.id_remapper.get("User", sf_owner_id)
            nexus_data["owner_id"] = (
                str(owner_uuid) if owner_uuid else str(self.config.default_owner_id)
            )
        else:
            nexus_data["owner_id"] = str(self.config.default_owner_id)

        # Object-specific relationship resolution
        if object_type == "Account":
            nexus_data = self._resolve_account_fields(nexus_data, sf_record)
        elif object_type == "Contact":
            nexus_data = self._resolve_contact_fields(nexus_data)
        elif object_type == "Opportunity":
            nexus_data = self._resolve_opportunity_fields(nexus_data)
        elif object_type == "Lead":
            nexus_data = self._resolve_lead_fields(nexus_data)
        elif object_type == "Case":
            nexus_data = self._resolve_case_fields(nexus_data)

        return nexus_data

    # -------------------------------------------------------------------
    # Relationship resolvers per entity type
    # -------------------------------------------------------------------

    def _resolve_account_fields(
        self, data: dict[str, Any], sf_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve Account-specific fields like territory and parent account."""
        # Build billing address from parts
        address_parts = []
        for key in (
            "billing_street",
            "billing_city",
            "billing_state",
            "billing_postal_code",
            "billing_country",
        ):
            val = data.pop(key, None)
            if val:
                address_parts.append(val)
        if address_parts:
            data["billing_address"] = ", ".join(address_parts)

        # Territory inference from billing country
        billing_country = sf_record.get("BillingCountry")
        region = _infer_territory_region(billing_country)
        data["territory_region"] = region
        data["territory_country"] = billing_country

        # Industry normalisation (Nexus uses Industry value object)
        industry_raw = data.get("industry", "Other")
        data["industry"] = industry_raw

        # Parent account relationship
        sf_parent_id = data.pop("_sf_parent_id", None)
        if sf_parent_id:
            parent_uuid = self.id_remapper.get("Account", sf_parent_id)
            if parent_uuid:
                data["parent_account_id"] = str(parent_uuid)

        return data

    def _resolve_contact_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve Contact FK references (account_id)."""
        sf_account_id = data.pop("_sf_account_id", None)
        if sf_account_id:
            account_uuid = self.id_remapper.get("Account", sf_account_id)
            if account_uuid:
                data["account_id"] = str(account_uuid)
            else:
                raise ValueError(
                    f"Contact references unmigrated Account: {sf_account_id}"
                )
        else:
            raise ValueError("Contact missing required AccountId")
        return data

    def _resolve_opportunity_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve Opportunity FK references (account_id, contact_id)."""
        sf_account_id = data.pop("_sf_account_id", None)
        if sf_account_id:
            account_uuid = self.id_remapper.get("Account", sf_account_id)
            if account_uuid:
                data["account_id"] = str(account_uuid)
            else:
                raise ValueError(
                    f"Opportunity references unmigrated Account: {sf_account_id}"
                )
        else:
            raise ValueError("Opportunity missing required AccountId")

        sf_contact_id = data.pop("_sf_contact_id", None)
        if sf_contact_id:
            contact_uuid = self.id_remapper.get("Contact", sf_contact_id)
            if contact_uuid:
                data["contact_id"] = str(contact_uuid)

        # Ensure amount is numeric
        if "amount" in data:
            data["amount"] = float(data["amount"])
        # Ensure probability is int
        if "probability" in data and data["probability"] is not None:
            data["probability"] = int(data["probability"])

        return data

    def _resolve_lead_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve Lead-specific normalisations."""
        # Lead has no FK dependencies beyond owner_id (already resolved)
        return data

    def _resolve_case_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve Case FK references (account_id, contact_id) and case number."""
        sf_account_id = data.pop("_sf_account_id", None)
        if sf_account_id:
            account_uuid = self.id_remapper.get("Account", sf_account_id)
            if account_uuid:
                data["account_id"] = str(account_uuid)
            else:
                raise ValueError(f"Case references unmigrated Account: {sf_account_id}")
        else:
            raise ValueError("Case missing required AccountId")

        sf_contact_id = data.pop("_sf_contact_id", None)
        if sf_contact_id:
            contact_uuid = self.id_remapper.get("Contact", sf_contact_id)
            if contact_uuid:
                data["contact_id"] = str(contact_uuid)

        # Generate case number if not present
        if not data.get("case_number"):
            self._case_counter += 1
            data["case_number"] = f"NX-{self._case_counter:06d}"

        return data

    # -------------------------------------------------------------------
    # Loading (persistence stub)
    # -------------------------------------------------------------------

    def _load_records(self, object_type: str, records: list[dict[str, Any]]) -> None:
        """
        Persist transformed records to the Nexus CRM database.

        This is a stub that writes to JSON files. In production, this would
        call the Nexus application-layer services or repository interfaces.
        """
        os.makedirs(self.config.output_dir, exist_ok=True)
        output_path = os.path.join(
            self.config.output_dir, f"{object_type.lower()}_migrated.json"
        )

        # Process in batches for memory efficiency
        for i in range(0, len(records), self.config.batch_size):
            batch = records[i : i + self.config.batch_size]
            logger.info(
                "Loading %s batch %d-%d of %d",
                object_type,
                i,
                i + len(batch),
                len(records),
            )

        # Write full output for audit
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)

        logger.info("Wrote %d %s records to %s", len(records), object_type, output_path)

    # -------------------------------------------------------------------
    # Summary / reporting
    # -------------------------------------------------------------------

    def _save_summary(self) -> None:
        """Save migration summary to a JSON file."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        summary = {
            "dry_run": self.config.dry_run,
            "completed_at": datetime.now(UTC).isoformat(),
            "objects": {
                obj_type: prog.to_dict() for obj_type, prog in self.progress.items()
            },
            "id_mapping_counts": {
                obj_type: self.id_remapper.count(obj_type)
                for obj_type in self.MIGRATION_ORDER
            },
        }
        summary_path = os.path.join(self.config.output_dir, "migration_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info("Migration summary saved to %s", summary_path)

    def get_migrated_records(self, object_type: str) -> list[dict[str, Any]]:
        """Return the transformed records for an object type (useful in dry-run)."""
        return self._migrated_records.get(object_type, [])
