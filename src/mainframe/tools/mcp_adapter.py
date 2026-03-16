"""Adapts MCP server tools to Mainframe's Tool protocol."""

from __future__ import annotations

import logging
from typing import Any

from mcp import ClientSession
from mcp.types import TextContent

from mainframe.tools.base import ToolContext, ToolResult
from mainframe.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPTool:
    """Wraps an MCP tool as a Mainframe Tool."""

    def __init__(
        self,
        name: str,
        tool_name: str,
        description: str,
        parameters: dict[str, Any],
        session: ClientSession,
    ) -> None:
        self.name = name  # prefixed: server__tool_name
        self.description = description
        self.parameters = parameters
        self._tool_name = tool_name  # original unprefixed name
        self._session = session

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        try:
            result = await self._session.call_tool(self._tool_name, params)
            text_parts = [
                block.text for block in result.content if isinstance(block, TextContent)
            ]
            content = "\n".join(text_parts) if text_parts else ""
            return ToolResult(content=content, is_error=bool(result.isError))
        except Exception as e:
            return ToolResult.error(f"MCP tool '{self.name}' failed: {e}")


async def discover_and_register(
    server_name: str,
    session: ClientSession,
    registry: ToolRegistry,
) -> list[str]:
    """Discover tools from an MCP server and register them in the tool registry."""
    result = await session.list_tools()
    registered: list[str] = []

    for tool in result.tools:
        prefixed_name = f"{server_name}__{tool.name}"
        mcp_tool = MCPTool(
            name=prefixed_name,
            tool_name=tool.name,
            description=tool.description or "",
            parameters=tool.inputSchema if tool.inputSchema else {},
            session=session,
        )
        registry.register(mcp_tool)  # type: ignore[arg-type]
        registered.append(prefixed_name)

    logger.info("Registered %d tools from MCP server '%s'", len(registered), server_name)
    return registered
