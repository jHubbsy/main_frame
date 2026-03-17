"""MCP client manager — connects to and manages MCP server processes."""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

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
            if config.transport == "streamable_http":
                return await self._connect_http(name, config)
            return await self._connect_stdio(name, config)
        except MCPConnectionError:
            raise
        except Exception as e:
            logger.warning("Failed to connect to MCP server '%s': %s", name, e)
            raise MCPConnectionError(f"Failed to connect to MCP server '{name}': {e}") from e

    async def _connect_stdio(self, name: str, config: MCPServerConfig) -> ClientSession:
        if not config.command:
            raise MCPConnectionError(f"stdio transport requires 'command' for server '{name}'")
        # Merge credentials into parent env so the subprocess has PATH, HOME, etc.
        env = {**os.environ, **config.env} if config.env else None
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=env,
        )
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(params))
        read_stream, write_stream = stdio_transport
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        self._sessions[name] = session
        return session

    async def _connect_http(self, name: str, config: MCPServerConfig) -> ClientSession:
        if not config.url:
            raise MCPConnectionError(
                f"streamable_http transport requires 'url' for server '{name}'"
            )

        http_client: httpx.AsyncClient | None = None
        if config.oauth:
            from mainframe.core.mcp_auth import build_oauth_provider
            oauth_provider = build_oauth_provider(name, config.url, config.oauth)
            http_client = await self._exit_stack.enter_async_context(
                httpx.AsyncClient(auth=oauth_provider)
            )

        transport = await self._exit_stack.enter_async_context(
            streamable_http_client(config.url, http_client=http_client)
        )
        read_stream, write_stream, _get_session_id = transport
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        self._sessions[name] = session
        return session

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
                pass
        return connected

    async def cleanup(self) -> None:
        """Close all connections and clean up resources."""
        await self._exit_stack.aclose()
        self._sessions.clear()
