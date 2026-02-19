"""Tests for credential store."""

from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

from mainframe.security.credentials import CredentialStore


def _make_store(tmp_path: Path) -> CredentialStore:
    key = Fernet.generate_key()
    return CredentialStore(db_path=tmp_path / "creds.db", master_key=key)


def test_credential_roundtrip(tmp_path: Path):
    store = _make_store(tmp_path)
    store.set("api_key", "sk-secret")
    assert store.get("api_key") == "sk-secret"


def test_credential_delete(tmp_path: Path):
    store = _make_store(tmp_path)
    store.set("key", "val")
    assert store.delete("key") is True
    assert store.get("key") is None


def test_credential_update_overwrites(tmp_path: Path):
    store = _make_store(tmp_path)
    store.set("key", "old_value")
    store.set("key", "new_value")
    assert store.get("key") == "new_value"


def test_credential_list_keys(tmp_path: Path):
    store = _make_store(tmp_path)
    store.set("a_key", "val1")
    store.set("b_key", "val2")
    assert store.list_keys() == ["a_key", "b_key"]
