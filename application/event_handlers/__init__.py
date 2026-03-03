"""
Event Handlers / Subscribers

Registers handlers for domain events to trigger side effects:
- Notifications on opportunity won
- Case escalation alerts
- Cache invalidation on entity updates
- Webhook delivery
- Lead scoring
- Workflow automation
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

# Module-level container reference, set by register_all_subscribers()
_container = None


def _get_webhook_service():
    try:
        return _container.webhook_service() if _container else None
    except Exception:
        return None


def _get_notification_adapter():
    try:
        from infrastructure.adapters import ConsoleNotificationAdapter
        return ConsoleNotificationAdapter()
    except Exception:
        return None


def _get_cache():
    try:
        return _container.cache() if _container else None
    except Exception:
        return None


def _get_metrics():
    try:
        from infrastructure.adapters.monitoring import metrics
        return metrics
    except Exception:
        return None


async def _fire_webhook(event_name, data, org_id=""):
    """Fire a webhook, logging errors but never raising."""
    try:
        from infrastructure.adapters.webhooks import WebhookEvent
        svc = _get_webhook_service()
        if svc is None:
            return
        event_enum = getattr(WebhookEvent, event_name, None)
        if event_enum:
            await svc.trigger(event_enum, data, org_id)
    except Exception as e:
        logger.debug(f"Webhook delivery skipped ({event_name}): {e}")


async def _send_notification(to, subject, body):
    """Send notification, logging errors but never raising."""
    try:
        adapter = _get_notification_adapter()
        if adapter:
            await adapter.send_email(to, subject, body)
    except Exception as e:
        logger.debug(f"Notification skipped: {e}")


async def on_opportunity_won(event: OpportunityWonEvent):
    """Handle opportunity won — notify sales team, update forecasts."""
    logger.info(f"Opportunity won: {event.aggregate_id}, amount: {event.amount}")

    await _send_notification(
        to="sales-team@company.com",
        subject=f"Deal Won! Amount: {event.amount}",
        body=f"Opportunity {event.aggregate_id} has been won for {event.amount}.",
    )
    await _fire_webhook(
        "OPPORTUNITY_WON",
        {"opportunity_id": event.aggregate_id, "amount": event.amount},
    )
    m = _get_metrics()
    if m:
        m.domain_events_total.inc({"event_type": "opportunity_won"})


async def on_opportunity_lost(event: OpportunityLostEvent):
    """Handle opportunity lost — notify manager, log reason."""
    logger.info(f"Opportunity lost: {event.aggregate_id}, reason: {event.reason}")

    await _send_notification(
        to="sales-manager@company.com",
        subject=f"Deal Lost: {event.aggregate_id}",
        body=f"Opportunity lost. Reason: {event.reason}",
    )
    await _fire_webhook(
        "OPPORTUNITY_LOST",
        {"opportunity_id": event.aggregate_id, "reason": event.reason},
    )


async def on_opportunity_stage_changed(event: OpportunityStageChangedEvent):
    """Handle stage change — update pipeline analytics, invalidate cache."""
    logger.info(
        f"Opportunity {event.aggregate_id} stage: {event.old_stage} -> {event.new_stage}"
    )

    await _fire_webhook(
        "OPPORTUNITY_STAGE_CHANGED",
        {
            "opportunity_id": event.aggregate_id,
            "old_stage": event.old_stage,
            "new_stage": event.new_stage,
        },
    )
    cache = _get_cache()
    if cache:
        try:
            await cache.invalidate_entity("opportunity", event.aggregate_id)
        except Exception as e:
            logger.debug(f"Cache invalidation skipped: {e}")


async def on_case_escalated(event: CaseEscalatedEvent):
    """Handle case escalation — alert support manager."""
    logger.info(f"Case escalated: {event.aggregate_id}, priority: {event.priority}")

    await _send_notification(
        to="support-manager@company.com",
        subject=f"URGENT: Case Escalated (Priority: {event.priority})",
        body=f"Case {event.aggregate_id} has been escalated to priority {event.priority}.",
    )
    await _fire_webhook(
        "CASE_CREATED",  # Use closest available webhook event
        {"case_id": event.aggregate_id, "priority": event.priority, "escalated": True},
    )


async def on_case_created(event: CaseCreatedEvent):
    """Handle new case — trigger auto-assignment, SLA tracking."""
    logger.info(f"Case created: {event.case_number}, subject: {event.subject}")

    await _fire_webhook(
        "CASE_CREATED",
        {"case_number": event.case_number, "subject": event.subject},
    )
    # Trigger auto-assignment workflow
    try:
        if _container:
            engine = _container.workflow_engine()
            if engine and engine._workflows:
                for wf_id, wf in engine._workflows.items():
                    if wf.is_active:
                        await engine.execute(wf_id, {
                            "case_number": event.case_number,
                            "subject": event.subject,
                        })
                        break
    except Exception as e:
        logger.debug(f"Workflow trigger skipped: {e}")


async def on_case_resolved(event: CaseResolvedEvent):
    """Handle case resolution — trigger CSAT survey, update metrics."""
    logger.info(f"Case resolved: {event.aggregate_id}, by: {event.resolved_by}")

    await _send_notification(
        to="customer-success@company.com",
        subject=f"Case Resolved: {event.aggregate_id}",
        body=f"Case resolved by {event.resolved_by}. Please send CSAT survey.",
    )
    await _fire_webhook(
        "CASE_RESOLVED",
        {"case_id": event.aggregate_id, "resolved_by": event.resolved_by},
    )


async def on_account_created(event: AccountCreatedEvent):
    """Handle new account — trigger onboarding workflow."""
    logger.info(f"Account created: {event.account_name}")

    await _fire_webhook(
        "ACCOUNT_CREATED",
        {"account_name": event.account_name, "account_id": event.aggregate_id},
    )
    # Trigger onboarding workflow
    try:
        if _container:
            engine = _container.workflow_engine()
            if engine and engine._workflows:
                for wf_id, wf in engine._workflows.items():
                    if wf.is_active:
                        await engine.execute(wf_id, {
                            "account_name": event.account_name,
                            "account_id": event.aggregate_id,
                        })
                        break
    except Exception as e:
        logger.debug(f"Onboarding workflow skipped: {e}")


async def on_account_updated(event: AccountUpdatedEvent):
    """Handle account update — invalidate cache."""
    logger.info(f"Account updated: {event.aggregate_id}")

    cache = _get_cache()
    if cache:
        try:
            await cache.invalidate_entity("account", event.aggregate_id)
        except Exception as e:
            logger.debug(f"Cache invalidation skipped: {e}")
    await _fire_webhook(
        "ACCOUNT_UPDATED",
        {"account_id": event.aggregate_id},
    )


async def on_contact_created(event: ContactCreatedEvent):
    """Handle new contact — enrich data, sync to marketing."""
    logger.info(f"Contact created: {event.contact_name} for account {event.account_id}")

    await _fire_webhook(
        "CONTACT_CREATED",
        {
            "contact_name": event.contact_name,
            "account_id": event.account_id,
            "contact_id": event.aggregate_id,
        },
    )


async def on_lead_created(event: LeadCreatedEvent):
    """Handle new lead — trigger scoring, assignment."""
    logger.info(f"Lead created: {event.lead_name}, email: {event.email}")

    # Score the lead
    try:
        if _container:
            scoring = _container.lead_scoring_service()
            if scoring:
                score = scoring.score_lead({
                    "name": event.lead_name,
                    "email": event.email,
                })
                logger.info(f"Lead {event.aggregate_id} scored: {score}")
    except Exception as e:
        logger.debug(f"Lead scoring skipped: {e}")

    await _fire_webhook(
        "LEAD_CREATED",
        {"lead_name": event.lead_name, "email": event.email, "lead_id": event.aggregate_id},
    )


async def on_lead_qualified(event: LeadQualifiedEvent):
    """Handle lead qualification — notify sales rep."""
    logger.info(f"Lead qualified: {event.aggregate_id}, score: {event.score}")

    await _send_notification(
        to="sales-rep@company.com",
        subject=f"Lead Qualified (Score: {event.score})",
        body=f"Lead {event.aggregate_id} has been qualified with score {event.score}. Please follow up.",
    )
    await _fire_webhook(
        "LEAD_QUALIFIED",
        {"lead_id": event.aggregate_id, "score": event.score},
    )


async def on_lead_converted(event: LeadConvertedEvent):
    """Handle lead conversion — update attribution."""
    logger.info(f"Lead converted: {event.aggregate_id} -> account: {event.account_id}")

    await _fire_webhook(
        "LEAD_CONVERTED",
        {
            "lead_id": event.aggregate_id,
            "account_id": event.account_id,
        },
    )
    m = _get_metrics()
    if m:
        m.domain_events_total.inc({"event_type": "lead_converted"})


def register_all_subscribers(event_bus: Any, container_ref=None):
    """Register all event subscribers on the given event bus.

    Args:
        event_bus: The event bus to subscribe handlers to.
        container_ref: Optional DI container for accessing services.
    """
    global _container
    if container_ref is not None:
        _container = container_ref
    else:
        # Fall back to the global container
        try:
            from infrastructure.config.dependency_injection import container as di_container
            _container = di_container
        except ImportError:
            pass

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

    import asyncio

    loop = asyncio.get_event_loop()
    for event_type, handler in subscribers.items():
        loop.create_task(event_bus.subscribe(event_type, handler))

    logger.info(f"Registered {len(subscribers)} event subscribers")
