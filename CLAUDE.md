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
| 6 | MCP Integration — "It connects to everything" | Planned |

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
- `tools/` — Tool protocol, registry, policy (allow/deny + permission groups), 10 builtins
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
- Skill actions are namespaced as `skill_name__action_name` (e.g. `github__list_prs`)

## Phase 5 Plan: Multi-Provider + Polish
- `providers/openai_compat.py` — OpenAI SDK wrapper with tool format translation
- `security/audit.py` — `mainframe security audit`
- `security/sanitize.py` — prompt injection defenses
- `tools/builtins/web_fetch.py` — HTTP GET with html2text (**Done**)
- `tools/builtins/web_search.py` — Brave Search API (**Done**)
- Session management CLI
- Shell completions, comprehensive test suite
- Done when: `mainframe chat --provider ollama --model llama3.3` works

## Phase 6 Plan: MCP Integration
- `core/mcp_client.py` — AsyncExitStack-managed connections to MCP servers (stdio + streamable HTTP)
- `tools/mcp_adapter.py` — Wraps discovered MCP tools as Mainframe `Tool` objects (schema mapping is ~1:1)
- Config: `[[mcp.servers]]` sections in config.toml (name, command/args for stdio, url/headers for HTTP)
- Startup: connect to configured servers, discover tools, register in tool registry, auto-allow in policy
- `cli/commands/mcp.py` — `mainframe mcp list` (servers + tools), `mainframe mcp test <server>`
- Optional: expose Mainframe as an MCP server via `FastMCP` (memory, skills, builtins available to external clients)
- Dependency: `mcp>=1.0.0`
- Done when: `mainframe chat` can use tools from a configured MCP server (e.g. `mcp-server-postgres`)

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
pytest tests/ -q       # 43 tests
ruff check src/ tests/ # lint
```
