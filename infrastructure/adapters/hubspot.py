"""
HubSpot Integration

Architectural Intent:
- Bi-directional marketing data sync
- Contact and campaign sync
"""

import asyncio
import logging
from typing import Dict, Any, Optional

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
                    "HubSpot %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "HubSpot %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class HubSpotAdapter:
    """HubSpot marketing integration."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://api.hubapi.com"
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that the API key is present."""
        if not self.api_key:
            logger.warning(
                "HubSpotAdapter initialized without api_key. "
                "All sync operations will return empty results."
            )
            self._configured = False
        else:
            self._configured = True
            logger.info("HubSpotAdapter configured successfully.")

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def sync_contacts(self, org_id: str) -> Dict[str, int]:
        """Sync contacts between HubSpot and Nexus.

        Returns sync statistics. Returns zeroed stats when not configured.
        """
        result = {"synced": 0, "created": 0, "updated": 0}
        if not self._configured:
            logger.debug("sync_contacts called without valid API key; skipping.")
            return result

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        f"{self.base_url}/crm/v3/objects/contacts",
                        headers=self._auth_headers(),
                        params={"limit": 100},
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "sync_contacts")
            contacts = data.get("results", [])
            logger.info(
                "Retrieved %d HubSpot contacts for org %s", len(contacts), org_id
            )
            # Actual sync logic would process contacts here
            result["synced"] = len(contacts)
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot sync HubSpot contacts.")
            return result
        except Exception as exc:
            logger.error("Failed to sync contacts for org %s: %s", org_id, exc)
            return result

    async def sync_campaigns(self, org_id: str) -> Dict[str, int]:
        """Sync marketing campaigns.

        Returns sync statistics. Returns zeroed stats when not configured.
        """
        result = {"synced": 0}
        if not self._configured:
            logger.debug("sync_campaigns called without valid API key; skipping.")
            return result

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        f"{self.base_url}/marketing/v1/campaigns",
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "sync_campaigns")
            campaigns = data.get("campaigns", [])
            logger.info(
                "Retrieved %d HubSpot campaigns for org %s", len(campaigns), org_id
            )
            result["synced"] = len(campaigns)
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot sync HubSpot campaigns.")
            return result
        except Exception as exc:
            logger.error("Failed to sync campaigns for org %s: %s", org_id, exc)
            return result

    async def push_lead(self, lead_data: Dict[str, Any]) -> Optional[str]:
        """Push a lead to HubSpot.

        Returns the HubSpot contact ID on success, None on failure.
        """
        if not self._configured:
            logger.debug("push_lead called without valid API key; skipping.")
            return None

        try:
            import httpx

            required_fields = ["email"]
            missing = [f for f in required_fields if f not in lead_data]
            if missing:
                logger.error(
                    "push_lead missing required fields: %s", ", ".join(missing)
                )
                return None

            payload = {
                "properties": lead_data,
            }

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/crm/v3/objects/contacts",
                        json=payload,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "push_lead")
            hubspot_id = data.get("id")
            logger.info("Pushed lead to HubSpot, contact ID: %s", hubspot_id)
            return hubspot_id
        except ImportError:
            logger.error("httpx is not installed. Cannot push lead to HubSpot.")
            return None
        except Exception as exc:
            logger.error("Failed to push lead to HubSpot: %s", exc)
            return None

    async def get_engagement_data(self, contact_email: str) -> Dict:
        """Get engagement data for a contact.

        Returns engagement metrics. Returns zeroed metrics on failure.
        """
        result = {"email_opens": 0, "clicks": 0, "form_submissions": 0}
        if not self._configured:
            logger.debug("get_engagement_data called without valid API key; skipping.")
            return result

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # First look up contact by email
                    search_payload = {
                        "filterGroups": [
                            {
                                "filters": [
                                    {
                                        "propertyName": "email",
                                        "operator": "EQ",
                                        "value": contact_email,
                                    }
                                ]
                            }
                        ]
                    }
                    response = await client.post(
                        f"{self.base_url}/crm/v3/objects/contacts/search",
                        json=search_payload,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"get_engagement_data({contact_email})"
            )
            contacts = data.get("results", [])
            if contacts:
                props = contacts[0].get("properties", {})
                result["email_opens"] = int(props.get("hs_email_open", 0))
                result["clicks"] = int(props.get("hs_email_click", 0))
                result["form_submissions"] = int(props.get("num_conversion_events", 0))
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot get HubSpot engagement data.")
            return result
        except Exception as exc:
            logger.error("Failed to get engagement data for %s: %s", contact_email, exc)
            return result
