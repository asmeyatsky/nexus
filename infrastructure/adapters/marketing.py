"""
Marketing Automation Integration

Architectural Intent:
- Integration with email marketing platforms (SendGrid, Mailchimp)
- Campaign management
- Lead scoring and nurturing
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum
import asyncio


class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"


class EmailProvider(Enum):
    SENDGRID = "sendgrid"
    MAILCHIMP = "mailchimp"
    SENDINBLUE = "sendinblue"


@dataclass
class EmailTemplate:
    id: str
    name: str
    subject: str
    html_content: str
    provider: EmailProvider


@dataclass
class Campaign:
    id: str
    name: str
    status: CampaignStatus
    template_id: str
    segment_ids: List[str] = field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    recipient_count: int = 0
    open_count: int = 0
    click_count: int = 0
    bounce_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LeadScore:
    lead_id: str
    score: int = 0
    behavioral_score: int = 0
    demographic_score: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


class MarketingAutomationService:
    """Marketing automation with email provider integration."""

    def __init__(self):
        self._campaigns: Dict[str, Campaign] = {}
        self._templates: Dict[str, EmailTemplate] = {}
        self._lead_scores: Dict[str, LeadScore] = {}
        self._provider_config: Dict[EmailProvider, Dict] = {}

    def configure_provider(self, provider: EmailProvider, config: Dict):
        self._provider_config[provider] = config

    async def _retry_with_backoff(
        self, coro_func, *args, max_retries: int = 3, **kwargs
    ):
        """Retry an async operation with exponential backoff."""
        last_exception = None
        for attempt in range(max_retries):
            try:
                return await coro_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 0.5
                    await asyncio.sleep(wait_time)
        raise last_exception

    async def send_via_sendgrid(
        self,
        to: List[str],
        subject: str,
        html: str,
        from_email: str = "noreply@company.com",
    ) -> Dict:
        config = self._provider_config.get(EmailProvider.SENDGRID, {})
        api_key = config.get("api_key", "")

        if not api_key:
            return {"success": False, "error": "SendGrid not configured"}

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {
                "to": [{"email": email} for email in to],
                "from": {"email": from_email},
                "subject": subject,
                "html": html,
            }
        ]

        import httpx

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, json={"personalizations": messages}
                )
                return {
                    "success": response.status_code in (200, 202, 201),
                    "status": response.status_code,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def send_via_mailchimp(
        self,
        to: List[str],
        subject: str,
        html: str,
        list_id: str,
    ) -> Dict:
        config = self._provider_config.get(EmailProvider.MAILCHIMP, {})
        api_key = config.get("api_key", "")
        dc = api_key.split("-")[-1] if api_key else ""

        if not api_key:
            return {"success": False, "error": "Mailchimp not configured"}

        url = f"https://{dc}.api.mailchimp.com/3.0/campaigns"
        auth = ("anystring", api_key)

        campaign_data = {
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {"subject_line": subject, "reply_to": "noreply@company.com"},
        }

        import httpx

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, auth=auth, json=campaign_data)
                return {
                    "success": response.status_code in (200, 201),
                    "campaign_id": response.json().get("id"),
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    def create_campaign(
        self,
        name: str,
        template_id: str,
        segment_ids: List[str] = None,
    ) -> Campaign:
        campaign = Campaign(
            id=str(uuid4()),
            name=name,
            status=CampaignStatus.DRAFT,
            template_id=template_id,
            segment_ids=segment_ids or [],
        )
        self._campaigns[campaign.id] = campaign
        return campaign

    def schedule_campaign(self, campaign_id: str, scheduled_at: datetime) -> bool:
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.DRAFT:
            return False

        campaign.status = CampaignStatus.SCHEDULED
        campaign.scheduled_at = scheduled_at
        return True

    async def send_campaign(self, campaign_id: str) -> Dict:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campaign not found"}

        template = self._templates.get(campaign.template_id)
        if not template:
            return {"success": False, "error": "Template not found"}

        if template.provider == EmailProvider.SENDGRID:
            result = await self.send_via_sendgrid(
                to=["recipient@example.com"],
                subject=template.subject,
                html=template.html_content,
            )
        elif template.provider == EmailProvider.MAILCHIMP:
            result = await self.send_via_mailchimp(
                to=["recipient@example.com"],
                subject=template.subject,
                html=template.html_content,
                list_id="default",
            )
        else:
            result = {"success": False, "error": "Unknown provider"}

        if result.get("success"):
            campaign.status = CampaignStatus.SENT
            campaign.sent_at = datetime.now()

        return result

    def update_lead_score(
        self,
        lead_id: str,
        behavioral_points: int = 0,
        demographic_points: int = 0,
    ):
        if lead_id not in self._lead_scores:
            self._lead_scores[lead_id] = LeadScore(lead_id=lead_id)

        score = self._lead_scores[lead_id]
        score.behavioral_score += behavioral_points
        score.demographic_score += demographic_points
        score.score = score.behavioral_score + score.demographic_score
        score.last_updated = datetime.now()

        return score

    def get_lead_score(self, lead_id: str) -> Optional[LeadScore]:
        return self._lead_scores.get(lead_id)

    def get_hot_leads(self, min_score: int = 50) -> List[str]:
        return [
            lead_id
            for lead_id, score in self._lead_scores.items()
            if score.score >= min_score
        ]


marketing_service = MarketingAutomationService()
