"""Memory manager — coordinates indexing and search across stores."""

from __future__ import annotations

from typing import Any

from mainframe.memory.base import SearchResult
from mainframe.memory.hybrid import reciprocal_rank_fusion
from mainframe.memory.sqlite_store import SqliteMemoryStore
from mainframe.memory.vector_store import VectorMemoryStore


class MemoryManager:
    """Coordinates hybrid search and indexing across SQLite FTS and ChromaDB."""

    def __init__(
        self,
        sqlite_store: SqliteMemoryStore | None = None,
        vector_store: VectorMemoryStore | None = None,
    ):
        self._sqlite = sqlite_store or SqliteMemoryStore()
        self._vector = vector_store or VectorMemoryStore()

    @property
    def sqlite(self) -> SqliteMemoryStore:
        return self._sqlite

    @property
    def vector(self) -> VectorMemoryStore:
        return self._vector

    async def search(
        self, query: str, *, max_results: int = 10
    ) -> list[SearchResult]:
        """Hybrid search: FTS5 keyword + ChromaDB semantic, merged via RRF."""
        fts_results = await self._sqlite.search(query, max_results=max_results)
        vec_results = await self._vector.search(query, max_results=max_results)
        return reciprocal_rank_fusion(
            fts_results, vec_results, max_results=max_results,
        )

    async def add_fact(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Add a fact to both stores."""
        meta = metadata or {}
        meta.setdefault("source", "user")
        sqlite_id = await self._sqlite.add(text, meta)
        await self._vector.add(text, meta)
        return sqlite_id

    async def index_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_call_id: str | None = None,
    ) -> None:
        """Index a conversation message in both stores."""
        # Skip very short or empty messages
        if not content or len(content.strip()) < 5:
            return

        await self._sqlite.add_message(session_id, role, content, tool_call_id)
        await self._vector.add(content, {
            "source": "session",
            "session_id": session_id,
            "role": role,
        })

    async def get_stats(self) -> dict[str, Any]:
        """Combined stats from all stores."""
        sqlite_stats = await self._sqlite.get_stats()
        vector_stats = await self._vector.get_stats()
        return {**sqlite_stats, **vector_stats}

    async def sync(self) -> None:
        """Sync all stores."""
        await self._sqlite.sync()
        await self._vector.sync()
