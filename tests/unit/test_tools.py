"""Tests for tool system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mainframe.tools.base import ToolContext, validate_params
from mainframe.tools.builtins import register_builtins
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


@pytest.fixture
def ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="test", workspace_dir=tmp_path)


@pytest.fixture
def registry() -> ToolRegistry:
    r = ToolRegistry()
    register_builtins(r)
    return r


def test_registry_has_all_builtins(registry: ToolRegistry):
    expected = {
        "bash", "read_file", "write_file", "edit_file",
        "glob_search", "grep_search", "memory_search", "create_skill",
        "web_fetch", "web_search",
    }
    assert set(registry.names) == expected


def test_policy_from_groups():
    policy = ToolPolicy.from_groups(["readonly"])
    assert policy.is_allowed("read_file")
    assert not policy.is_allowed("bash")


def test_validate_params_missing_required():
    schema = {"required": ["path"], "properties": {"path": {"type": "string"}}}
    errors = validate_params({}, schema)
    assert any("path" in e for e in errors)


@pytest.mark.asyncio
async def test_read_file(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "test.txt").write_text("hello\nworld\n")
    result = await registry.execute("read_file", {"path": "test.txt"}, ctx)
    assert not result.is_error
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_write_file(registry: ToolRegistry, ctx: ToolContext):
    result = await registry.execute("write_file", {"path": "out.txt", "content": "data"}, ctx)
    assert not result.is_error
    assert (ctx.workspace_dir / "out.txt").read_text() == "data"


@pytest.mark.asyncio
async def test_edit_file(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "edit.txt").write_text("foo bar baz")
    result = await registry.execute("edit_file", {
        "path": "edit.txt", "old_string": "bar", "new_string": "qux",
    }, ctx)
    assert not result.is_error
    assert (ctx.workspace_dir / "edit.txt").read_text() == "foo qux baz"


@pytest.mark.asyncio
async def test_glob_search(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "a.py").write_text("")
    (ctx.workspace_dir / "b.txt").write_text("")
    result = await registry.execute("glob_search", {"pattern": "*.py"}, ctx)
    assert not result.is_error
    assert "a.py" in result.content
    assert "b.txt" not in result.content


@pytest.mark.asyncio
async def test_grep_search(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "code.py").write_text("def hello():\n    pass\n")
    result = await registry.execute("grep_search", {"pattern": "def hello"}, ctx)
    assert not result.is_error
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_bash(registry: ToolRegistry, ctx: ToolContext):
    result = await registry.execute("bash", {"command": "echo test123"}, ctx)
    assert not result.is_error
    assert "test123" in result.content


@pytest.mark.asyncio
async def test_create_skill(registry: ToolRegistry, tmp_path: Path):
    ctx = ToolContext(session_id="test", workspace_dir=tmp_path)
    # Monkey-patch skills_dir to use tmp_path
    import mainframe.tools.builtins.create_skill as cs_mod

    original = cs_mod.skills_dir
    cs_mod.skills_dir = lambda: tmp_path / "skills"

    try:
        result = await registry.execute("create_skill", {
            "skill_name": "test-gen",
            "description": "A generated skill",
            "body": "# Test\nGenerated skill.",
        }, ctx)
        assert not result.is_error
        assert (tmp_path / "skills" / "test-gen" / "SKILL.md").exists()
    finally:
        cs_mod.skills_dir = original


@pytest.mark.asyncio
async def test_web_fetch(registry: ToolRegistry, ctx: ToolContext):
    html_content = "<html><body><h1>Hello</h1><p>World</p></body></html>"
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("mainframe.tools.builtins.web_fetch.httpx.AsyncClient", return_value=mock_client):
        result = await registry.execute("web_fetch", {"url": "https://example.com"}, ctx)

    assert not result.is_error
    assert "Hello" in result.content
    assert "World" in result.content


@pytest.mark.asyncio
async def test_web_fetch_truncation(registry: ToolRegistry, ctx: ToolContext):
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "A" * 500
    mock_response.headers = {"content-type": "text/plain"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("mainframe.tools.builtins.web_fetch.httpx.AsyncClient", return_value=mock_client):
        result = await registry.execute(
            "web_fetch", {"url": "https://example.com", "max_length": 100}, ctx,
        )

    assert not result.is_error
    assert "truncated" in result.content


@pytest.mark.asyncio
async def test_web_search(registry: ToolRegistry, ctx: ToolContext):
    brave_response = {
        "web": {
            "results": [
                {
                    "title": "Example Result",
                    "url": "https://example.com",
                    "description": "An example search result.",
                },
            ],
        },
    }
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: brave_response

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("mainframe.tools.builtins.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("mainframe.tools.builtins.web_search._get_brave_key", return_value="test-key"),
    ):
        result = await registry.execute("web_search", {"query": "test query"}, ctx)

    assert not result.is_error
    assert "Example Result" in result.content
    assert "https://example.com" in result.content


@pytest.mark.asyncio
async def test_web_search_no_api_key(registry: ToolRegistry, ctx: ToolContext):
    with patch("mainframe.tools.builtins.web_search._get_brave_key", return_value=None):
        result = await registry.execute("web_search", {"query": "test"}, ctx)

    assert result.is_error
    assert "API key" in result.content
