"""Shared test fixtures for Mainframe."""

from __future__ import annotations

from pathlib import Path

import pytest

from mainframe.config.schema import MainframeConfig
from mainframe.core.session import Session


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config() -> MainframeConfig:
    return MainframeConfig()


@pytest.fixture
def session(tmp_dir: Path) -> Session:
    return Session(sessions_path=tmp_dir)
