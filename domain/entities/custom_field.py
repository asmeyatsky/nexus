"""
Custom Field Entity

Architectural Intent:
- User-defined fields on any entity
- Schema flexibility for enterprise customization
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, Any
from enum import Enum


class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    PICKLIST = "picklist"
    MULTI_PICKLIST = "multi_picklist"
    CURRENCY = "currency"
    URL = "url"
    EMAIL = "email"


@dataclass(frozen=True)
class CustomFieldDefinition:
    id: str
    name: str
    label: str
    field_type: FieldType
    entity_type: str
    org_id: str
    is_required: bool = False
    default_value: Optional[str] = None
    picklist_values: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        name: str,
        label: str,
        field_type: FieldType,
        entity_type: str,
        org_id: str,
        is_required: bool = False,
        default_value: Optional[str] = None,
        picklist_values: tuple[str, ...] = (),
    ) -> "CustomFieldDefinition":
        return CustomFieldDefinition(
            id=id,
            name=name,
            label=label,
            field_type=field_type,
            entity_type=entity_type,
            org_id=org_id,
            is_required=is_required,
            default_value=default_value,
            picklist_values=picklist_values,
        )


@dataclass(frozen=True)
class CustomFieldValue:
    id: str
    field_definition_id: str
    entity_id: str
    value: Any
    org_id: str
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
