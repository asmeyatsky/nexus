"""
LinkedIn Sales Navigator Integration

Architectural Intent:
- Lead and contact enrichment
- Company data enrichment
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

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
                    "LinkedIn %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "LinkedIn %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class LinkedInAdapter:
    """LinkedIn Sales Navigator integration for data enrichment."""

    BASE_URL = "https://api.linkedin.com/v2"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that the API key is present."""
        if not self.api_key:
            logger.warning(
                "LinkedInAdapter initialized without api_key. "
                "Enrichment and lead search will return empty results."
            )
            self._configured = False
        else:
            self._configured = True
            logger.info("LinkedInAdapter configured successfully.")

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers for the LinkedIn API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def enrich_contact(self, email: str) -> Optional[Dict[str, Any]]:
        """Enrich contact data from LinkedIn.

        Returns a dict with LinkedIn profile data, or None when not configured
        or on failure.
        """
        if not self._configured:
            logger.debug("enrich_contact called without valid API key; returning None.")
            return None

        if not email or "@" not in email:
            logger.error("enrich_contact called with invalid email: %s", email)
            return None

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.BASE_URL}/people",
                        params={"q": "email", "email": email},
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, f"enrich_contact({email})")
            elements = data.get("elements", [])
            if not elements:
                logger.info("No LinkedIn profile found for %s", email)
                return None

            profile = elements[0]
            result = {
                "linkedin_id": profile.get("id", ""),
                "first_name": profile.get("firstName", {})
                .get("localized", {})
                .get("en_US", ""),
                "last_name": profile.get("lastName", {})
                .get("localized", {})
                .get("en_US", ""),
                "headline": profile.get("headline", {})
                .get("localized", {})
                .get("en_US", ""),
                "industry": profile.get("industryName", {})
                .get("localized", {})
                .get("en_US", ""),
                "profile_url": profile.get("vanityName", ""),
            }
            logger.info("Enriched contact %s from LinkedIn.", email)
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot enrich contact from LinkedIn.")
            return None
        except Exception as exc:
            logger.error("Failed to enrich contact %s: %s", email, exc)
            return None

    async def enrich_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Enrich company data from LinkedIn.

        Returns a dict with company data, or None when not configured or on failure.
        """
        if not self._configured:
            logger.debug("enrich_company called without valid API key; returning None.")
            return None

        if not company_name:
            logger.error("enrich_company called with empty company name.")
            return None

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.BASE_URL}/organizationLookup",
                        params={"q": "vanityName", "vanityName": company_name},
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"enrich_company({company_name})"
            )
            elements = data.get("elements", [])
            if not elements:
                logger.info("No LinkedIn company found for '%s'", company_name)
                return None

            org = elements[0]
            result = {
                "linkedin_id": org.get("id", ""),
                "name": org.get("localizedName", ""),
                "description": org.get("localizedDescription", ""),
                "website": org.get("localizedWebsite", ""),
                "industry": org.get("industryName", ""),
                "employee_count_range": org.get("staffCountRange", ""),
                "headquarters": org.get("locations", [{}])[0]
                if org.get("locations")
                else {},
            }
            logger.info("Enriched company '%s' from LinkedIn.", company_name)
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot enrich company from LinkedIn.")
            return None
        except Exception as exc:
            logger.error("Failed to enrich company '%s': %s", company_name, exc)
            return None

    async def find_leads(
        self, company: str, title: str = "", location: str = ""
    ) -> List[Dict[str, Any]]:
        """Search for leads on LinkedIn.

        Returns a list of lead dicts. Returns an empty list when not configured
        or on failure.
        """
        if not self._configured:
            logger.debug(
                "find_leads called without valid API key; returning empty list."
            )
            return []

        if not company:
            logger.error("find_leads called without a company name.")
            return []

        try:
            import httpx

            params: Dict[str, Any] = {"q": "search", "company": company}
            if title:
                params["title"] = title
            if location:
                params["location"] = location

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.BASE_URL}/salesNavigator/leads",
                        params=params,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"find_leads(company={company})"
            )
            leads = []
            for element in data.get("elements", []):
                leads.append(
                    {
                        "linkedin_id": element.get("id", ""),
                        "name": element.get("name", ""),
                        "title": element.get("title", ""),
                        "company": element.get("company", ""),
                        "location": element.get("location", ""),
                    }
                )
            logger.info(
                "Found %d leads for company '%s' (title='%s', location='%s')",
                len(leads),
                company,
                title,
                location,
            )
            return leads
        except ImportError:
            logger.error("httpx is not installed. Cannot search LinkedIn leads.")
            return []
        except Exception as exc:
            logger.error("Failed to find leads for company '%s': %s", company, exc)
            return []
