"""
Infrastructure Adapters

Architectural Intent:
- Implementations of domain ports
- Adapters for external services (notification, event bus, etc.)
"""

from typing import Optional
from domain.ports import (
    NotificationPort,
    EventBusPort,
    AuditLogPort,
    AuthenticationPort,
)


class ConsoleNotificationAdapter(NotificationPort):
    """Adapter that logs notifications to console - for development."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        template_id: Optional[str] = None,
    ) -> bool:
        print(f"[EMAIL] To: {to}, Subject: {subject}")
        return True

    async def send_sms(self, to: str, message: str) -> bool:
        print(f"[SMS] To: {to}, Message: {message}")
        return True


class InMemoryEventBusAdapter(EventBusPort):
    """In-memory event bus adapter - for development/testing."""

    def __init__(self):
        self._handlers = {}

    async def publish(self, events: list) -> None:
        for event in events:
            event_type = type(event).__name__
            if event_type in self._handlers:
                for handler in self._handlers[event_type]:
                    await handler(event)

    async def subscribe(self, event_type: str, handler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)


class ConsoleAuditLogAdapter(AuditLogPort):
    """Adapter that logs to console - for development."""

    async def log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict] = None,
    ) -> None:
        print(
            f"[AUDIT] User: {user_id}, Action: {action}, Resource: {resource_type}/{resource_id}"
        )


class MockAuthenticationAdapter(AuthenticationPort):
    """Mock authentication adapter - for development."""

    async def authenticate(self, token: str) -> Optional[dict]:
        return {"user_id": "test-user", "email": "test@example.com"}

    async def validate_permissions(
        self, user_id: str, resource: str, action: str
    ) -> bool:
        return True
