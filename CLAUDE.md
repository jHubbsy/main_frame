# Mainframe — Project Context

## What This Is
Clean-room Python AI agent inspired by OpenClaw. Preserves good ideas (multi-turn agent loop, skill system, hybrid memory, provider abstraction), fixes security model, strips to essentials. Learning project.

## Implementation Status

| Phase | Goal | Status |
|-------|------|--------|
| 1 | Foundation — "It talks back" | **Done** |
| 2 | Tool System — "It can do things" | **Done** |
| 3 | Memory — "It remembers" | **Next** |
| 4 | Skills — "It's extensible" | Pending |
| 5 | Multi-Provider + Polish | Pending |

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
- `tools/` — Tool protocol, registry, policy (allow/deny + permission groups), 6 builtins
- `security/credentials.py` — Fernet-encrypted credential store, auto machine key, no password needed
- `cli/` — Click entrypoint, chat REPL (prompt_toolkit + rich), single-shot run, auth management

## Phase 3 Plan: Memory
- `memory/sqlite_store.py` — SQLite FTS5 keyword search over transcripts/facts
- `memory/vector_store.py` — ChromaDB embedded semantic search
- `memory/hybrid.py` — Reciprocal Rank Fusion merge
- `memory/manager.py` — file indexing, chunking, embedding, change detection
- `tools/builtins/memory_search.py` — agent-callable memory search tool
- Session compaction (summarize old messages near context limit)
- `cli/commands/memory.py` — `mainframe memory search`, `mainframe memory status`
- Done when: "what did we discuss yesterday about auth" returns a relevant answer

## Phase 4 Plan: Skills
- `skills/manifest.py` — SkillManifest, YAML frontmatter parser (SKILL.md)
- `skills/loader.py` — disk discovery
- `skills/verifier.py` — ed25519 signature verification
- `skills/registry.py` — installed skills catalog, system prompt injection
- `skills/sandbox.py` — Tier 1 (RestrictedPython + subprocess), Tier 2 (container)
- `cli/commands/skills.py` — install, list, audit

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
pytest tests/ -q       # 22 tests
ruff check src/ tests/ # lint
```
