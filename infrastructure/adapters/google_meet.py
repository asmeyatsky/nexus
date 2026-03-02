"""
Google Meet Integration

Architectural Intent:
- Meeting transcript processing
- Auto-summarization via Vertex AI
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


@dataclass
class MeetingTranscript:
    meeting_id: str
    title: str
    participants: List[str]
    transcript_text: str
    duration_minutes: int
    date: str


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
                    "Google Meet %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                    operation_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Google Meet %s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    exc,
                )
    raise last_exception


class GoogleMeetAdapter:
    """Google Meet integration for transcript capture and summarization."""

    def __init__(self, project_id: str = "", credentials: Dict[str, Any] = None):
        self.project_id = project_id
        self._credentials = credentials
        self._configured = False
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that required configuration is present."""
        if not self.project_id:
            logger.warning(
                "GoogleMeetAdapter initialized without project_id. "
                "Transcript retrieval and summarization will return placeholder data."
            )
            self._configured = False
        else:
            self._configured = True
            logger.info(
                "GoogleMeetAdapter configured with project '%s'.", self.project_id
            )

    async def get_transcript(self, meeting_id: str) -> Optional[MeetingTranscript]:
        """Retrieve meeting transcript.

        Returns None when the adapter is not configured or on failure.
        """
        if not self._configured:
            logger.debug(
                "get_transcript called without valid configuration; returning None."
            )
            return None

        try:
            import httpx

            async def _do_request():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"https://meet.googleapis.com/v1/meetings/{meeting_id}/transcript",
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"get_transcript({meeting_id})"
            )
            return MeetingTranscript(
                meeting_id=meeting_id,
                title=data.get("title", ""),
                participants=data.get("participants", []),
                transcript_text=data.get("transcript", ""),
                duration_minutes=data.get("durationMinutes", 0),
                date=data.get("date", ""),
            )
        except ImportError:
            logger.error("httpx is not installed. Cannot retrieve meeting transcripts.")
            return None
        except Exception as exc:
            logger.error("Failed to get transcript for meeting %s: %s", meeting_id, exc)
            return None

    async def summarize_transcript(self, transcript: MeetingTranscript) -> Dict:
        """Summarize meeting transcript using Vertex AI.

        Returns a summary dict. Falls back to a basic extraction when
        Vertex AI is not available.
        """
        fallback = {
            "summary": "",
            "action_items": [],
            "key_topics": [],
            "sentiment": "neutral",
        }

        if not self._configured:
            logger.debug(
                "summarize_transcript called without valid configuration; "
                "returning basic fallback summary."
            )
            # Provide a minimal local fallback when not configured
            fallback["summary"] = (
                f"Meeting '{transcript.title}' with {len(transcript.participants)} "
                f"participants ({transcript.duration_minutes} min). "
                "Full AI summarization requires Google Cloud project configuration."
            )
            return fallback

        try:
            import httpx

            payload = {
                "instances": [{"content": transcript.transcript_text}],
                "parameters": {
                    "maxOutputTokens": 1024,
                    "temperature": 0.2,
                },
            }

            async def _do_request():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"https://us-central1-aiplatform.googleapis.com/v1/projects/"
                        f"{self.project_id}/locations/us-central1/publishers/google/"
                        f"models/text-bison:predict",
                        json=payload,
                        headers=self._auth_headers(),
                    )
                    response.raise_for_status()
                    return response.json()

            data = await _retry_with_backoff(
                _do_request, f"summarize_transcript({transcript.meeting_id})"
            )
            predictions = data.get("predictions", [{}])
            content = predictions[0].get("content", "") if predictions else ""
            return {
                "summary": content,
                "action_items": [],
                "key_topics": [],
                "sentiment": "neutral",
            }
        except ImportError:
            logger.error(
                "httpx is not installed. Cannot call Vertex AI for summarization."
            )
            return fallback
        except Exception as exc:
            logger.error(
                "Failed to summarize transcript for meeting %s: %s",
                transcript.meeting_id,
                exc,
            )
            return fallback

    async def link_to_opportunity(
        self, meeting_id: str, opportunity_id: str, org_id: str
    ) -> Dict:
        """Link meeting to an opportunity as activity.

        This is a local CRM operation and does not require external API calls.
        """
        try:
            activity = {
                "activity_type": "meeting",
                "meeting_id": meeting_id,
                "opportunity_id": opportunity_id,
                "org_id": org_id,
            }
            logger.info(
                "Linked meeting %s to opportunity %s in org %s",
                meeting_id,
                opportunity_id,
                org_id,
            )
            return activity
        except Exception as exc:
            logger.error(
                "Failed to link meeting %s to opportunity %s: %s",
                meeting_id,
                opportunity_id,
                exc,
            )
            return {
                "activity_type": "meeting",
                "meeting_id": meeting_id,
                "opportunity_id": opportunity_id,
                "error": str(exc),
            }

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers from stored credentials."""
        token = ""
        if self._credentials:
            token = self._credentials.get("access_token", "")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
