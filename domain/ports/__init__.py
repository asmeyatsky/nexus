"""
External Service Ports

Architectural Intent:
- Port interfaces for external services (Hexagonal Architecture)
- Defined in domain layer, implemented in infrastructure layer
- Protocol-based for dependency inversion
"""

from typing import Protocol, Optional, Any


class NotificationPort(Protocol):
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        template_id: Optional[str] = None,
    ) -> bool: ...

    async def send_sms(self, to: str, message: str) -> bool: ...


class EventBusPort(Protocol):
    async def publish(self, events: list[Any]) -> None: ...

    async def subscribe(self, event_type: str, handler: Any) -> None: ...


class AuthenticationPort(Protocol):
    async def authenticate(self, token: str) -> Optional[dict]: ...

    async def validate_permissions(
        self, user_id: str, resource: str, action: str
    ) -> bool: ...


class AuditLogPort(Protocol):
    async def log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict] = None,
    ) -> None: ...


class SearchPort(Protocol):
    async def index(
        self, document_type: str, document_id: str, content: dict
    ) -> None: ...

    async def search(
        self, query: str, filters: Optional[dict] = None
    ) -> list[dict]: ...
