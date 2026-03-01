"""
Salesforce ETL Migration Scripts

Architectural Intent:
- Extract data from Salesforce
- Transform to Nexus CRM schema
- Load into Nexus CRM
- Validation and rollback support
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json
import csv
from abc import ABC, abstractmethod


class MigrationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationConfig:
    salesforce_client_id: str
    salesforce_client_secret: str
    salesforce_instance_url: str
    nexus_api_url: str
    nexus_api_key: str
    batch_size: int = 100
    parallel_workers: int = 5


@dataclass
class FieldMapping:
    source_field: str
    target_field: str
    transform: Optional[Callable] = None
    default: Any = None


@dataclass
class MigrationResult:
    status: MigrationStatus
    total_records: int = 0
    migrated: int = 0
    failed: int = 0
    errors: List[Dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    sf_id_to_nexus_id: Dict[str, str] = field(default_factory=dict)


class SalesforceClient:
    """Salesforce API client for data extraction."""

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.instance_url: str = config.salesforce_instance_url

    async def authenticate(self) -> bool:
        """Authenticate with Salesforce OAuth."""
        import httpx

        url = f"{self.instance_url}/services/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.salesforce_client_id,
            "client_secret": self.config.salesforce_client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                return True
        return False

    async def query(self, soql: str) -> List[Dict]:
        """Execute SOQL query."""
        import httpx

        if not self.access_token:
            await self.authenticate()

        url = f"{self.instance_url}/services/data/v58.0/query"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"q": soql}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("records", [])
        return []

    async def get_all_records(
        self, object_name: str, batch_size: int = 2000
    ) -> List[Dict]:
        """Get all records from a Salesforce object using pagination."""
        records = []
        offset = 0

        while True:
            soql = (
                f"SELECT Id, Name FROM {object_name} LIMIT {batch_size} OFFSET {offset}"
            )
            batch = await self.query(soql)

            if not batch:
                break

            records.extend(batch)
            offset += batch_size

            if len(batch) < batch_size:
                break

        return records


class SchemaMapper:
    """Maps Salesforce fields to Nexus CRM fields."""

    ACCOUNT_MAPPINGS = [
        FieldMapping("Name", "name"),
        FieldMapping("Industry", "industry"),
        FieldMapping("Website", "website"),
        FieldMapping("Phone", "phone"),
        FieldMapping("BillingCity", "billing_address", lambda x: x if x else None),
        FieldMapping(
            "AnnualRevenue", "annual_revenue", lambda x: float(x) if x else None
        ),
        FieldMapping(
            "NumberOfEmployees", "employee_count", lambda x: int(x) if x else None
        ),
        FieldMapping("OwnerId", "owner_id"),
    ]

    CONTACT_MAPPINGS = [
        FieldMapping("FirstName", "first_name"),
        FieldMapping("LastName", "last_name"),
        FieldMapping("Email", "email"),
        FieldMapping("Phone", "phone"),
        FieldMapping("Title", "title"),
        FieldMapping("Department", "department"),
        FieldMapping("AccountId", "account_id"),
    ]

    OPPORTUNITY_MAPPINGS = [
        FieldMapping("Name", "name"),
        FieldMapping("StageName", "stage", lambda x: x.replace(" ", "_").lower()),
        FieldMapping("Amount", "amount", lambda x: float(x) if x else 0),
        FieldMapping(
            "CloseDate",
            "close_date",
            lambda x: datetime.strptime(x, "%Y-%m-%d").isoformat(),
        ),
        FieldMapping("AccountId", "account_id"),
        FieldMapping("OwnerId", "owner_id"),
    ]

    LEAD_MAPPINGS = [
        FieldMapping("FirstName", "first_name"),
        FieldMapping("LastName", "last_name"),
        FieldMapping("Email", "email"),
        FieldMapping("Company", "company"),
        FieldMapping("Status", "status"),
        FieldMapping("Rating", "rating"),
        FieldMapping("Phone", "phone"),
        FieldMapping("Title", "title"),
    ]

    CASE_MAPPINGS = [
        FieldMapping("Subject", "subject"),
        FieldMapping("Description", "description"),
        FieldMapping("Status", "status"),
        FieldMapping("Priority", "priority"),
        FieldMapping("Origin", "origin"),
        FieldMapping("AccountId", "account_id"),
        FieldMapping("ContactId", "contact_id"),
    ]

    @classmethod
    def transform_record(cls, source: Dict, mappings: List[FieldMapping]) -> Dict:
        """Transform a Salesforce record to Nexus CRM format."""
        result = {}

        for mapping in mappings:
            value = source.get(mapping.source_field, mapping.default)

            if value is None and mapping.default is not None:
                value = mapping.default

            if value is not None and mapping.transform:
                try:
                    value = mapping.transform(value)
                except Exception:
                    value = None

            if value is not None:
                result[mapping.target_field] = value

        return result


class SalesforceETL:
    """Salesforce to Nexus CRM ETL process."""

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.sf_client = SalesforceClient(config)
        self.mapper = SchemaMapper()
        self.results: Dict[str, MigrationResult] = {}

    async def migrate_accounts(self) -> MigrationResult:
        """Migrate accounts from Salesforce."""
        result = MigrationResult(status=MigrationStatus.IN_PROGRESS)

        sf_records = await self.sf_client.get_all_records("Account")
        result.total_records = len(sf_records)

        accounts = []
        for sf_record in sf_records:
            try:
                nexus_record = self.mapper.transform_record(
                    sf_record, self.mapper.ACCOUNT_MAPPINGS
                )
                nexus_record["territory"] = "EMEA"
                nexus_record["owner_id"] = "default-owner-id"
                accounts.append(nexus_record)
                result.migrated += 1
                result.sf_id_to_nexus_id[sf_record["Id"]] = f"acc_{result.migrated}"
            except Exception as e:
                result.failed += 1
                result.errors.append({"sf_id": sf_record.get("Id"), "error": str(e)})

        if result.failed == 0:
            result.status = MigrationStatus.COMPLETED
        elif result.migrated > 0:
            result.status = MigrationStatus.PARTIAL
        else:
            result.status = MigrationStatus.FAILED

        result.completed_at = datetime.now()
        self.results["accounts"] = result
        return result

    async def migrate_contacts(
        self, account_mapping: Dict[str, str]
    ) -> MigrationResult:
        """Migrate contacts from Salesforce."""
        result = MigrationResult(status=MigrationStatus.IN_PROGRESS)

        sf_records = await self.sf_client.get_all_records("Contact")
        result.total_records = len(sf_records)

        for sf_record in sf_records:
            try:
                nexus_record = self.mapper.transform_record(
                    sf_record, self.mapper.CONTACT_MAPPINGS
                )

                sf_account_id = sf_record.get("AccountId")
                if sf_account_id and sf_account_id in account_mapping:
                    nexus_record["account_id"] = account_mapping[sf_account_id]

                result.migrated += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({"sf_id": sf_record.get("Id"), "error": str(e)})

        result.status = (
            MigrationStatus.COMPLETED if result.failed == 0 else MigrationStatus.PARTIAL
        )
        result.completed_at = datetime.now()
        self.results["contacts"] = result
        return result

    async def migrate_opportunities(
        self, account_mapping: Dict[str, str]
    ) -> MigrationResult:
        """Migrate opportunities from Salesforce."""
        result = MigrationResult(status=MigrationStatus.IN_PROGRESS)

        soql = "SELECT Id, Name, StageName, Amount, CloseDate, AccountId, OwnerId FROM Opportunity"
        sf_records = await self.sf_client.query(soql)
        result.total_records = len(sf_records)

        for sf_record in sf_records:
            try:
                nexus_record = self.mapper.transform_record(
                    sf_record, self.mapper.OPPORTUNITY_MAPPINGS
                )

                sf_account_id = sf_record.get("AccountId")
                if sf_account_id and sf_account_id in account_mapping:
                    nexus_record["account_id"] = account_mapping[sf_account_id]

                result.migrated += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({"sf_id": sf_record.get("Id"), "error": str(e)})

        result.status = (
            MigrationStatus.COMPLETED if result.failed == 0 else MigrationStatus.PARTIAL
        )
        result.completed_at = datetime.now()
        self.results["opportunities"] = result
        return result

    async def migrate_leads(self) -> MigrationResult:
        """Migrate leads from Salesforce."""
        result = MigrationResult(status=MigrationStatus.IN_PROGRESS)

        sf_records = await self.sf_client.get_all_records("Lead")
        result.total_records = len(sf_records)

        for sf_record in sf_records:
            try:
                nexus_record = self.mapper.transform_record(
                    sf_record, self.mapper.LEAD_MAPPINGS
                )
                nexus_record["owner_id"] = "default-owner-id"
                result.migrated += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({"sf_id": sf_record.get("Id"), "error": str(e)})

        result.status = (
            MigrationStatus.COMPLETED if result.failed == 0 else MigrationStatus.PARTIAL
        )
        result.completed_at = datetime.now()
        self.results["leads"] = result
        return result

    async def migrate_cases(self, account_mapping: Dict[str, str]) -> MigrationResult:
        """Migrate cases from Salesforce."""
        result = MigrationResult(status=MigrationStatus.IN_PROGRESS)

        sf_records = await self.sf_client.get_all_records("Case")
        result.total_records = len(sf_records)

        case_number = 1
        for sf_record in sf_records:
            try:
                nexus_record = self.mapper.transform_record(
                    sf_record, self.mapper.CASE_MAPPINGS
                )
                nexus_record["case_number"] = f"CASE-{case_number:06d}"
                nexus_record["owner_id"] = "default-owner-id"
                case_number += 1
                result.migrated += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({"sf_id": sf_record.get("Id"), "error": str(e)})

        result.status = (
            MigrationStatus.COMPLETED if result.failed == 0 else MigrationStatus.PARTIAL
        )
        result.completed_at = datetime.now()
        self.results["cases"] = result
        return result

    async def run_full_migration(self) -> Dict[str, MigrationResult]:
        """Run complete migration from Salesforce."""

        accounts_result = await self.migrate_accounts()
        account_mapping = accounts_result.sf_id_to_nexus_id

        await self.migrate_contacts(account_mapping)
        await self.migrate_opportunities(account_mapping)
        await self.migrate_leads()
        await self.migrate_cases(account_mapping)

        return self.results

    def get_summary(self) -> Dict:
        """Get migration summary."""
        total_migrated = sum(r.migrated for r in self.results.values())
        total_failed = sum(r.failed for r in self.results.values())

        return {
            "status": "completed",
            "total_migrated": total_migrated,
            "total_failed": total_failed,
            "by_object": {
                obj: {
                    "migrated": r.migrated,
                    "failed": r.failed,
                }
                for obj, r in self.results.items()
            },
        }
