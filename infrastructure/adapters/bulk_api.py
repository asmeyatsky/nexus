"""
Bulk API for Data Migration

Architectural Intent:
- Bulk import/export operations
- Async processing for large datasets
- Progress tracking and resumability
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum
import asyncio
import csv
import io


class BulkOperationType(Enum):
    IMPORT = "import"
    EXPORT = "export"
    UPDATE = "update"
    DELETE = "delete"


class BulkStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BulkJob:
    id: str
    operation: BulkOperationType
    entity_type: str
    status: BulkStatus
    total_records: int = 0
    processed_records: int = 0
    success_records: int = 0
    failed_records: int = 0
    errors: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    created_by: str = ""
    org_id: str = ""
    file_url: Optional[str] = None
    result_url: Optional[str] = None


class BulkAPI:
    """Bulk API for large-scale data operations."""

    def __init__(self):
        self._jobs: Dict[str, BulkJob] = {}
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, entity_type: str, handler: Callable):
        self._handlers[entity_type] = handler

    async def create_job(
        self,
        operation: BulkOperationType,
        entity_type: str,
        created_by: str,
        org_id: str,
        file_url: str = None,
    ) -> BulkJob:
        job = BulkJob(
            id=str(uuid4()),
            operation=operation,
            entity_type=entity_type,
            status=BulkStatus.PENDING,
            created_by=created_by,
            org_id=org_id,
            file_url=file_url,
        )
        self._jobs[job.id] = job
        return job

    async def process_job(
        self,
        job_id: str,
        records: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> BulkJob:
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = BulkStatus.PROCESSING
        job.total_records = len(records)

        handler = self._handlers.get(job.entity_type)
        if not handler:
            job.status = BulkStatus.FAILED
            job.errors.append({"error": f"No handler for {job.entity_type}"})
            return job

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            for record in batch:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(record)
                    else:
                        handler(record)

                    job.success_records += 1
                except Exception as e:
                    job.failed_records += 1
                    job.errors.append(
                        {
                            "record": record.get("id", "unknown"),
                            "error": str(e),
                        }
                    )

                job.processed_records += 1

            await asyncio.sleep(0.1)

        if job.failed_records == 0:
            job.status = BulkStatus.COMPLETED
        elif job.success_records > 0:
            job.status = BulkStatus.PARTIAL
        else:
            job.status = BulkStatus.FAILED

        job.completed_at = datetime.now()
        return job

    def get_job(self, job_id: str) -> Optional[Dict]:
        job = self._jobs.get(job_id)
        if not job:
            return None

        return {
            "id": job.id,
            "operation": job.operation.value,
            "entity_type": job.entity_type,
            "status": job.status.value,
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "success_records": job.success_records,
            "failed_records": job.failed_records,
            "errors": job.errors[:100],
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "progress": job.processed_records / job.total_records
            if job.total_records > 0
            else 0,
        }

    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(csv_content))
        return [dict(row) for row in reader]

    def generate_csv(self, records: List[Dict[str, Any]]) -> str:
        if not records:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()


bulk_api = BulkAPI()


async def bulk_import_accounts_handler(
    record: Dict[str, Any], repository=None
) -> Dict:
    """Handler for bulk importing accounts.

    Args:
        record: The account record data to import.
        repository: An optional account repository instance. If not provided,
            a new InMemoryAccountRepository is created (for backwards compat).
    """
    from domain import Account, Industry, Territory
    from uuid import UUID

    if repository is None:
        from infrastructure.mcp_servers.nexus_crm_server import InMemoryAccountRepository

        repository = InMemoryAccountRepository()

    account = Account.create(
        name=record.get("name", ""),
        industry=Industry.from_string(record.get("industry", "other")),
        territory=Territory(region=record.get("territory", "EMEA")),
        owner_id=UUID(record.get("owner_id", str(uuid4()))),
        website=record.get("website"),
    )

    await repository.save(account)
    return {"id": str(account.id), "name": account.name}


bulk_api.register_handler("account", bulk_import_accounts_handler)
