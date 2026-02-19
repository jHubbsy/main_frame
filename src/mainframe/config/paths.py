"""XDG-compliant path resolution for Mainframe."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "mainframe"


def config_dir() -> Path:
    """~/.config/mainframe/ (or XDG_CONFIG_HOME)."""
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    """~/.local/share/mainframe/ (or XDG_DATA_HOME)."""
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    """~/.cache/mainframe/ (or XDG_CACHE_HOME)."""
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file() -> Path:
    return config_dir() / "config.toml"


def credentials_db() -> Path:
    return data_dir() / "credentials.db"


def sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def skills_dir() -> Path:
    path = data_dir() / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def memory_db() -> Path:
    return data_dir() / "memory.db"
