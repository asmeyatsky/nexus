"""
Vertex AI Integration

Architectural Intent:
- AI capabilities for Nexus CRM
- Uses Google Vertex AI for generative AI
- Features: opportunity scoring, lead enrichment, content generation
"""

import json
import logging
import re
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LeadEnrichment:
    company_size: Optional[str] = None
    industry_trends: Optional[str] = None
    recommended_approach: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class OpportunityAnalysis:
    risk_level: str = "low"
    success_probability: float = 0.0
    recommendations: list = None
    insights: str = ""

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class EmailDraft:
    subject: str
    body: str
    tone: str = "professional"


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from model response text, with fallback to regex."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting JSON from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


class VertexAIClient:
    """Client for Vertex AI integration."""

    def __init__(self, project_id: str = None, location: str = "europe-west2"):
        self.project_id = project_id or "your-project-id"
        self.location = location
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import aiplatform

                aiplatform.init(project=self.project_id, location=self.location)
                self._client = aiplatform
            except Exception as e:
                logger.warning(f"Vertex AI not available: {e}")
                return None
        return self._client

    async def enrich_lead(self, company_name: str, industry: str) -> LeadEnrichment:
        """Enrich lead data with AI-generated insights."""
        client = self._get_client()

        if client is None:
            return LeadEnrichment(
                company_size="Unknown",
                industry_trends="AI service unavailable",
                recommended_approach="Manual research recommended",
                confidence_score=0.0,
            )

        try:
            prompt = f"""Analyze this company for sales outreach:
Company: {company_name}
Industry: {industry}

Provide:
1. Estimated company size category
2. Key industry trends
3. Recommended outreach approach

Format as JSON with keys: company_size, industry_trends, recommended_approach"""

            model = client.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            logger.info(f"Vertex AI lead enrichment response for {company_name}")

            parsed = _extract_json(response.text)
            if parsed:
                return LeadEnrichment(
                    company_size=parsed.get("company_size", "Unknown"),
                    industry_trends=parsed.get("industry_trends", ""),
                    recommended_approach=parsed.get("recommended_approach", ""),
                    confidence_score=0.75,
                )

            # Fallback: use raw text as insight
            return LeadEnrichment(
                company_size="Unknown",
                industry_trends=response.text[:200] if response.text else "",
                recommended_approach="Review AI response manually",
                confidence_score=0.4,
            )
        except Exception as e:
            logger.error(f"Lead enrichment failed for {company_name}: {e}")
            return LeadEnrichment(
                confidence_score=0.0,
            )

    async def analyze_opportunity(
        self,
        opportunity_name: str,
        amount: float,
        stage: str,
        account_industry: str,
    ) -> OpportunityAnalysis:
        """Analyze opportunity for risk and recommendations."""
        client = self._get_client()

        if client is None:
            return OpportunityAnalysis(
                risk_level="medium",
                success_probability=0.5,
                recommendations=["Manual review recommended"],
                insights="AI service unavailable",
            )

        try:
            prompt = f"""Analyze this sales opportunity:
Name: {opportunity_name}
Amount: ${amount}
Stage: {stage}
Industry: {account_industry}

Provide:
1. Risk level (low/medium/high)
2. Success probability estimate
3. Key recommendations
4. Strategic insights

Format as JSON with keys: risk_level, success_probability, recommendations (array), insights"""

            model = client.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            logger.info(f"Vertex AI opportunity analysis for {opportunity_name}")

            parsed = _extract_json(response.text)
            if parsed:
                risk = parsed.get("risk_level", "medium")
                if risk not in ("low", "medium", "high"):
                    risk = "medium"
                prob = parsed.get("success_probability", 0.5)
                if isinstance(prob, (int, float)):
                    prob = max(0.0, min(1.0, float(prob)))
                else:
                    prob = 0.5
                recs = parsed.get("recommendations", [])
                if isinstance(recs, str):
                    recs = [recs]
                return OpportunityAnalysis(
                    risk_level=risk,
                    success_probability=prob,
                    recommendations=recs,
                    insights=parsed.get("insights", ""),
                )

            return OpportunityAnalysis(
                risk_level="medium",
                success_probability=0.5,
                recommendations=["Review AI response manually"],
                insights=response.text[:200] if response.text else "",
            )
        except Exception as e:
            logger.error(f"Opportunity analysis failed for {opportunity_name}: {e}")
            return OpportunityAnalysis()

    async def generate_email_draft(
        self,
        recipient_name: str,
        company: str,
        purpose: str,
        tone: str = "professional",
    ) -> EmailDraft:
        """Generate email draft for outreach."""
        client = self._get_client()

        if client is None:
            return EmailDraft(
                subject=f"Following up - {company}",
                body=f"Hi {recipient_name},\n\nI'd love to discuss how we can help {company}...",
                tone=tone,
            )

        try:
            prompt = f"""Generate a {tone} cold outreach email:
Recipient: {recipient_name}
Company: {company}
Purpose: {purpose}

Format as JSON with keys: subject, body"""

            model = client.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            logger.info(f"Vertex AI email draft for {recipient_name} at {company}")

            parsed = _extract_json(response.text)
            if parsed and "subject" in parsed and "body" in parsed:
                return EmailDraft(
                    subject=parsed["subject"],
                    body=parsed["body"],
                    tone=tone,
                )

            # Fallback: try to split response into subject/body
            text = response.text or ""
            lines = text.strip().split("\n", 1)
            subject = (
                lines[0].replace("Subject:", "").strip()
                if lines
                else f"Ideas for {company}"
            )
            body = lines[1].strip() if len(lines) > 1 else text
            return EmailDraft(
                subject=subject[:200],
                body=body,
                tone=tone,
            )
        except Exception as e:
            logger.error(f"Email draft generation failed: {e}")
            return EmailDraft(
                subject=f"Discussion about {company}",
                body=f"Hi {recipient_name},\n\nLet's connect about {company}.",
                tone=tone,
            )


vertex_ai_client = VertexAIClient()
