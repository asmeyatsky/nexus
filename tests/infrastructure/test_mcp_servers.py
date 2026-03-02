"""
MCP Server Schema Tests

Tests for MCP server tool schemas and compliance.
"""

from infrastructure.mcp_clients import (
    MCPRequest,
    MCPResponse,
    MCPErrorCode,
)


class TestMCPSchemas:
    def test_mcp_request_creation(self):
        req = MCPRequest(method="test/method", params={"key": "value"}, id="1")
        assert req.method == "test/method"
        assert req.params == {"key": "value"}

    def test_mcp_response_success(self):
        resp = MCPResponse(result={"data": "ok"}, id="1")
        assert not resp.is_error
        assert resp.result == {"data": "ok"}

    def test_mcp_response_error(self):
        resp = MCPResponse(
            error={"code": MCPErrorCode.INTERNAL_ERROR.value, "message": "fail"},
            id="1",
        )
        assert resp.is_error

    def test_error_codes(self):
        assert MCPErrorCode.INVALID_REQUEST.value == -32600
        assert MCPErrorCode.METHOD_NOT_FOUND.value == -32601
        assert MCPErrorCode.INVALID_PARAMS.value == -32602
        assert MCPErrorCode.INTERNAL_ERROR.value == -32603
