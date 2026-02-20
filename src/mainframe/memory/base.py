"""MemoryStore protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SearchResult:
    """A single memory search result."""

    content: str
    score: float = 0.0
    source: str = ""  # "session", "fact", "file"
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MemoryStore(Protocol):
    """Protocol for memory storage backends."""

    async def search(
        self, query: str, *, max_results: int = 10
    ) -> list[SearchResult]: ...

    async def add(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> str: ...

    async def sync(self) -> None: ...
