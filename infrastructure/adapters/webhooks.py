"""
Webhooks System - SECURED

Architectural Intent:
- Event-driven integrations with third-party systems
- Configurable webhook endpoints
- Retry logic and delivery confirmation
- SSRF protection
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum
import asyncio
import hashlib
import hmac
import logging
import secrets
import time
import ipaddress
import httpx


logger = logging.getLogger(__name__)

# Maximum length for stored response body snippets (for debugging only)
_MAX_RESPONSE_BODY_LEN = 256


# Internal IP ranges to block for SSRF prevention
BLOCKED_IP_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "0.0.0.0/8",
    "100.64.0.0/10",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "fc00::/7",
    "fe80::/10",
    "::1/128",
]


def is_url_safe(url: str) -> tuple[bool, str]:
    """Validate URL to prevent SSRF attacks."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False, "Only HTTP and HTTPS are allowed"

        if parsed.hostname is None:
            return False, "Invalid URL"

        # Block internal IPs
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            for blocked in BLOCKED_IP_RANGES:
                if ip in ipaddress.ip_network(blocked):
                    return False, "Internal IPs are not allowed"
        except ValueError:
            # Hostname is not an IP -- resolve it to check for DNS rebinding
            import socket

            try:
                resolved_ips = socket.getaddrinfo(parsed.hostname, None)
                for _, _, _, _, addr in resolved_ips:
                    resolved_ip = ipaddress.ip_address(addr[0])
                    for blocked in BLOCKED_IP_RANGES:
                        if resolved_ip in ipaddress.ip_network(blocked):
                            return False, "Resolved IP is in blocked range"
            except socket.gaierror:
                return False, "Could not resolve hostname"

        # Block localhost variations
        if parsed.hostname.lower() in ("localhost", "localhost.localdomain"):
            return False, "Localhost is not allowed"

        # Block private/reserved domains
        if parsed.hostname.endswith(".internal"):
            return False, "Internal domains are not allowed"

        return True, "allowed"

    except Exception:
        return False, "URL validation error"


class WebhookEvent(Enum):
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_UPDATED = "account.updated"
    ACCOUNT_DELETED = "account.deleted"
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    OPPORTUNITY_CREATED = "opportunity.created"
    OPPORTUNITY_UPDATED = "opportunity.updated"
    OPPORTUNITY_STAGE_CHANGED = "opportunity.stage_changed"
    OPPORTUNITY_WON = "opportunity.won"
    OPPORTUNITY_LOST = "opportunity.lost"
    LEAD_CREATED = "lead.created"
    LEAD_QUALIFIED = "lead.qualified"
    LEAD_CONVERTED = "lead.converted"
    CASE_CREATED = "case.created"
    CASE_RESOLVED = "case.resolved"


@dataclass
class Webhook:
    id: str
    url: str
    events: List[WebhookEvent]
    secret: str
    org_id: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    failure_count: int = 0


@dataclass
class WebhookDelivery:
    id: str
    webhook_id: str
    event: WebhookEvent
    payload: Dict
    status: str
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    attempts: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None


class WebhookService:
    """Webhook management and delivery service."""

    def __init__(self):
        self._webhooks: Dict[str, Webhook] = {}
        self._deliveries: Dict[str, WebhookDelivery] = {}
        self._retry_delays = [5, 30, 120, 300]

    def create_webhook(
        self,
        url: str,
        events: List[WebhookEvent],
        org_id: str,
        secret: str = None,
    ) -> Optional[Webhook]:
        is_safe, reason = is_url_safe(url)
        if not is_safe:
            raise ValueError(f"URL validation failed: {reason}")

        webhook = Webhook(
            id=str(uuid4()),
            url=url,
            events=events,
            secret=secret or secrets.token_hex(32),
            org_id=org_id,
        )
        self._webhooks[webhook.id] = webhook
        return webhook

    def delete_webhook(self, webhook_id: str):
        self._webhooks.pop(webhook_id, None)

    def get_webhooks_for_event(self, event: WebhookEvent, org_id: str) -> List[Webhook]:
        return [
            w
            for w in self._webhooks.values()
            if w.is_active and event in w.events and w.org_id == org_id
        ]

    async def trigger(self, event: WebhookEvent, data: Dict[str, Any], org_id: str):
        webhooks = self.get_webhooks_for_event(event, org_id)

        payload = {
            "id": str(uuid4()),
            "type": event.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        for webhook in webhooks:
            asyncio.create_task(self._deliver(webhook, event, payload))

    async def _deliver(self, webhook: Webhook, event: WebhookEvent, payload: Dict):
        delivery_id = str(uuid4())

        timestamp = str(int(time.time()))
        signature = self._generate_signature(payload, webhook.secret, timestamp)

        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event=event,
            payload=payload,
            status="pending",
        )
        self._deliveries[delivery_id] = delivery

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Event": event.value,
            "X-Webhook-Delivery": delivery_id,
        }

        # Validate URL before making request (SSRF protection)
        is_safe, reason = is_url_safe(webhook.url)
        if not is_safe:
            delivery.status = "failed"
            delivery.response_body = "URL validation failed"
            return

        for attempt in range(len(self._retry_delays) + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=30, follow_redirects=False
                ) as client:
                    response = await client.post(
                        webhook.url, json=payload, headers=headers
                    )

                    delivery.response_code = response.status_code
                    # Truncate response body to prevent storing large/sensitive payloads
                    delivery.response_body = (
                        response.text[:_MAX_RESPONSE_BODY_LEN]
                        if response.text
                        else None
                    )
                    delivery.attempts = attempt + 1

                    if 200 <= response.status_code < 300:
                        delivery.status = "delivered"
                        delivery.delivered_at = datetime.now()
                        webhook.last_triggered = datetime.now()
                        webhook.failure_count = 0
                        break
                    else:
                        delivery.status = "failed"

            except Exception:
                delivery.status = "failed"
                delivery.response_body = "Delivery failed due to a connection error"
                delivery.attempts = attempt + 1

            if attempt < len(self._retry_delays):
                await asyncio.sleep(self._retry_delays[attempt])

        if delivery.status == "failed":
            webhook.failure_count += 1
            if webhook.failure_count >= 10:
                webhook.is_active = False

    def _generate_signature(
        self, payload: Dict, secret: str, timestamp: str = ""
    ) -> str:
        import json

        body = json.dumps(payload, sort_keys=True)
        # Include timestamp in signature to prevent replay attacks
        message = f"{timestamp}.{body}" if timestamp else body
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256)
        return signature.hexdigest()

    def get_delivery_status(self, delivery_id: str) -> Optional[Dict]:
        delivery = self._deliveries.get(delivery_id)
        if not delivery:
            return None

        return {
            "id": delivery.id,
            "webhook_id": delivery.webhook_id,
            "event": delivery.event.value,
            "status": delivery.status,
            "response_code": delivery.response_code,
            "attempts": delivery.attempts,
            "created_at": delivery.created_at.isoformat(),
            "delivered_at": delivery.delivered_at.isoformat()
            if delivery.delivered_at
            else None,
        }


webhook_service = WebhookService()
