"""SQLite FTS5 keyword search over messages and facts."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mainframe.config.paths import memory_db
from mainframe.memory.base import SearchResult


class SqliteMemoryStore:
    """Keyword search using SQLite FTS5."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or memory_db()
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_call_id TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                tags TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                USING fts5(content, content=messages, content_rowid=id);

            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
                USING fts5(content, content=facts, content_rowid=id);
        """)
        # Triggers to keep FTS in sync
        for table in ("messages", "facts"):
            fts = f"{table}_fts"
            conn.executescript(f"""
                CREATE TRIGGER IF NOT EXISTS {table}_ai AFTER INSERT ON {table} BEGIN
                    INSERT INTO {fts}(rowid, content) VALUES (new.id, new.content);
                END;
                CREATE TRIGGER IF NOT EXISTS {table}_ad AFTER DELETE ON {table} BEGIN
                    INSERT INTO {fts}({fts}, rowid, content)
                        VALUES('delete', old.id, old.content);
                END;
                CREATE TRIGGER IF NOT EXISTS {table}_au AFTER UPDATE ON {table} BEGIN
                    INSERT INTO {fts}({fts}, rowid, content)
                        VALUES('delete', old.id, old.content);
                    INSERT INTO {fts}(rowid, content) VALUES (new.id, new.content);
                END;
            """)
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    async def search(
        self, query: str, *, max_results: int = 10
    ) -> list[SearchResult]:
        """FTS5 search across messages and facts."""
        conn = self._connect()
        results: list[SearchResult] = []

        # Search messages
        rows = conn.execute(
            """SELECT m.content, m.session_id, m.role, m.created_at,
                      rank * -1 as score
               FROM messages_fts fts
               JOIN messages m ON m.id = fts.rowid
               WHERE messages_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, max_results),
        ).fetchall()

        for row in rows:
            results.append(SearchResult(
                content=row["content"],
                score=row["score"],
                source="session",
                metadata={
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "created_at": row["created_at"],
                },
            ))

        # Search facts
        rows = conn.execute(
            """SELECT f.content, f.source, f.created_at, f.tags,
                      rank * -1 as score
               FROM facts_fts fts
               JOIN facts f ON f.id = fts.rowid
               WHERE facts_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, max_results),
        ).fetchall()

        for row in rows:
            results.append(SearchResult(
                content=row["content"],
                score=row["score"],
                source="fact",
                metadata={
                    "fact_source": row["source"],
                    "created_at": row["created_at"],
                    "tags": row["tags"],
                },
            ))

        conn.close()

        # Sort combined results by score descending, return top N
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    async def add(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Add a fact to memory."""
        metadata = metadata or {}
        conn = self._connect()
        cursor = conn.execute(
            "INSERT INTO facts (content, source, tags) VALUES (?, ?, ?)",
            (text, metadata.get("source", ""), str(metadata.get("tags", ""))),
        )
        conn.commit()
        row_id = str(cursor.lastrowid)
        conn.close()
        return row_id

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_call_id: str | None = None,
    ) -> None:
        """Index a conversation message for search."""
        conn = self._connect()
        conn.execute(
            """INSERT INTO messages (session_id, role, content, tool_call_id)
               VALUES (?, ?, ?, ?)""",
            (session_id, role, content, tool_call_id),
        )
        conn.commit()
        conn.close()

    async def sync(self) -> None:
        """Optimize FTS index."""
        conn = self._connect()
        conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('optimize')")
        conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('optimize')")
        conn.commit()
        conn.close()

    async def get_stats(self) -> dict[str, int]:
        """Return counts of indexed items."""
        conn = self._connect()
        msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        fact_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        conn.close()
        return {"messages": msg_count, "facts": fact_count}
