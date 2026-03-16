"""Search the web using Brave Search API."""

from __future__ import annotations

import getpass
from typing import Any

import httpx

from mainframe.security.credentials import get_api_key, store_api_key
from mainframe.tools.base import ToolContext, ToolResult

name = "web_search"
description = (
    "Search the web using Brave Search and return a list of results with titles, "
    "URLs, and description snippets."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "count": {
            "type": "integer",
            "description": "Number of results to return (default 5, max 20).",
        },
    },
    "required": ["query"],
}

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_TIMEOUT = 10.0


def _get_brave_key() -> str | None:
    """Get Brave API key, prompting interactively if not found."""
    key = get_api_key("brave")
    if key:
        return key

    try:
        key = getpass.getpass("Enter your Brave Search API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not key:
        return None

    store_api_key("brave", key)
    return key


def _format_results(results: list[dict[str, Any]]) -> str:
    """Format Brave search results into readable text."""
    if not results:
        return "No results found."

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        desc = r.get("description", "No description.")
        lines.append(f"{i}. **{title}**\n   {url}\n   {desc}")

    return "\n\n".join(lines)


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    query: str = params["query"]
    count: int = min(params.get("count", 5), 20)

    api_key = _get_brave_key()
    if not api_key:
        return ToolResult.error(
            "Brave Search API key not configured. "
            "Set BRAVE_API_KEY env var or run `mainframe auth login` with provider 'brave'."
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _BRAVE_SEARCH_URL,
                params={"q": query, "count": count},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )
    except httpx.TimeoutException:
        return ToolResult.error("Brave Search request timed out.")
    except httpx.HTTPError as e:
        return ToolResult.error(f"Brave Search request failed: {e}")

    if resp.status_code == 401:
        return ToolResult.error("Invalid Brave Search API key.")
    if resp.status_code == 429:
        return ToolResult.error("Brave Search rate limit exceeded. Try again later.")
    if resp.status_code >= 400:
        return ToolResult.error(f"Brave Search API error: HTTP {resp.status_code}")

    data = resp.json()
    web_results = data.get("web", {}).get("results", [])

    return ToolResult.success(_format_results(web_results))
