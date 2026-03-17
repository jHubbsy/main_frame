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

# Auth setup
echo
read -rp "Set up your provider API key now? [Y/n] " setup_auth
if [[ "${setup_auth:-Y}" =~ ^[Yy]$ ]]; then
    mainframe auth login
fi

echo
success "Done. Run 'mainframe chat' or 'computer' to start."
warn "If commands are not found, restart your shell or run: source ~/.zshrc"
