"""Session state management with JSONL persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from mainframe.config.paths import sessions_dir
from mainframe.providers.base import ContentBlock, Message, Role


@dataclass
class SessionMeta:
    session_id: str
    created_at: str
    updated_at: str
    title: str = "Untitled"
    turn_count: int = 0


class Session:
    """Manages conversation state and persistence."""

    def __init__(self, session_id: str | None = None, sessions_path: Path | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._sessions_path = sessions_path or sessions_dir()
        self._messages: list[Message] = []
        self._meta = SessionMeta(
            session_id=self.session_id,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        self._loaded = False

    @property
    def messages(self) -> list[Message]:
        return self._messages

    @property
    def meta(self) -> SessionMeta:
        return self._meta

    @property
    def session_file(self) -> Path:
        return self._sessions_path / f"{self.session_id}.jsonl"

    @property
    def meta_file(self) -> Path:
        return self._sessions_path / f"{self.session_id}.meta.json"

    def add_message(self, message: Message) -> None:
        self._messages.append(message)
        self._meta.updated_at = datetime.now(UTC).isoformat()
        if message.role == Role.USER:
            self._meta.turn_count += 1
            # Auto-title from first user message
            if self._meta.title == "Untitled" and isinstance(message.content, str):
                self._meta.title = message.content[:80]
        self._append_to_file(message)
        self._save_meta()

    def _serialize_message(self, msg: Message) -> dict:
        content = msg.content
        if isinstance(content, list):
            content = [
                {k: v for k, v in asdict(b).items() if v is not None}
                for b in content
            ]
        return {
            "role": msg.role.value,
            "content": content,
            "tool_call_id": msg.tool_call_id,
        }

    def _deserialize_message(self, data: dict) -> Message:
        content = data["content"]
        if isinstance(content, list):
            content = [ContentBlock(**b) for b in content]
        return Message(
            role=Role(data["role"]),
            content=content,
            tool_call_id=data.get("tool_call_id"),
        )

    def _append_to_file(self, message: Message) -> None:
        self._sessions_path.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, "a") as f:
            f.write(json.dumps(self._serialize_message(message)) + "\n")

    def _save_meta(self) -> None:
        with open(self.meta_file, "w") as f:
            json.dump(asdict(self._meta), f, indent=2)

    def load(self) -> bool:
        """Load session from disk. Returns True if session existed."""
        if not self.session_file.exists():
            return False

        self._messages = []
        with open(self.session_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    self._messages.append(self._deserialize_message(data))

        if self.meta_file.exists():
            with open(self.meta_file) as f:
                meta_data = json.load(f)
                self._meta = SessionMeta(**meta_data)

        self._loaded = True
        return True

    def compact(self, summary: str) -> None:
        """Replace conversation history with a single summary message and rewrite disk state."""
        summary_message = Message(
            role=Role.USER,
            content=(
                "[Context Summary — conversation history compacted to reduce token usage]\n\n"
                + summary
            ),
        )
        self._messages = [summary_message]
        self._meta.turn_count = 1
        self._meta.updated_at = datetime.now(UTC).isoformat()

        # Rewrite session file with only the summary
        self._sessions_path.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, "w") as f:
            f.write(json.dumps(self._serialize_message(summary_message)) + "\n")
        self._save_meta()

    @classmethod
    def list_sessions(cls, sessions_path: Path | None = None) -> list[SessionMeta]:
        """List all saved sessions, most recent first."""
        path = sessions_path or sessions_dir()
        sessions = []
        for meta_file in sorted(path.glob("*.meta.json"), reverse=True):
            with open(meta_file) as f:
                data = json.load(f)
                sessions.append(SessionMeta(**data))
        return sessions

    @classmethod
    def latest_session_id(cls, sessions_path: Path | None = None) -> str | None:
        """Get the most recently updated session ID."""
        sessions = cls.list_sessions(sessions_path)
        return sessions[0].session_id if sessions else None
