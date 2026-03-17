"""MCP OAuth helpers — browser-based auth flow with encrypted token storage."""

from __future__ import annotations

import asyncio
import webbrowser
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from mainframe.cli.display import print_info
from mainframe.security.credentials import _get_credential_store

if TYPE_CHECKING:
    from mainframe.config.schema import MCPOAuthConfig


class CredentialTokenStorage:
    """TokenStorage backed by Mainframe's Fernet-encrypted credential store."""

    def __init__(self, server_name: str) -> None:
        self._server_name = server_name
        self._store = _get_credential_store()

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._store.get(f"mcp_{self._server_name}_oauth_token")
        if raw is None:
            return None
        return OAuthToken.model_validate_json(raw)

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._store.set(f"mcp_{self._server_name}_oauth_token", tokens.model_dump_json())

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._store.get(f"mcp_{self._server_name}_oauth_client")
        if raw is None:
            return None
        return OAuthClientInformationFull.model_validate_json(raw)

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._store.set(
            f"mcp_{self._server_name}_oauth_client", client_info.model_dump_json()
        )


# Satisfy the TokenStorage Protocol
CredentialTokenStorage.__protocol_attrs__ = TokenStorage.__protocol_attrs__  # type: ignore[attr-defined]


async def _run_callback_server(
    port: int,
) -> tuple[asyncio.Future[tuple[str, str | None]], asyncio.Server]:
    """Spin up a local HTTP server to catch the OAuth redirect callback."""
    loop = asyncio.get_event_loop()
    future: asyncio.Future[tuple[str, str | None]] = loop.create_future()

    async def _handle(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
            first_line = data.decode(errors="replace").split("\n")[0]
            parts = first_line.split(" ")
            code: str | None = None
            state: str | None = None
            if len(parts) >= 2:
                parsed = urlparse(parts[1])
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                state = params.get("state", [None])[0]

            body = (
                "<html><body>"
                "<h2>Authentication successful!</h2>"
                "<p>You can close this tab and return to Mainframe.</p>"
                "</body></html>"
            )
            response = (
                f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            )
            writer.write(response.encode())
            await writer.drain()

            if not future.done() and code:
                future.set_result((code, state))
        except Exception as exc:
            if not future.done():
                future.set_exception(exc)
        finally:
            writer.close()

    server = await asyncio.start_server(_handle, "127.0.0.1", port)
    return future, server


def build_oauth_provider(
    server_name: str,
    server_url: str,
    oauth_config: MCPOAuthConfig,
) -> OAuthClientProvider:
    """Build an OAuthClientProvider wired to a local callback server."""
    port = oauth_config.redirect_port
    redirect_uri = f"http://localhost:{port}/callback"
    storage = CredentialTokenStorage(server_name)

    # Mutable state shared between the two handlers (called sequentially)
    _state: dict[str, object] = {}

    async def redirect_handler(auth_url: str) -> None:
        future, server = await _run_callback_server(port)
        _state["future"] = future
        _state["server"] = server
        print_info(f"Opening browser for MCP auth: {server_name}")
        print_info(f"If browser doesn't open, visit:\n  {auth_url}")
        webbrowser.open(auth_url)

    async def callback_handler() -> tuple[str, str | None]:
        future = _state["future"]  # type: ignore[assignment]
        server = _state["server"]  # type: ignore[assignment]
        print_info("Waiting for browser authentication (5 min timeout)...")
        try:
            result: tuple[str, str | None] = await asyncio.wait_for(
                future, timeout=300.0  # type: ignore[arg-type]
            )
        finally:
            server.close()  # type: ignore[union-attr]
            await server.wait_closed()  # type: ignore[union-attr]
        return result

    metadata = OAuthClientMetadata(
        redirect_uris=[redirect_uri],  # type: ignore[list-item]
        token_endpoint_auth_method="none",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=" ".join(oauth_config.scopes) if oauth_config.scopes else None,
        client_name="Mainframe",
    )

    return OAuthClientProvider(
        server_url=server_url,
        client_metadata=metadata,
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
