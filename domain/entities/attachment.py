"""
File Attachment Entity

Architectural Intent:
- File attachment support for any entity
- GCS-backed storage
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass(frozen=True)
class Attachment:
    id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    entity_type: str
    entity_id: str
    uploaded_by: str
    org_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self):
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be greater than 0")

    @staticmethod
    def create(
        id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_path: str,
        entity_type: str,
        entity_id: str,
        uploaded_by: str,
        org_id: str,
    ) -> "Attachment":
        return Attachment(
            id=id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            entity_type=entity_type,
            entity_id=entity_id,
            uploaded_by=uploaded_by,
            org_id=org_id,
        )
