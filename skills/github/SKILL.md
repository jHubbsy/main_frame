---
name: github
version: "1.0.0"
description: "GitHub operations via the gh CLI"
sandbox_tier: 1
permissions:
  bins: ["gh"]
  network: true
  filesystem:
    read: ["$WORKSPACE"]
    write: []
publisher: "mainframe-official"
---
# GitHub Skill

You can use the `gh` CLI to interact with GitHub. Common operations:

## Pull Requests
- `gh pr list` — list open PRs
- `gh pr view <number>` — view PR details
- `gh pr create --title "..." --body "..."` — create a PR
- `gh pr checkout <number>` — check out a PR branch
- `gh pr merge <number>` — merge a PR

## Issues
- `gh issue list` — list open issues
- `gh issue view <number>` — view issue details
- `gh issue create --title "..." --body "..."` — create an issue

## Repository
- `gh repo view` — view repo info
- `gh repo clone <owner/repo>` — clone a repo

## API
- `gh api repos/{owner}/{repo}/pulls` — raw API access

Always use the `bash` tool with `gh` commands. Check that `gh` is authenticated first with `gh auth status`.
