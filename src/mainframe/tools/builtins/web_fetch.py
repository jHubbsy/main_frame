"""Fetch a URL and return its content as markdown."""

from __future__ import annotations

from typing import Any

import html2text
import httpx

from mainframe.tools.base import ToolContext, ToolResult

name = "web_fetch"
description = (
    "Fetch a URL and return the page content as markdown."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL to fetch.",
        },
        "max_length": {
            "type": "integer",
            "description": "Maximum character length of returned content (default 10000).",
        },
    },
    "required": ["url"],
}

_USER_AGENT = "Mainframe/0.1 (AI Agent; +https://github.com/mainframe)"
_TIMEOUT = 15.0


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    url: str = params["url"]
    max_length: int = params.get("max_length", 10000)

    if not url.startswith(("http://", "https://")):
        return ToolResult.error(f"Invalid URL (must start with http:// or https://): {url}")

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = await client.get(url)
    except httpx.TimeoutException:
        return ToolResult.error(f"Request timed out after {_TIMEOUT}s: {url}")
    except httpx.ConnectError as e:
        return ToolResult.error(f"Connection failed: {e}")
    except httpx.HTTPError as e:
        return ToolResult.error(f"HTTP error: {e}")

    if resp.status_code >= 400:
        return ToolResult.error(f"HTTP {resp.status_code} for {url}")

    content_type = resp.headers.get("content-type", "")

    if "text/html" in content_type or "<html" in resp.text[:500].lower():
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.body_width = 0
        text = converter.handle(resp.text)
    else:
        text = resp.text

    if len(text) > max_length:
        text = text[:max_length] + f"\n\n... (truncated at {max_length} chars)"

    return ToolResult.success(text)
