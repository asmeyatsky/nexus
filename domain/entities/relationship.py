"""
Relationship Mapping Entity

Architectural Intent:
- Map relationships between accounts and contacts
- Influence mapping for sales strategy
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum


class RelationshipType(Enum):
    PARTNER = "partner"
    COMPETITOR = "competitor"
    SUBSIDIARY = "subsidiary"
    VENDOR = "vendor"
    INFLUENCER = "influencer"
    DECISION_MAKER = "decision_maker"
    CHAMPION = "champion"


@dataclass(frozen=True)
class Relationship:
    id: str
    from_entity_type: str
    from_entity_id: str
    to_entity_type: str
    to_entity_id: str
    relationship_type: RelationshipType
    strength: int  # 1-10
    org_id: str
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        from_entity_type: str,
        from_entity_id: str,
        to_entity_type: str,
        to_entity_id: str,
        relationship_type: RelationshipType,
        strength: int,
        org_id: str,
        notes: str = "",
    ) -> "Relationship":
        if not 1 <= strength <= 10:
            raise ValueError("Relationship strength must be between 1 and 10")
        return Relationship(
            id=id,
            from_entity_type=from_entity_type,
            from_entity_id=from_entity_id,
            to_entity_type=to_entity_type,
            to_entity_id=to_entity_id,
            relationship_type=relationship_type,
            strength=strength,
            org_id=org_id,
            notes=notes,
        )
