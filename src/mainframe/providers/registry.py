"""Provider discovery and instantiation."""

from __future__ import annotations

import getpass

from mainframe.config.schema import ProviderConfig
from mainframe.core.errors import AuthenticationError, ConfigError
from mainframe.providers.anthropic import AnthropicProvider
from mainframe.providers.base import Provider
from mainframe.security.credentials import get_api_key, store_api_key


def _prompt_for_api_key(provider: str) -> str | None:
    """Prompt user for API key via masked input. Returns None if cancelled."""
    print(f"\nNo {provider} API key found.")
    print("Enter your API key below (input is hidden).\n")
    try:
        key = getpass.getpass(f"{provider} API key: ")
    except (EOFError, KeyboardInterrupt):
        return None
    key = key.strip()
    if not key:
        return None
    store_api_key(provider, key)
    print("API key saved.\n")
    return key


def create_provider(config: ProviderConfig) -> Provider:
    """Create a provider instance from config."""
    if config.name == "anthropic":
        api_key = get_api_key("anthropic")
        if not api_key:
            api_key = _prompt_for_api_key("anthropic")
        if not api_key:
            raise AuthenticationError(
                "No Anthropic API key provided. Run mainframe again to retry."
            )
        return AnthropicProvider(api_key=api_key, model=config.model)

    raise ConfigError(f"Unknown provider: {config.name}")
