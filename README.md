# Mainframe

A secure, extensible AI agent framework built in Python. Multi-turn conversational agent with tool execution, hybrid memory, a skill/action system, and web access — designed to be provider-agnostic.

## Features

**Agent Loop** — Turn-based conversation with automatic tool execution. The agent calls tools, processes results, and continues until it has a final answer.

**11 Builtin Tools**
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
| `connect_mcp` | Propose connecting to an MCP server (requires user approval) |

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
./install.sh
```

The script will install [pipx](https://pipx.pypa.io) if needed (via Homebrew on macOS), install mainframe into an isolated environment, and prompt you to set your API key. Once complete, `mainframe` and `computer` are available globally — no virtual environment activation required.

## Quick Start

```bash
mainframe chat    # interactive session
computer          # shortcut for the above
```

On first launch, Mainframe creates its data directories under `~/.local/share/mainframe/` and `~/.config/mainframe/`, initializes the memory stores, and drops you into an interactive REPL. Type a message, and the agent will respond — using tools autonomously as needed.

> **Note:** The first time memory is used, ChromaDB will download its embedding model (`all-MiniLM-L6-v2`, ~80MB) to `~/.cache/chroma/onnx_models/`. This is a one-time download — you'll see a progress bar in the terminal while it completes.

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

## CLI Reference

| Command | Description |
|---------|-------------|
| `mainframe chat` | Start an interactive chat session |
| `mainframe chat --resume` | Resume the most recent session |
| `mainframe chat --session-id <id>` | Resume a specific session |
| `mainframe chat --model <model>` | Override the model |
| `mainframe chat --no-tools` | Disable tool use |
| `mainframe chat --no-memory` | Disable memory indexing |
| `mainframe run <prompt>` | Run a single prompt and exit |
| `mainframe run <prompt> --raw` | Output raw text without formatting |
| `mainframe run <prompt> --no-tools` | Disable tool use |
| `mainframe auth login` | Set or update an API key (default: anthropic) |
| `mainframe auth login --provider <name>` | Set key for a specific provider (e.g. `brave`) |
| `mainframe auth logout` | Remove a stored API key |
| `mainframe auth status` | Show which providers have stored keys |
| `mainframe memory search <query>` | Search conversation history and facts |
| `mainframe memory search <query> --limit <n>` | Limit search results (default: 5) |
| `mainframe memory add <text>` | Add a fact to memory |
| `mainframe memory add <text> --source <label>` | Add with custom source label |
| `mainframe memory status` | Show memory system statistics |
| `mainframe skills list` | List all discovered skills |
| `mainframe skills install <path>` | Install a skill from a local directory |
| `mainframe skills inspect <path>` | Inspect a SKILL.md file |
| `mainframe skills audit` | Audit installed skills for security issues |
| `mainframe mcp list` | List configured MCP servers and their tools |
| `mainframe mcp test <server>` | Test connection to an MCP server |
| `mainframe --version` | Show version |
| `computer` | Shortcut for `mainframe chat` |

**In-session commands:** `/tools`, `/session`, `/quit`

## MCP Integration

Mainframe supports the [Model Context Protocol](https://modelcontextprotocol.io/) for connecting to external tool servers at runtime.

### Static Configuration

Pre-configure MCP servers in `~/.config/mainframe/config.toml`:

```toml
[mcp]
enabled = true

[mcp.servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_..." }

[mcp.servers.postgres]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
```

Configured servers are connected at startup, and their tools are automatically registered and allowed by policy.

### Dynamic Connection (Human-in-the-Loop)

The agent can propose connecting to MCP servers mid-conversation using the `connect_mcp` tool. This is a human-in-the-loop flow — no subprocess is spawned until you approve:

1. Agent calls `connect_mcp` with server name, command, args, and optional env vars
2. After the agent's turn, you're prompted: `Connect to MCP server 'github' (npx @modelcontextprotocol/server-github)? [y/N]`
3. If approved, Mainframe connects, discovers tools, registers them, and informs the agent
4. If denied, the agent is told the request was rejected

This prevents prompt injection from using MCP as an arbitrary command execution vector.

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
  core/          # Agent loop, session persistence, event bus, MCP client
  memory/        # SQLite FTS5, ChromaDB vectors, hybrid search
  providers/     # LLM provider abstraction (Anthropic SDK)
  security/      # Encrypted credential store
  skills/        # Manifest parser, loader, verifier, actions, registry
  tools/         # Tool protocol, registry, policy, 11 builtins, MCP adapter
```

## Development

```bash
source .venv/bin/activate
pytest tests/ -q       # Run tests
ruff check src/ tests/ # Lint
```
