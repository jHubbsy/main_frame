# Mainframe — Project Context

## What This Is
Clean-room Python AI agent inspired by OpenClaw. Preserves good ideas (multi-turn agent loop, skill system, hybrid memory, provider abstraction), fixes security model, strips to essentials. Learning project.

## Implementation Status

| Phase | Goal | Status |
|-------|------|--------|
| 1 | Foundation — "It talks back" | **Done** |
| 2 | Tool System — "It can do things" | **Done** |
| 3 | Memory — "It remembers" | **Done** |
| 4 | Skills — "It's extensible" | **Done** |
| 4.5 | Executable Actions + Agent Authoring | **Done** |
| 5 | Multi-Provider + Polish | **Next** |

## Key Decisions Made
- Python 3.14 (system has 3.14, not 3.12)
- Machine-derived Fernet key for credential encryption (no master password — fully automated)
- `getpass` masked prompt on first run for API key, encrypted to disk
- Agent loop uses `complete()` (not streaming) for tool calls for reliable parsing
- `computer` is a shortcut entrypoint that launches `mainframe chat` directly
- Distribution: exploring pipx/PyPI but not set up yet (homebrew Python blocks global pip installs via PEP 668)

## Architecture
- `providers/base.py` — Protocol-based provider abstraction with shared types
- `providers/anthropic.py` — Claude SDK wrapper (streaming + non-streaming)
- `core/agent.py` — Turn-based loop: provider.complete() → tool execution → feed results → repeat until end_turn
- `core/session.py` — JSONL persistence, session resume
- `core/events.py` — Typed EventBus (BeforeToolCall, AfterToolCall, TextDelta, etc.)
- `tools/` — Tool protocol, registry, policy (allow/deny + permission groups), 8 builtins
- `security/credentials.py` — Fernet-encrypted credential store, auto machine key, no password needed
  - **Future hardening:** migrate to macOS Keychain (`keyring` package) so credentials are protected even if the agent is hijacked — current file-based master key is readable by any process running as the same user
- `cli/` — Click entrypoint, chat REPL (prompt_toolkit + rich), single-shot run, auth management
- `memory/` — SQLite FTS5 + ChromaDB vector search, RRF hybrid merge, MemoryManager
- `skills/` — SKILL.md manifests, YAML frontmatter, ed25519 verification, tiered sandbox, action system

## Phase 4.5: Executable Actions + Agent Authoring
- `skills/actions.py` — SkillAction wrapper, discover_actions() loads Python modules from actions/ dirs
- `skills/registry.py` — discovers actions at load, registers them as tools, validates `requires` deps
- `tools/builtins/create_skill.py` — agent can draft new skills (SKILL.md + action files) on disk
- `config/schema.py` — per-skill config overrides via `[skills.skill-name]` in config.toml
- `skills/github/actions/list_prs.py` — example action using gh CLI
- Skill actions are namespaced as `skill_name:action_name` (e.g. `github:list_prs`)

## Phase 5 Plan: Multi-Provider + Polish
- `providers/openai_compat.py` — OpenAI SDK wrapper with tool format translation
- `security/audit.py` — `mainframe security audit`
- `security/sanitize.py` — prompt injection defenses
- `tools/builtins/web_fetch.py` — HTTP GET with html2text
- Session management CLI
- Shell completions, comprehensive test suite
- Done when: `mainframe chat --provider ollama --model llama3.3` works

## Running
```bash
cd /Users/justinhubbell/CODE/main_frame
source .venv/bin/activate
mainframe chat        # interactive
mainframe run "prompt" # single-shot
computer              # shortcut for mainframe chat
mainframe auth login  # set/update API key
mainframe auth status # check stored keys
```

## Testing
```bash
source .venv/bin/activate
pytest tests/ -q       # 39 tests
ruff check src/ tests/ # lint
```
