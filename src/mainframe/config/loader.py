"""TOML config loading with environment variable overlay."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from mainframe.config.paths import config_file
from mainframe.config.schema import MainframeConfig


def load_config(path: Path | None = None) -> MainframeConfig:
    """Load config from TOML file, then overlay environment variables."""
    path = path or config_file()

    data: dict = {}
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)

    config = MainframeConfig(**data)

    # Environment variable overlays
    if model := os.environ.get("MAINFRAME_MODEL"):
        config.provider.model = model
    if provider := os.environ.get("MAINFRAME_PROVIDER"):
        config.provider.name = provider
    if base_url := os.environ.get("MAINFRAME_BASE_URL"):
        config.provider.base_url = base_url

    return config
