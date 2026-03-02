"""
Google Workspace Integration

Architectural Intent:
- Gmail, Calendar, Drive sync
- Contact and event auto-capture
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


@dataclass
class GmailMessage:
    id: str
    subject: str
    sender: str
    recipients: List[str]
    body: str
    date: str
    thread_id: str


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: str
    end: str
    attendees: List[str]
    location: Optional[str] = None


async def _retry_with_backoff(
    coro_factory, operation_name: str, max_retries: int = MAX_RETRIES
):
    """Execute an async operation with exponential backoff retry logic.

    Args:
        coro_factory: A callable that returns a new coroutine on each call.
        operation_name: Human-readable name for logging.
        max_retries: Maximum number of retry attempts.

    Returns:
        The result of the coroutine on success.

    Raises:
        The last exception encountered after all retries are exhausted.
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Google Workspace %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Google Workspace %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class GoogleWorkspaceAdapter:
    """Google Workspace integration for Gmail, Calendar, Drive."""

    def __init__(self, credentials: Dict[str, Any] = None):
        self._credentials = credentials
        self._client = None
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that required credentials are present."""
        if not self._credentials:
            logger.warning(
                "GoogleWorkspaceAdapter initialized without credentials. "
                "Integration will operate in degraded mode (returning empty results)."
            )
            self._configured = False
            return

        required_keys = ["client_id", "client_secret"]
        missing = [k for k in required_keys if k not in self._credentials]
        if missing:
            logger.warning(
                "Google Workspace credentials missing keys: %s. "
                "Some operations may fail.",
                ", ".join(missing),
            )
            self._configured = False
        else:
            self._configured = True
            logger.info("GoogleWorkspaceAdapter configured successfully.")

    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """Initialize with OAuth2 credentials."""
        self._credentials = credentials
        self._validate_configuration()

    async def list_emails(
        self, user_email: str, query: str = "", max_results: int = 50
    ) -> List[GmailMessage]:
        """List emails matching query.

        Returns an empty list when credentials are not configured or on failure.
        """
        if not self._configured:
            logger.debug(
                "list_emails called without valid credentials; returning empty list."
            )
            return []

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                        params={"q": query, "maxResults": max_results},
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "list_emails")
            messages = []
            for msg in data.get("messages", []):
                messages.append(
                    GmailMessage(
                        id=msg.get("id", ""),
                        subject=msg.get("subject", ""),
                        sender=msg.get("from", ""),
                        recipients=msg.get("to", "").split(",")
                        if msg.get("to")
                        else [],
                        body=msg.get("snippet", ""),
                        date=msg.get("date", ""),
                        thread_id=msg.get("threadId", ""),
                    )
                )
            return messages
        except ImportError:
            logger.error("httpx is not installed. Cannot make HTTP requests for Gmail.")
            return []
        except Exception as exc:
            logger.error("Failed to list emails for %s: %s", user_email, exc)
            return []

    async def list_calendar_events(
        self, user_email: str, time_min: str = None, time_max: str = None
    ) -> List[CalendarEvent]:
        """List calendar events in range.

        Returns an empty list when credentials are not configured or on failure.
        """
        if not self._configured:
            logger.debug(
                "list_calendar_events called without valid credentials; returning empty list."
            )
            return []

        try:
            import httpx

            params = {}
            if time_min:
                params["timeMin"] = time_min
            if time_max:
                params["timeMax"] = time_max

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                        params=params,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "list_calendar_events")
            events = []
            for item in data.get("items", []):
                events.append(
                    CalendarEvent(
                        id=item.get("id", ""),
                        title=item.get("summary", ""),
                        start=item.get("start", {}).get("dateTime", ""),
                        end=item.get("end", {}).get("dateTime", ""),
                        attendees=[
                            a.get("email", "") for a in item.get("attendees", [])
                        ],
                        location=item.get("location"),
                    )
                )
            return events
        except ImportError:
            logger.error(
                "httpx is not installed. Cannot make HTTP requests for Calendar."
            )
            return []
        except Exception as exc:
            logger.error("Failed to list calendar events for %s: %s", user_email, exc)
            return []

    async def sync_contacts(self, user_email: str, org_id: str) -> Dict[str, int]:
        """Sync Google contacts to CRM contacts.

        Returns sync statistics. Returns zeroed stats on failure.
        """
        result = {"created": 0, "updated": 0, "skipped": 0}
        if not self._configured:
            logger.debug(
                "sync_contacts called without valid credentials; skipping sync."
            )
            return result

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        "https://people.googleapis.com/v1/people/me/connections",
                        params={"personFields": "names,emailAddresses,organizations"},
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "sync_contacts")
            connections = data.get("connections", [])
            logger.info(
                "Retrieved %d Google contacts for org %s", len(connections), org_id
            )
            # Actual sync logic would process connections here
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot sync contacts.")
            return result
        except Exception as exc:
            logger.error("Failed to sync contacts for org %s: %s", org_id, exc)
            return result

    async def capture_email_activity(
        self, message: GmailMessage, contact_email: str, org_id: str
    ) -> Dict:
        """Auto-capture email as CRM activity.

        Always returns an activity dict, even on partial failure, to ensure
        activity tracking is never silently lost.
        """
        try:
            activity = {
                "activity_type": "email",
                "subject": message.subject,
                "contact_email": contact_email,
                "message_id": message.id,
                "thread_id": message.thread_id,
                "date": message.date,
                "org_id": org_id,
            }
            logger.info(
                "Captured email activity for contact %s in org %s: %s",
                contact_email,
                org_id,
                message.subject,
            )
            return activity
        except Exception as exc:
            logger.error(
                "Failed to capture email activity for %s: %s", contact_email, exc
            )
            return {
                "activity_type": "email",
                "subject": getattr(message, "subject", ""),
                "contact_email": contact_email,
                "error": str(exc),
            }

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers from stored credentials."""
        token = self._credentials.get("access_token", "") if self._credentials else ""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
