# Contributing to Mainframe

## Adding an Optional Integration

Optional integrations (e.g. Telegram, Slack, Discord) follow a standard pattern so they are auto-detected by `install.sh` and surfaced by `mainframe extras`.

### 1. Declare the extra in `pyproject.toml`

Add your dependencies under `[project.optional-dependencies]` and a matching metadata block:

```toml
[project.optional-dependencies]
yourfeature = [
    "some-package>=1.0",
]

[tool.mainframe.extras.yourfeature]
description = "Brief description shown during install (mention required env vars/tokens)"
check_package = "some-package"   # canonical PyPI name used to detect if it's installed
```

`check_package` must match what `importlib.metadata.version()` expects (PyPI name, not import name).

### 2. Lazy-import inside the command handler

Never import optional dependencies at module top level. Import inside the Click command body with a user-friendly fallback:

```python
@click.command(name="yourfeature")
def yourfeature() -> None:
    """Your feature description."""
    try:
        import some_package
    except ImportError:
        print_error("yourfeature integration is not installed.")
        print_info("Install it with: pipx inject mainframe '.[yourfeature]'")
        sys.exit(1)
    # ... rest of command
```

### 3. Register in `cli/app.py`

Import and add your command:

```python
from mainframe.cli.commands.yourfeature import yourfeature
# ...
cli.add_command(yourfeature)
```

### Checklist

- [ ] `[project.optional-dependencies]` entry in `pyproject.toml`
- [ ] `[tool.mainframe.extras.<name>]` metadata block with `description` and `check_package`
- [ ] Optional library imported lazily inside command handler (not at module top)
- [ ] Graceful `ImportError` with install hint
- [ ] Command registered in `cli/app.py`

### Verifying your integration

After implementing, run:

```bash
mainframe extras
```

Your extra should appear with status `✗ missing` (before install) or `✓ installed` (after). If it shows `? no metadata`, the `[tool.mainframe.extras.<name>]` block is missing.
