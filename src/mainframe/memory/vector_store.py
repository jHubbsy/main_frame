"""ChromaDB embedded vector store for semantic search."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import chromadb

from mainframe.config.paths import data_dir
from mainframe.memory.base import SearchResult


class VectorMemoryStore:
    """Semantic search using ChromaDB's embedded mode."""

    def __init__(self, persist_dir: Path | None = None, collection_name: str = "memory"):
        persist_dir = persist_dir or (data_dir() / "chromadb")
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def search(
        self, query: str, *, max_results: int = 10
    ) -> list[SearchResult]:
        """Semantic similarity search."""
        results = self._collection.query(
            query_texts=[query],
            n_results=max_results,
        )

        search_results: list[SearchResult] = []
        if not results["documents"] or not results["documents"][0]:
            return search_results

        documents = results["documents"][0]
        distances = results["distances"][0] if results["distances"] else [0.0] * len(documents)
        metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)

        for doc, dist, meta in zip(documents, distances, metadatas, strict=False):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - (distance / 2)
            score = 1.0 - (dist / 2.0)
            search_results.append(SearchResult(
                content=doc,
                score=score,
                source=meta.get("source", ""),
                metadata=meta,
            ))

        return search_results

    async def add(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Add a document to the vector store."""
        doc_id = uuid.uuid4().hex[:12]
        meta = metadata or {}
        # ChromaDB requires metadata values to be str, int, float, or bool
        clean_meta = {
            k: v for k, v in meta.items()
            if isinstance(v, (str, int, float, bool))
        }
        self._collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[clean_meta] if clean_meta else None,
        )
        return doc_id

    async def sync(self) -> None:
        """No-op — ChromaDB PersistentClient auto-persists."""

    async def get_stats(self) -> dict[str, int]:
        """Return count of stored vectors."""
        return {"vectors": self._collection.count()}
