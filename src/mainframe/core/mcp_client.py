"""MCP client manager — connects to and manages MCP server processes."""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mainframe.core.errors import MCPConnectionError

if TYPE_CHECKING:
    from mainframe.config.schema import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Manages connections to multiple MCP servers."""

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()

    @property
    def server_names(self) -> list[str]:
        return list(self._sessions.keys())

    def get_session(self, name: str) -> ClientSession | None:
        return self._sessions.get(name)

    async def connect_server(self, name: str, config: MCPServerConfig) -> ClientSession | None:
        """Connect to a single MCP server. Returns session or None on failure."""
        try:
            params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env or None,
            )
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            read_stream, write_stream = stdio_transport
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            self._sessions[name] = session
            return session
        except Exception as e:
            logger.warning("Failed to connect to MCP server '%s': %s", name, e)
            raise MCPConnectionError(f"Failed to connect to MCP server '{name}': {e}") from e

    async def connect_all(
        self, servers: dict[str, MCPServerConfig],
    ) -> dict[str, ClientSession]:
        """Connect to all configured servers, skipping failures with warnings."""
        connected: dict[str, ClientSession] = {}
        for name, config in servers.items():
            try:
                session = await self.connect_server(name, config)
                if session:
                    connected[name] = session
            except MCPConnectionError:
                # Already logged in connect_server
                pass
        return connected

    async def cleanup(self) -> None:
        """Close all connections and clean up resources."""
        await self._exit_stack.aclose()
        self._sessions.clear()
