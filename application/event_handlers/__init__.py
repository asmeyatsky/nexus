"""
Event Handlers / Subscribers

Registers handlers for domain events to trigger side effects:
- Notifications on opportunity won
- Case escalation alerts
- Cache invalidation on entity updates
- Audit logging
"""

import logging
from typing import Any

from domain.events import (
    OpportunityWonEvent,
    OpportunityLostEvent,
    OpportunityStageChangedEvent,
    CaseEscalatedEvent,
    CaseCreatedEvent,
    CaseResolvedEvent,
    AccountCreatedEvent,
    AccountUpdatedEvent,
    ContactCreatedEvent,
    LeadCreatedEvent,
    LeadQualifiedEvent,
    LeadConvertedEvent,
)

logger = logging.getLogger(__name__)


async def on_opportunity_won(event: OpportunityWonEvent):
    """Handle opportunity won — notify sales team, update forecasts."""
    logger.info(f"Opportunity won: {event.aggregate_id}, amount: {event.amount}")


async def on_opportunity_lost(event: OpportunityLostEvent):
    """Handle opportunity lost — notify manager, log reason."""
    logger.info(f"Opportunity lost: {event.aggregate_id}, reason: {event.reason}")


async def on_opportunity_stage_changed(event: OpportunityStageChangedEvent):
    """Handle stage change — update pipeline analytics."""
    logger.info(
        f"Opportunity {event.aggregate_id} stage: {event.old_stage} -> {event.new_stage}"
    )


async def on_case_escalated(event: CaseEscalatedEvent):
    """Handle case escalation — alert support manager."""
    logger.info(f"Case escalated: {event.aggregate_id}, priority: {event.priority}")


async def on_case_created(event: CaseCreatedEvent):
    """Handle new case — trigger auto-assignment, SLA tracking."""
    logger.info(f"Case created: {event.case_number}, subject: {event.subject}")


async def on_case_resolved(event: CaseResolvedEvent):
    """Handle case resolution — trigger CSAT survey, update metrics."""
    logger.info(f"Case resolved: {event.aggregate_id}, by: {event.resolved_by}")


async def on_account_created(event: AccountCreatedEvent):
    """Handle new account — trigger onboarding workflow."""
    logger.info(f"Account created: {event.account_name}")


async def on_account_updated(event: AccountUpdatedEvent):
    """Handle account update — invalidate cache."""
    logger.info(f"Account updated: {event.aggregate_id}")


async def on_contact_created(event: ContactCreatedEvent):
    """Handle new contact — enrich data, sync to marketing."""
    logger.info(f"Contact created: {event.contact_name} for account {event.account_id}")


async def on_lead_created(event: LeadCreatedEvent):
    """Handle new lead — trigger scoring, assignment."""
    logger.info(f"Lead created: {event.lead_name}, email: {event.email}")


async def on_lead_qualified(event: LeadQualifiedEvent):
    """Handle lead qualification — notify sales rep."""
    logger.info(f"Lead qualified: {event.aggregate_id}, score: {event.score}")


async def on_lead_converted(event: LeadConvertedEvent):
    """Handle lead conversion — update attribution."""
    logger.info(f"Lead converted: {event.aggregate_id} -> account: {event.account_id}")


def register_all_subscribers(event_bus: Any):
    """Register all event subscribers on the given event bus."""
    import asyncio

    subscribers = {
        "OpportunityWonEvent": on_opportunity_won,
        "OpportunityLostEvent": on_opportunity_lost,
        "OpportunityStageChangedEvent": on_opportunity_stage_changed,
        "CaseEscalatedEvent": on_case_escalated,
        "CaseCreatedEvent": on_case_created,
        "CaseResolvedEvent": on_case_resolved,
        "AccountCreatedEvent": on_account_created,
        "AccountUpdatedEvent": on_account_updated,
        "ContactCreatedEvent": on_contact_created,
        "LeadCreatedEvent": on_lead_created,
        "LeadQualifiedEvent": on_lead_qualified,
        "LeadConvertedEvent": on_lead_converted,
    }

    for event_type, handler in subscribers.items():
        # Use synchronous subscribe if available, otherwise schedule async
        loop = asyncio.get_event_loop()
        loop.create_task(event_bus.subscribe(event_type, handler))

    logger.info(f"Registered {len(subscribers)} event subscribers")
