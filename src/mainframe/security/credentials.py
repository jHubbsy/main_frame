"""Encrypted credential store using Fernet (AES-128-CBC + HMAC).

Machine-local Fernet key (auto-generated, chmod 600) encrypts all credentials.
Storage: SQLite with individual Fernet-encrypted values.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import stat
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from mainframe.config.paths import credentials_db
from mainframe.core.errors import CredentialError


class CredentialStore:
    """Encrypted credential storage backed by SQLite."""

    def __init__(self, db_path: Path | None = None, master_key: bytes | None = None):
        self._db_path = db_path or credentials_db()
        self._fernet: Fernet | None = None

        if master_key:
            self._fernet = Fernet(master_key)

        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                key_name TEXT PRIMARY KEY,
                encrypted_value BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        self._enforce_permissions()

    def _enforce_permissions(self) -> None:
        """Ensure credential DB is owner-only (chmod 600)."""
        with contextlib.suppress(OSError):
            self._db_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def _require_unlocked(self) -> Fernet:
        if self._fernet is None:
            raise CredentialError("Credential store is locked.")
        return self._fernet

    @property
    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def set(self, key_name: str, value: str) -> None:
        """Store an encrypted credential."""
        fernet = self._require_unlocked()
        encrypted = fernet.encrypt(value.encode())
        now = datetime.now(UTC).isoformat()

        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT INTO credentials (key_name, encrypted_value, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key_name) DO UPDATE SET encrypted_value=?, updated_at=?""",
            (key_name, encrypted, now, now, encrypted, now),
        )
        conn.commit()
        conn.close()

    def get(self, key_name: str) -> str | None:
        """Retrieve and decrypt a credential. Returns None if not found."""
        fernet = self._require_unlocked()

        conn = sqlite3.connect(self._db_path)
        row = conn.execute(
            "SELECT encrypted_value FROM credentials WHERE key_name = ?", (key_name,)
        ).fetchone()
        conn.close()

        if row is None:
            return None

        try:
            return fernet.decrypt(row[0]).decode()
        except InvalidToken as e:
            raise CredentialError(
                f"Failed to decrypt '{key_name}': corrupt or wrong key"
            ) from e

    def delete(self, key_name: str) -> bool:
        """Delete a credential. Returns True if it existed."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute("DELETE FROM credentials WHERE key_name = ?", (key_name,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def list_keys(self) -> list[str]:
        """List all stored credential keys (not values)."""
        conn = sqlite3.connect(self._db_path)
        rows = conn.execute(
            "SELECT key_name FROM credentials ORDER BY key_name"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]

    def has_credentials(self) -> bool:
        """Check if any credentials are stored."""
        conn = sqlite3.connect(self._db_path)
        row = conn.execute("SELECT COUNT(*) FROM credentials").fetchone()
        conn.close()
        return row[0] > 0


# --- Machine key management ---

def _machine_key_path() -> Path:
    """Path to the machine-derived Fernet key file."""
    return credentials_db().parent / ".master.key"


def _get_or_create_machine_key() -> bytes:
    """Get or generate a machine-local Fernet key (chmod 600)."""
    key_path = _machine_key_path()
    if key_path.exists():
        return key_path.read_bytes().strip()

    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    with contextlib.suppress(OSError):
        key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return key


def _get_credential_store() -> CredentialStore:
    """Get a credential store unlocked with the machine key."""
    key = _get_or_create_machine_key()
    return CredentialStore(master_key=key)


# --- Public API ---

def get_api_key(provider: str = "anthropic") -> str | None:
    """Get API key from environment variable (preferred) or credential store.

    Environment variables checked first:
    - MAINFRAME_ANTHROPIC_API_KEY / ANTHROPIC_API_KEY
    - MAINFRAME_{PROVIDER}_API_KEY / {PROVIDER}_API_KEY

    Then falls back to the encrypted credential store.
    """
    env_keys = [
        f"MAINFRAME_{provider.upper()}_API_KEY",
        f"{provider.upper()}_API_KEY",
    ]
    for key in env_keys:
        if value := os.environ.get(key):
            return value

    try:
        store = _get_credential_store()
        return store.get(f"{provider}_api_key")
    except Exception:
        return None


def store_api_key(provider: str, api_key: str) -> None:
    """Encrypt and store an API key. Overwrites any existing key for this provider."""
    store = _get_credential_store()
    store.set(f"{provider}_api_key", api_key)


def update_api_key(provider: str, new_api_key: str) -> bool:
    """Replace an existing API key. Deletes the old one first to avoid conflicts.

    Returns True if an old key was replaced, False if this is a new key.
    """
    store = _get_credential_store()
    key_name = f"{provider}_api_key"
    existed = store.delete(key_name)
    store.set(key_name, new_api_key)
    return existed


def delete_api_key(provider: str) -> bool:
    """Remove a stored API key. Returns True if it existed."""
    store = _get_credential_store()
    return store.delete(f"{provider}_api_key")


def list_stored_providers() -> list[str]:
    """List providers that have stored API keys."""
    store = _get_credential_store()
    keys = store.list_keys()
    return [k.removesuffix("_api_key") for k in keys if k.endswith("_api_key")]
