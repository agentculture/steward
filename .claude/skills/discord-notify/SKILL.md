---
name: discord-notify
description: >
  Send notifications to Discord via webhook. Use when: a long task completes,
  an error needs attention, the user says "notify me", "ping me", "let me know",
  "send to discord", or "update me when done".
---

# Discord Notify

Send a message to a Discord channel using a webhook embed.

## When to Use

- A long-running task finishes (build, deploy, migration)
- An error occurs that the user should know about
- The user explicitly asks to be notified

## Prerequisites

The script requires the following tools on `PATH`:

- `bash`
- `curl` — sends the webhook POST
- `jq` — builds the JSON payload safely

## Environment

Set `DISCORD_WEBHOOK_URL` to a Discord webhook URL before use.

## Usage

```bash
# Basic info message
bash .claude/skills/discord-notify/scripts/send-discord.sh "Build passed"

# Completion (green)
bash .claude/skills/discord-notify/scripts/send-discord.sh --type completion "Deploy finished"

# Error (red)
bash .claude/skills/discord-notify/scripts/send-discord.sh --type error "Tests failed on main"

# Status update (yellow)
bash .claude/skills/discord-notify/scripts/send-discord.sh --type status "Migration running — 3/10 tables done"

# Custom title
bash .claude/skills/discord-notify/scripts/send-discord.sh --type completion --title "CI Pipeline" "All checks green"

# Different sender identity
bash .claude/skills/discord-notify/scripts/send-discord.sh --username "Codex" "Task complete"
```

## Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--type` | `-t` | `info` | `info` (blue), `status` (yellow), `completion` (green), `error` (red) |
| `--title` | `-T` | auto | Override the embed title |
| `--username` | `-u` | `Claude Code` | Sender name shown in Discord |
