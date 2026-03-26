# AFFiNE Integration Guide

This guide explains how to connect your Mainframe AI agent to an [AFFiNE](https://affine.pro) workspace using the official Model Context Protocol (MCP) server.

## Overview

The `affine-mcp-server` exposes AFFiNE's functionalities (such as creating workspaces, reading/writing documents, and appending markdown) via a comprehensive API, allowing Mainframe to interact with your knowledge base autonomously.

This integration connects with [AFFiNE](https://github.com/toeverything/AFFiNE), an open-source knowledge workspace, utilizing the [affine-mcp-server](https://github.com/DAWNCR0W/affine-mcp-server).

## Prerequisites

Before configuring the server, ensure you meet the following requirements:

1. **Node.js**: Version 18 or higher is required to run the `affine-mcp-server` package via `npx`.
2. **AFFiNE Instance**: You must have an active AFFiNE instance. The server supports both:
   - **Cloud-hosted** (e.g., `app.affine.pro`)
   - **Self-hosted** (e.g., via local Docker Compose)

## Authentication

Before Mainframe can access your workspace, you must authenticate the MCP server interactively:

```bash
npx -y affine-mcp-server login
```

- **For Cloud**: Follow the prompts to log in (email/password or API token). By default, it will prompt you for `https://app.affine.pro`.
- **For Self-Hosted**: When prompted for the "Affine URL", replace the default URL with your self-hosted instance URL (e.g., `http://localhost:3010`), then proceed to log in with your local credentials.

The server will store your tokens locally in `~/.config/affine-mcp/config`.

## Agent Configuration

Once authenticated, add the server to your local Mainframe configuration file at `~/.config/mainframe/config.toml`:

```toml
[mcp]
enabled = true

[mcp.servers.affine]
command = "npx"
args = ["-y", "affine-mcp-server"]
```

Configured servers are connected at startup, and their 60+ AFFiNE tools are automatically registered and allowed by the agent framework's policy.
