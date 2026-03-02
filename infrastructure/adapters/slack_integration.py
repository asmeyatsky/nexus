"""
Slack Integration

Architectural Intent:
- Send CRM notifications to Slack channels
- Slack slash commands for CRM queries
"""

from typing import Dict, Any, Optional, List


class SlackAdapter:
    """Slack integration for notifications and commands."""

    def __init__(self, bot_token: str = "", webhook_url: str = ""):
        self.bot_token = bot_token
        self.webhook_url = webhook_url

    async def send_notification(
        self, channel: str, message: str, blocks: List[Dict] = None
    ) -> bool:
        """Send notification to Slack channel."""
        if not self.bot_token and not self.webhook_url:
            print(f"[Slack Mock] #{channel}: {message}")
            return True

        import httpx
        async with httpx.AsyncClient() as client:
            payload = {"channel": channel, "text": message}
            if blocks:
                payload["blocks"] = blocks
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            return response.status_code == 200

    async def send_deal_alert(
        self, channel: str, deal_name: str, amount: float, stage: str, owner: str
    ) -> bool:
        """Send deal stage change alert."""
        message = f"Deal *{deal_name}* moved to _{stage}_ (${amount:,.2f}) — Owner: {owner}"
        return await self.send_notification(channel, message)

    async def send_case_alert(
        self, channel: str, case_number: str, subject: str, priority: str
    ) -> bool:
        """Send new case alert."""
        message = f"New {priority} case #{case_number}: {subject}"
        return await self.send_notification(channel, message)
