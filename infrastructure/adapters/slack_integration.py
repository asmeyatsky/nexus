"""
Slack Integration

Architectural Intent:
- Send CRM notifications to Slack channels
- Slack slash commands for CRM queries
"""

import asyncio
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5


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
                    "Slack %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Slack %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class SlackAdapter:
    """Slack integration for notifications and commands."""

    def __init__(self, bot_token: str = "", webhook_url: str = ""):
        self.bot_token = bot_token
        self.webhook_url = webhook_url
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that at least one authentication method is available."""
        if not self.bot_token and not self.webhook_url:
            logger.warning(
                "SlackAdapter initialized without bot_token or webhook_url. "
                "Notifications will be logged locally instead of sent to Slack."
            )
            self._configured = False
        else:
            if self.bot_token:
                logger.info("SlackAdapter configured with bot token.")
            if self.webhook_url:
                logger.info("SlackAdapter configured with webhook URL.")
            self._configured = True

    async def send_notification(
        self, channel: str, message: str, blocks: List[Dict] = None
    ) -> bool:
        """Send notification to Slack channel.

        Falls back to local logging when Slack is not configured.
        Returns True on success, False on failure.
        """
        if not self._configured:
            logger.info("[Slack Offline] #%s: %s", channel, message)
            return True

        try:
            import httpx  # noqa: F401

            if self.bot_token:
                return await self._send_via_api(channel, message, blocks)
            elif self.webhook_url:
                return await self._send_via_webhook(channel, message)
        except ImportError:
            logger.error(
                "httpx is not installed. Cannot send Slack notifications. "
                "Install with: pip install httpx"
            )
            return False
        except Exception as exc:
            logger.error("Failed to send Slack notification to #%s: %s", channel, exc)
            return False

    async def _send_via_api(
        self, channel: str, message: str, blocks: Optional[List[Dict]] = None
    ) -> bool:
        """Send a message using the Slack Web API (chat.postMessage)."""
        import httpx

        payload = {"channel": channel, "text": message}
        if blocks:
            payload["blocks"] = blocks

        async def _do_request():
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    error_msg = data.get("error", "unknown error")
                    raise RuntimeError(f"Slack API error: {error_msg}")
                return True

        try:
            return await _retry_with_backoff(
                _do_request, f"send_notification(#{channel})"
            )
        except Exception as exc:
            logger.error("Slack API send failed for #%s: %s", channel, exc)
            return False

    async def _send_via_webhook(self, channel: str, message: str) -> bool:
        """Send a message using an incoming webhook URL."""
        import httpx

        payload = {"text": message, "channel": channel}

        async def _do_request():
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True

        try:
            return await _retry_with_backoff(_do_request, f"webhook(#{channel})")
        except Exception as exc:
            logger.error("Slack webhook send failed for #%s: %s", channel, exc)
            return False

    async def send_deal_alert(
        self, channel: str, deal_name: str, amount: float, stage: str, owner: str
    ) -> bool:
        """Send deal stage change alert."""
        try:
            message = (
                f"Deal *{deal_name}* moved to _{stage}_ "
                f"(${amount:,.2f}) — Owner: {owner}"
            )
            return await self.send_notification(channel, message)
        except Exception as exc:
            logger.error("Failed to send deal alert for '%s': %s", deal_name, exc)
            return False

    async def send_case_alert(
        self, channel: str, case_number: str, subject: str, priority: str
    ) -> bool:
        """Send new case alert."""
        try:
            message = f"New {priority} case #{case_number}: {subject}"
            return await self.send_notification(channel, message)
        except Exception as exc:
            logger.error("Failed to send case alert for #%s: %s", case_number, exc)
            return False
