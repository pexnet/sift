"""MCP server module — shared between stdio and StreamableHTTP transports."""

from contextvars import ContextVar
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from sift.mcp.tools import TOOL_DEFINITIONS, execute_tool

mcp_server = Server("sift")

# Context variable for passing user_id from HTTP handler into MCP tool execution
_user_id_var: ContextVar[Any] = ContextVar("mcp_user_id", default=None)


def set_mcp_user_id(user_id: Any) -> None:
    _user_id_var.set(user_id)


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOL_DEFINITIONS


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    import json

    user_id = _user_id_var.get()
    if user_id is None:
        return [TextContent(type="text", text=json.dumps({"error": "Not authenticated"}))]

    result = await execute_tool(name, arguments, user_id)
    return [TextContent(type="text", text=result)]
