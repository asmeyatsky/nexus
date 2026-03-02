"""
Jira/Asana Integration

Architectural Intent:
- Project tracking integration
- Bi-directional issue sync
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


async def _retry_with_backoff(
    coro_factory, operation_name: str, max_retries: int = MAX_RETRIES
):
    """Execute an async operation with exponential backoff retry logic."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Jira %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Jira %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class JiraAdapter:
    """Jira integration for project tracking."""

    def __init__(self, base_url: str = "", api_token: str = "", email: str = ""):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_token = api_token
        self.email = email
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that required Jira configuration is present."""
        if not self.base_url:
            logger.warning(
                "JiraAdapter initialized without base_url. "
                "Operations will return mock/empty results."
            )
            self._configured = False
            return

        missing = []
        if not self.api_token:
            missing.append("api_token")
        if not self.email:
            missing.append("email")

        if missing:
            logger.warning(
                "JiraAdapter missing configuration: %s. "
                "API calls will likely fail authentication.",
                ", ".join(missing),
            )
            # Still mark configured so we attempt calls (base_url is set)
            self._configured = True
        else:
            self._configured = True
            logger.info("JiraAdapter configured for %s.", self.base_url)

    def _auth_headers(self) -> Dict[str, str]:
        """Build basic auth headers for Jira Cloud API."""
        import base64

        credentials = base64.b64encode(
            f"{self.email}:{self.api_token}".encode()
        ).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_issue(
        self, project_key: str, summary: str, description: str, issue_type: str = "Task"
    ) -> Optional[str]:
        """Create a Jira issue.

        Returns the issue key (e.g. 'PROJ-123') on success, or a mock key
        when not configured. Returns None on failure.
        """
        if not self._configured:
            logger.info(
                "[Jira Offline] Would create %s in %s: %s",
                issue_type,
                project_key,
                summary,
            )
            return f"MOCK-{project_key}-1"

        try:
            import httpx

            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": description}],
                            }
                        ],
                    },
                    "issuetype": {"name": issue_type},
                }
            }

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/rest/api/3/issue",
                        json=payload,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"create_issue({project_key})"
            )
            issue_key = data.get("key")
            logger.info("Created Jira issue %s: %s", issue_key, summary)
            return issue_key
        except ImportError:
            logger.error("httpx is not installed. Cannot create Jira issue.")
            return None
        except Exception as exc:
            logger.error("Failed to create Jira issue in %s: %s", project_key, exc)
            return None

    async def link_case_to_issue(
        self, case_id: str, issue_key: str, org_id: str
    ) -> Dict:
        """Link a CRM case to a Jira issue.

        This is a local CRM linkage operation. Returns linkage metadata.
        """
        try:
            result = {
                "case_id": case_id,
                "issue_key": issue_key,
                "org_id": org_id,
                "linked": True,
            }
            logger.info(
                "Linked CRM case %s to Jira issue %s in org %s",
                case_id,
                issue_key,
                org_id,
            )
            return result
        except Exception as exc:
            logger.error(
                "Failed to link case %s to issue %s: %s",
                case_id,
                issue_key,
                exc,
            )
            return {
                "case_id": case_id,
                "issue_key": issue_key,
                "linked": False,
                "error": str(exc),
            }

    async def sync_status(self, issue_key: str) -> Optional[str]:
        """Get current status of a Jira issue.

        Returns the status name (e.g. 'In Progress') or None on failure.
        """
        if not self._configured:
            logger.debug(
                "sync_status called without valid configuration; returning None."
            )
            return None

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        f"{self.base_url}/rest/api/3/issue/{issue_key}",
                        headers=self._auth_headers(),
                        params={"fields": "status"},
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, f"sync_status({issue_key})")
            status = data.get("fields", {}).get("status", {}).get("name")
            logger.info("Jira issue %s status: %s", issue_key, status)
            return status
        except ImportError:
            logger.error("httpx is not installed. Cannot sync Jira issue status.")
            return None
        except Exception as exc:
            logger.error("Failed to get status for %s: %s", issue_key, exc)
            return None


class AsanaAdapter:
    """Asana integration for project tracking."""

    def __init__(self, access_token: str = ""):
        self.access_token = access_token
        self.base_url = "https://app.asana.com/api/1.0"
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that the access token is present."""
        if not self.access_token:
            logger.warning(
                "AsanaAdapter initialized without access_token. "
                "Task operations will return empty results."
            )
            self._configured = False
        else:
            self._configured = True
            logger.info("AsanaAdapter configured successfully.")

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers for Asana API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def create_task(
        self, project_id: str, name: str, notes: str = ""
    ) -> Optional[str]:
        """Create an Asana task.

        Returns the task GID on success, None on failure or when not configured.
        """
        if not self._configured:
            logger.debug(
                "create_task called without valid access token; returning None."
            )
            return None

        try:
            import httpx

            payload = {
                "data": {
                    "projects": [project_id],
                    "name": name,
                    "notes": notes,
                }
            }

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/tasks",
                        json=payload,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, f"create_task({project_id})")
            task_gid = data.get("data", {}).get("gid")
            logger.info("Created Asana task %s: %s", task_gid, name)
            return task_gid
        except ImportError:
            logger.error("httpx is not installed. Cannot create Asana task.")
            return None
        except Exception as exc:
            logger.error(
                "Failed to create Asana task in project %s: %s", project_id, exc
            )
            return None
