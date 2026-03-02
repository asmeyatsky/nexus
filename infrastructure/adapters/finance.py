"""
Finance System Integration

Architectural Intent:
- Invoice and revenue tracking
- ERP system integration
"""

import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


@dataclass
class Invoice:
    id: str
    account_id: str
    opportunity_id: str
    amount: float
    currency: str
    status: str
    due_date: str
    org_id: str


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
                    "Finance %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Finance %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class FinanceAdapter:
    """Finance/ERP system integration."""

    def __init__(self, api_url: str = "", api_key: str = ""):
        self.api_url = api_url.rstrip("/") if api_url else ""
        self.api_key = api_key
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that required configuration is present."""
        if not self.api_url:
            logger.warning(
                "FinanceAdapter initialized without api_url. "
                "Invoice operations will return mock/empty results."
            )
            self._configured = False
            return

        if not self.api_key:
            logger.warning(
                "FinanceAdapter has api_url but no api_key. "
                "API calls will likely fail authentication."
            )
            # Still try (some ERPs use other auth)
            self._configured = True
        else:
            self._configured = True
            logger.info("FinanceAdapter configured for %s.", self.api_url)

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers for the finance API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_invoice(
        self,
        account_id: str,
        opportunity_id: str,
        amount: float,
        currency: str,
        org_id: str,
    ) -> Optional[Invoice]:
        """Create an invoice from a won opportunity.

        Returns the created Invoice on success. Returns None and logs when
        not configured or on failure.
        """
        if not self._configured:
            logger.info(
                "[Finance Offline] Would create invoice: %.2f %s for account %s",
                amount,
                currency,
                account_id,
            )
            return None

        if amount <= 0:
            logger.error("Cannot create invoice with non-positive amount: %.2f", amount)
            return None

        try:
            import httpx

            payload = {
                "account_id": account_id,
                "opportunity_id": opportunity_id,
                "amount": amount,
                "currency": currency,
                "org_id": org_id,
                "due_date": datetime.utcnow().isoformat(),
            }

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.api_url}/invoices",
                        json=payload,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"create_invoice(account={account_id})"
            )
            invoice = Invoice(
                id=data.get("id", ""),
                account_id=account_id,
                opportunity_id=opportunity_id,
                amount=amount,
                currency=currency,
                status=data.get("status", "pending"),
                due_date=data.get("due_date", ""),
                org_id=org_id,
            )
            logger.info(
                "Created invoice %s for %.2f %s (account %s)",
                invoice.id,
                amount,
                currency,
                account_id,
            )
            return invoice
        except ImportError:
            logger.error("httpx is not installed. Cannot create invoice.")
            return None
        except Exception as exc:
            logger.error("Failed to create invoice for account %s: %s", account_id, exc)
            return None

    async def get_account_revenue(
        self, account_id: str, org_id: str
    ) -> Dict[str, float]:
        """Get total revenue for an account.

        Returns revenue metrics. Returns zeroed metrics on failure.
        """
        result = {"total_revenue": 0.0, "outstanding": 0.0, "overdue": 0.0}
        if not self._configured:
            logger.debug(
                "get_account_revenue called without valid configuration; returning zeros."
            )
            return result

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.api_url}/accounts/{account_id}/revenue",
                        headers=self._auth_headers(),
                        params={"org_id": org_id},
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"get_account_revenue({account_id})"
            )
            result["total_revenue"] = float(data.get("total_revenue", 0.0))
            result["outstanding"] = float(data.get("outstanding", 0.0))
            result["overdue"] = float(data.get("overdue", 0.0))
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot get account revenue.")
            return result
        except Exception as exc:
            logger.error("Failed to get revenue for account %s: %s", account_id, exc)
            return result

    async def sync_invoices(self, org_id: str) -> Dict[str, int]:
        """Sync invoices from ERP.

        Returns sync statistics. Returns zeroed stats on failure.
        """
        result = {"synced": 0, "created": 0, "updated": 0}
        if not self._configured:
            logger.debug("sync_invoices called without valid configuration; skipping.")
            return result

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        f"{self.api_url}/invoices",
                        headers=self._auth_headers(),
                        params={"org_id": org_id, "limit": 200},
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(_do_request, "sync_invoices")
            invoices = data.get("invoices", [])
            logger.info(
                "Retrieved %d invoices from ERP for org %s", len(invoices), org_id
            )
            result["synced"] = len(invoices)
            # Actual sync logic would diff and process invoices here
            return result
        except ImportError:
            logger.error("httpx is not installed. Cannot sync invoices.")
            return result
        except Exception as exc:
            logger.error("Failed to sync invoices for org %s: %s", org_id, exc)
            return result
