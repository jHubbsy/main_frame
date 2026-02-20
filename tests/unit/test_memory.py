"""Tests for memory system."""

from __future__ import annotations

from pathlib import Path

import pytest

from mainframe.memory.base import SearchResult
from mainframe.memory.hybrid import reciprocal_rank_fusion
from mainframe.memory.sqlite_store import SqliteMemoryStore


@pytest.fixture
def sqlite_store(tmp_path: Path) -> SqliteMemoryStore:
    return SqliteMemoryStore(db_path=tmp_path / "memory.db")


@pytest.mark.asyncio
async def test_sqlite_add_and_search(sqlite_store: SqliteMemoryStore):
    await sqlite_store.add("Python is a programming language", {"source": "test"})
    results = await sqlite_store.search("Python programming")
    assert len(results) > 0
    assert "Python" in results[0].content


@pytest.mark.asyncio
async def test_sqlite_message_indexing(sqlite_store: SqliteMemoryStore):
    await sqlite_store.add_message("sess1", "user", "Tell me about authentication")
    await sqlite_store.add_message("sess1", "assistant", "OAuth2 is a common auth protocol")
    results = await sqlite_store.search("authentication")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_sqlite_stats(sqlite_store: SqliteMemoryStore):
    await sqlite_store.add_message("s1", "user", "hello")
    await sqlite_store.add("a fact")
    stats = await sqlite_store.get_stats()
    assert stats["messages"] == 1
    assert stats["facts"] == 1


def test_rrf_merge():
    list_a = [
        SearchResult(content="doc1", score=0.9, source="fts"),
        SearchResult(content="doc2", score=0.5, source="fts"),
    ]
    list_b = [
        SearchResult(content="doc2", score=0.8, source="vector"),
        SearchResult(content="doc3", score=0.7, source="vector"),
    ]
    merged = reciprocal_rank_fusion(list_a, list_b, max_results=3)
    # doc2 appears in both lists, should rank highest
    assert merged[0].content == "doc2"
    assert len(merged) == 3


def test_rrf_deduplication():
    list_a = [SearchResult(content="same", score=1.0, source="a")]
    list_b = [SearchResult(content="same", score=0.5, source="b")]
    merged = reciprocal_rank_fusion(list_a, list_b)
    assert len(merged) == 1
