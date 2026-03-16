"""Tests for MCP client integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mainframe.tools.base import ToolContext
from mainframe.tools.mcp_adapter import MCPTool, discover_and_register
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


@pytest.fixture
def ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="test", workspace_dir=tmp_path)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


def _make_text_content(text: str) -> MagicMock:
    """Create a mock TextContent block."""
    from mcp.types import TextContent

    return TextContent(type="text", text=text)


@pytest.mark.asyncio
async def test_mcp_tool_execute(ctx: ToolContext, mock_session: AsyncMock):
    """MCPTool.execute calls session.call_tool and returns content."""
    mock_result = MagicMock()
    mock_result.content = [_make_text_content("hello from mcp")]
    mock_result.isError = False
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    tool = MCPTool(
        name="server__do_thing",
        tool_name="do_thing",
        description="Does a thing",
        parameters={"type": "object", "properties": {}},
        session=mock_session,
    )

    result = await tool.execute({"key": "value"}, ctx)
    assert not result.is_error
    assert result.content == "hello from mcp"
    mock_session.call_tool.assert_awaited_once_with("do_thing", {"key": "value"})


@pytest.mark.asyncio
async def test_mcp_tool_error_handling(ctx: ToolContext, mock_session: AsyncMock):
    """MCPTool.execute returns ToolResult.is_error on exception."""
    mock_session.call_tool = AsyncMock(side_effect=RuntimeError("connection lost"))

    tool = MCPTool(
        name="server__broken",
        tool_name="broken",
        description="Breaks",
        parameters={},
        session=mock_session,
    )

    result = await tool.execute({}, ctx)
    assert result.is_error
    assert "connection lost" in result.content


@pytest.mark.asyncio
async def test_mcp_tool_server_error(ctx: ToolContext, mock_session: AsyncMock):
    """MCPTool.execute propagates isError from MCP result."""
    mock_result = MagicMock()
    mock_result.content = [_make_text_content("not found")]
    mock_result.isError = True
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    tool = MCPTool(
        name="server__fail",
        tool_name="fail",
        description="Fails",
        parameters={},
        session=mock_session,
    )

    result = await tool.execute({}, ctx)
    assert result.is_error
    assert result.content == "not found"


@pytest.mark.asyncio
async def test_discover_and_register(mock_session: AsyncMock, registry: ToolRegistry):
    """discover_and_register lists tools and registers them with prefixed names."""
    mock_tool_1 = MagicMock()
    mock_tool_1.name = "list_prs"
    mock_tool_1.description = "List pull requests"
    mock_tool_1.inputSchema = {"type": "object", "properties": {"repo": {"type": "string"}}}

    mock_tool_2 = MagicMock()
    mock_tool_2.name = "create_issue"
    mock_tool_2.description = "Create an issue"
    mock_tool_2.inputSchema = {"type": "object", "properties": {}}

    mock_list_result = MagicMock()
    mock_list_result.tools = [mock_tool_1, mock_tool_2]
    mock_session.list_tools = AsyncMock(return_value=mock_list_result)

    names = await discover_and_register("github", mock_session, registry)

    assert names == ["github__list_prs", "github__create_issue"]
    assert registry.has("github__list_prs")
    assert registry.has("github__create_issue")


def test_mcp_tool_namespacing():
    """Verify server__tool naming convention."""
    tool = MCPTool(
        name="postgres__query",
        tool_name="query",
        description="Run a query",
        parameters={},
        session=AsyncMock(),
    )
    assert tool.name == "postgres__query"
    assert tool._tool_name == "query"


def test_policy_mcp_wildcard():
    """mcp:github in allowed_tool_groups allows github__* tools."""
    policy = ToolPolicy.from_groups(["builtin", "mcp:github"])

    # Builtin tools allowed
    assert policy.is_allowed("bash")
    assert policy.is_allowed("read_file")

    # MCP tools from github server allowed
    assert policy.is_allowed("github__list_prs")
    assert policy.is_allowed("github__create_issue")

    # MCP tools from other servers denied
    assert not policy.is_allowed("slack__send_message")
    assert not policy.is_allowed("postgres__query")


def test_policy_multiple_mcp_servers():
    """Multiple mcp: groups each allow their server's tools."""
    policy = ToolPolicy.from_groups(["mcp:github", "mcp:slack"])

    assert policy.is_allowed("github__list_prs")
    assert policy.is_allowed("slack__send_message")
    assert not policy.is_allowed("postgres__query")


def test_policy_allow_mcp_server():
    """allow_mcp_server dynamically adds a server prefix."""
    policy = ToolPolicy.from_groups(["builtin"])
    assert not policy.is_allowed("github__list_prs")

    policy.allow_mcp_server("github")
    assert policy.is_allowed("github__list_prs")


# --- connect_mcp tool tests ---


@pytest.mark.asyncio
async def test_connect_mcp_creates_pending_request(ctx: ToolContext):
    """connect_mcp stores a pending request with correct fields."""
    from mainframe.tools.builtins.connect_mcp import (
        clear_pending_requests,
        execute,
        get_pending_requests,
    )

    clear_pending_requests()

    result = await execute(
        {
            "server_name": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": "tok_123"},
        },
        ctx,
    )

    assert not result.is_error
    pending = get_pending_requests()
    assert len(pending) == 1
    assert pending[0].server_name == "github"
    assert pending[0].command == "npx"
    assert pending[0].args == ["-y", "@modelcontextprotocol/server-github"]
    assert pending[0].env == {"GITHUB_TOKEN": "tok_123"}

    clear_pending_requests()


@pytest.mark.asyncio
async def test_connect_mcp_clears_requests(ctx: ToolContext):
    """clear_pending_requests empties the list."""
    from mainframe.tools.builtins.connect_mcp import (
        clear_pending_requests,
        execute,
        get_pending_requests,
    )

    clear_pending_requests()

    await execute({"server_name": "test", "command": "echo"}, ctx)
    assert len(get_pending_requests()) == 1

    clear_pending_requests()
    assert len(get_pending_requests()) == 0
