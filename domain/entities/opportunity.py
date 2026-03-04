"""
Opportunity Domain Entity

Architectural Intent:
- Core aggregate for sales pipeline bounded context
- Immutable state with stage transitions managed via domain methods
- Domain events emitted for stage changes

Key Design Decisions:
1. Opportunity is the primary revenue-tracking entity
2. Stage is managed as a state machine with valid transitions
3. Amount uses Money value object for currency handling
4. Close date is required for pipeline forecasting
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from domain.value_objects import Money
from domain.events import (
    DomainEvent,
    OpportunityCreatedEvent,
    OpportunityStageChangedEvent,
    OpportunityUpdatedEvent,
    OpportunityWonEvent,
    OpportunityLostEvent,
)


class OpportunityStage(Enum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    VALUE_PROPOSITION = "value_proposition"
    DECISION_MAKERS = "decision_makers"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


STAGE_ORDER = {
    OpportunityStage.PROSPECTING: 1,
    OpportunityStage.QUALIFICATION: 2,
    OpportunityStage.NEEDS_ANALYSIS: 3,
    OpportunityStage.VALUE_PROPOSITION: 4,
    OpportunityStage.DECISION_MAKERS: 5,
    OpportunityStage.PROPOSAL: 6,
    OpportunityStage.NEGOTIATION: 7,
    OpportunityStage.CLOSED_WON: 8,
    OpportunityStage.CLOSED_LOST: 0,
}

STAGE_PROBABILITIES = {
    OpportunityStage.PROSPECTING: 10,
    OpportunityStage.QUALIFICATION: 20,
    OpportunityStage.NEEDS_ANALYSIS: 30,
    OpportunityStage.VALUE_PROPOSITION: 40,
    OpportunityStage.DECISION_MAKERS: 50,
    OpportunityStage.PROPOSAL: 60,
    OpportunityStage.NEGOTIATION: 75,
    OpportunityStage.CLOSED_WON: 100,
    OpportunityStage.CLOSED_LOST: 0,
}


VALID_STAGE_TRANSITIONS = {
    OpportunityStage.PROSPECTING: {
        OpportunityStage.QUALIFICATION,
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.QUALIFICATION: {
        OpportunityStage.NEEDS_ANALYSIS,
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.NEEDS_ANALYSIS: {
        OpportunityStage.VALUE_PROPOSITION,
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.VALUE_PROPOSITION: {
        OpportunityStage.DECISION_MAKERS,
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.DECISION_MAKERS: {
        OpportunityStage.PROPOSAL,
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.PROPOSAL: {
        OpportunityStage.NEGOTIATION,
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.NEGOTIATION: {
        OpportunityStage.CLOSED_WON,
        OpportunityStage.CLOSED_LOST,
    },
    OpportunityStage.CLOSED_WON: set(),
    OpportunityStage.CLOSED_LOST: set(),
}


class OpportunitySource(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    REFERRAL = "referral"
    PARTNER = "partner"
    TRADE_SHOW = "trade_show"
    WEB = "web"
    OTHER = "other"


@dataclass(frozen=True)
class Opportunity:
    id: UUID
    account_id: UUID
    name: str
    stage: OpportunityStage
    amount: Money
    probability: int
    close_date: datetime
    owner_id: UUID
    contact_id: Optional[UUID] = None
    source: Optional[OpportunitySource] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: Optional[datetime] = None
    domain_events: tuple[DomainEvent, ...] = field(default_factory=tuple)

    @property
    def is_won(self) -> bool:
        return self.stage == OpportunityStage.CLOSED_WON

    @property
    def is_lost(self) -> bool:
        return self.stage == OpportunityStage.CLOSED_LOST

    @property
    def is_closed(self) -> bool:
        return self.is_won or self.is_lost

    @property
    def weighted_value(self) -> Money:
        multiplier = Decimal(self.probability) / Decimal(100)
        return Money(self.amount.amount * multiplier, self.amount.currency)

    @staticmethod
    def create(
        account_id: UUID,
        name: str,
        amount: Money,
        close_date: datetime,
        owner_id: UUID,
        source: Optional[OpportunitySource] = None,
        contact_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> "Opportunity":
        opportunity_id = uuid4()
        now = datetime.now(UTC)
        return Opportunity(
            id=opportunity_id,
            account_id=account_id,
            name=name,
            stage=OpportunityStage.PROSPECTING,
            amount=amount,
            probability=10,
            close_date=close_date,
            owner_id=owner_id,
            source=source,
            contact_id=contact_id,
            description=description,
            created_at=now,
            updated_at=now,
            domain_events=(
                OpportunityCreatedEvent(
                    aggregate_id=str(opportunity_id),
                    occurred_at=now,
                    opportunity_name=name,
                    account_id=str(account_id),
                    amount=amount.amount_float,
                ),
            ),
        )

    def change_stage(
        self, new_stage: OpportunityStage, reason: Optional[str] = None
    ) -> "Opportunity":
        if new_stage not in VALID_STAGE_TRANSITIONS.get(self.stage, set()):
            raise ValueError(
                f"Invalid stage transition from {self.stage.value} to {new_stage.value}"
            )

        now = datetime.now(UTC)
        events = list(self.domain_events)

        events.append(
            OpportunityStageChangedEvent(
                aggregate_id=str(self.id),
                occurred_at=now,
                old_stage=self.stage.value,
                new_stage=new_stage.value,
                amount=self.amount.amount_float,
            )
        )

        closed_at = (
            now
            if new_stage in (OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST)
            else None
        )

        if new_stage == OpportunityStage.CLOSED_WON:
            events.append(
                OpportunityWonEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    amount=self.amount.amount_float,
                )
            )
        elif new_stage == OpportunityStage.CLOSED_LOST:
            events.append(
                OpportunityLostEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                    amount=self.amount.amount_float,
                    reason=reason or "Not specified",
                )
            )

        return replace(
            self,
            stage=new_stage,
            probability=STAGE_PROBABILITIES.get(new_stage, self.probability),
            updated_at=now,
            closed_at=closed_at,
            domain_events=tuple(events),
        )

    def update(
        self,
        name: Optional[str] = None,
        amount: Optional[Money] = None,
        probability: Optional[int] = None,
        close_date: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> "Opportunity":
        now = datetime.now(UTC)
        return replace(
            self,
            name=name if name is not None else self.name,
            amount=amount if amount is not None else self.amount,
            probability=probability if probability is not None else self.probability,
            close_date=close_date if close_date is not None else self.close_date,
            description=description if description is not None else self.description,
            updated_at=now,
            domain_events=self.domain_events
            + (
                OpportunityUpdatedEvent(
                    aggregate_id=str(self.id),
                    occurred_at=now,
                ),
            ),
        )
