# Mainframe

A secure, extensible AI agent framework built in Python. Multi-turn conversational agent with tool execution, hybrid memory, a skill/action system, and web access — designed to be provider-agnostic.

## Features

**Agent Loop** — Turn-based conversation with automatic tool execution. The agent calls tools, processes results, and continues until it has a final answer.

**10 Builtin Tools**
| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands |
| `read_file` | Read file contents with line numbers |
| `write_file` | Create or overwrite files |
| `edit_file` | Find-and-replace edits in existing files |
| `glob_search` | Find files by glob pattern |
| `grep_search` | Search file contents with regex |
| `memory_search` | Query conversation history and stored facts |
| `create_skill` | Agent-authored skill generation |
| `web_fetch` | HTTP GET with HTML-to-markdown conversion |
| `web_search` | Web search via Brave Search API |

**Hybrid Memory** — SQLite FTS5 keyword search + ChromaDB vector search, merged via Reciprocal Rank Fusion. Conversations are automatically indexed.

**Skill System** — Extensible via `SKILL.md` manifests with YAML frontmatter. Skills can declare permissions, sandbox tiers, ed25519 signatures, and expose executable actions as namespaced tools (e.g. `github:list_prs`).

**Security**
- Fernet-encrypted credential store with auto-generated machine key
- Tool permission policies (allow/deny lists, permission groups)
- Tiered skill sandboxing
- Skill signature verification and security auditing

## Prerequisites

- Python 3.12+
- An Anthropic API key (other providers planned)
- Brave Search API key (optional, for `web_search`)

## Installation

```bash
git clone git@github.com:jHubbsy/main_frame.git
cd main_frame
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Setup

Set your API key (encrypted to disk on first run):

```bash
mainframe auth login
# Enter your Anthropic API key when prompted
```

Optionally set up Brave Search:

```bash
mainframe auth login --provider brave
```

Or use environment variables:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export BRAVE_API_KEY="BSA..."
```

Check stored credentials:

```bash
mainframe auth status
```

## Usage

### Interactive Chat

```bash
mainframe chat
# or use the shortcut:
computer
```

**Chat options:**
```bash
mainframe chat --resume            # Resume last session
mainframe chat --session-id <id>   # Resume specific session
mainframe chat --model <model>     # Override model
mainframe chat --no-tools          # Disable tool use
mainframe chat --no-memory         # Disable memory indexing
```

**In-session commands:** `/tools`, `/session`, `/quit`

### Single-Shot

```bash
mainframe run "list all Python files in src/"
mainframe run "explain this error" --raw     # Unformatted output
```

### Memory

```bash
mainframe memory search "authentication"
mainframe memory add "project uses JWT tokens"
mainframe memory status
```

### Skills

```bash
mainframe skills list
mainframe skills install ./my-skill
mainframe skills inspect ./my-skill
mainframe skills audit
```

## Configuration

Config file at `~/.config/mainframe/config.toml`:

```toml
[provider]
name = "anthropic"
model = "claude-sonnet-4-20250514"

[security]
allowed_tool_groups = ["builtin"]

# Per-skill config overrides
[skills.my-skill]
api_url = "https://example.com"
```

## Project Structure

```
src/mainframe/
  cli/           # Click CLI, chat REPL, display formatting
  config/        # Config schema, loader, paths
  core/          # Agent loop, session persistence, event bus
  memory/        # SQLite FTS5, ChromaDB vectors, hybrid search
  providers/     # LLM provider abstraction (Anthropic SDK)
  security/      # Encrypted credential store
  skills/        # Manifest parser, loader, verifier, actions, registry
  tools/         # Tool protocol, registry, policy, 10 builtins
```

## Development

```bash
source .venv/bin/activate
pytest tests/ -q       # Run tests
ruff check src/ tests/ # Lint
```
