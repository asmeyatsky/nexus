"""
Pipeline Entity

Architectural Intent:
- Multi-pipeline support for different sales processes
- Configurable stages per pipeline
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import List


@dataclass(frozen=True)
class PipelineStage:
    name: str
    order: int
    probability: int  # 0-100
    is_closed: bool = False
    is_won: bool = False

    def __post_init__(self):
        if self.is_won and not self.is_closed:
            raise ValueError(
                "A won stage must also be closed (is_won=True requires is_closed=True)"
            )


@dataclass(frozen=True)
class Pipeline:
    id: str
    name: str
    stages: tuple[PipelineStage, ...]
    is_default: bool
    is_active: bool
    org_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        name: str,
        stages: List[PipelineStage],
        org_id: str,
        is_default: bool = False,
    ) -> "Pipeline":
        return Pipeline(
            id=id,
            name=name,
            stages=tuple(stages),
            is_default=is_default,
            is_active=True,
            org_id=org_id,
        )

    @staticmethod
    def default_stages() -> List[PipelineStage]:
        return [
            PipelineStage("Prospecting", 1, 10),
            PipelineStage("Qualification", 2, 20),
            PipelineStage("Needs Analysis", 3, 40),
            PipelineStage("Proposal", 4, 60),
            PipelineStage("Negotiation", 5, 80),
            PipelineStage("Closed Won", 6, 100, is_closed=True, is_won=True),
            PipelineStage("Closed Lost", 7, 0, is_closed=True),
        ]
