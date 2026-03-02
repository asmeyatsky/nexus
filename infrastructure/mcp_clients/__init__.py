"""
MCP Client Adapters

Architectural Intent:
- Client adapters for calling external MCP servers
- Typed request/response schemas
- Error handling with MCP error format
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MCPErrorCode(Enum):
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPRequest:
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class MCPResponse:
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class BaseMCPClient:
    """Base class for MCP client adapters."""

    def __init__(self, server_url: str):
        self.server_url = server_url

    async def call(self, method: str, params: Dict[str, Any] = None) -> MCPResponse:
        """Make an MCP call to the server."""
        import httpx

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.server_url, json=request)
                data = response.json()
                return MCPResponse(
                    result=data.get("result"),
                    error=data.get("error"),
                    id=data.get("id"),
                )
        except Exception as e:
            return MCPResponse(
                error={
                    "code": MCPErrorCode.INTERNAL_ERROR.value,
                    "message": str(e),
                }
            )


class AnalyticsMCPClient(BaseMCPClient):
    """MCP client for analytics service."""

    async def get_pipeline_summary(self, org_id: str) -> MCPResponse:
        return await self.call("analytics/pipeline_summary", {"org_id": org_id})

    async def get_forecast(self, org_id: str) -> MCPResponse:
        return await self.call("analytics/forecast", {"org_id": org_id})


class NotificationMCPClient(BaseMCPClient):
    """MCP client for notification service."""

    async def send_email(self, to: str, subject: str, body: str) -> MCPResponse:
        return await self.call(
            "notifications/send_email",
            {"to": to, "subject": subject, "body": body},
        )

    async def send_slack(self, channel: str, message: str) -> MCPResponse:
        return await self.call(
            "notifications/send_slack",
            {"channel": channel, "message": message},
        )
