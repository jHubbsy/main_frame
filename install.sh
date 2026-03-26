#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RESET='\033[0m'

info()    { echo -e "${BLUE}==>${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}!${RESET} $*"; }
die()     { echo -e "${RED}Error:${RESET} $*" >&2; exit 1; }

# Verify we're in the repo root
[[ -f "pyproject.toml" ]] || die "Run this script from the mainframe repo root."

command -v python3 >/dev/null 2>&1 || die "python3 is required."

# Install pipx if missing
if ! command -v pipx >/dev/null 2>&1; then
    info "pipx not found, installing..."
    if command -v brew >/dev/null 2>&1; then
        brew install pipx
    elif python3 -m pip install --user pipx 2>/dev/null; then
        true
    else
        die "Could not install pipx. Install manually: https://pipx.pypa.io"
    fi
    success "pipx installed"
fi

# Install mainframe
info "Installing mainframe..."
if pipx list 2>/dev/null | grep -q "mainframe"; then
    warn "mainframe already installed — reinstalling"
    pipx reinstall mainframe
else
    pipx install -e .
fi

pipx ensurepath
success "'mainframe' and 'computer' are now available"

# Optional extras — parse from pyproject.toml and prompt for each
echo
info "Optional integrations:"
extras_json=$(python3 - <<'PYEOF'
import sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # fallback for older Python
    except ImportError:
        print("[]")
        sys.exit(0)
import json

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)

opt_deps = data.get("project", {}).get("optional-dependencies", {})
extras_meta = data.get("tool", {}).get("mainframe", {}).get("extras", {})

result = []
for name, pkgs in opt_deps.items():
    if name == "dev":
        continue
    meta = extras_meta.get(name, {})
    result.append({
        "name": name,
        "description": meta.get("description", name),
        "packages": pkgs,
    })
print(json.dumps(result))
PYEOF
)

extras_count=$(python3 -c "import json,sys; print(len(json.loads(sys.argv[1])))" "$extras_json")

if [[ "$extras_count" -eq 0 ]]; then
    info "No optional integrations declared."
else
    while IFS=$'\t' read -r name description; do
        read -rp "  Install '$name' — $description? [y/N] " choice
        if [[ "${choice:-N}" =~ ^[Yy]$ ]]; then
            pipx inject mainframe ".[${name}]"
            success "Installed '$name' extra"
        fi
    done < <(python3 - <<PYEOF
import json, sys
extras = json.loads("""$extras_json""")
for e in extras:
    print(e["name"] + "\t" + e["description"])
PYEOF
)
fi

# Auth setup
echo
read -rp "Set up your provider API key now? [Y/n] " setup_auth
if [[ "${setup_auth:-Y}" =~ ^[Yy]$ ]]; then
    mainframe auth login
fi

echo
success "Done. Run 'mainframe chat' or 'computer' to start."
success "Run 'mainframe extras' to check integration status at any time."
warn "If commands are not found, restart your shell or run: source ~/.zshrc"
