#!/usr/bin/env bash
set -euo pipefail

# Discord webhook notification sender using embeds.
# Requires DISCORD_WEBHOOK_URL environment variable.

# --- Defaults ---
TYPE="info"
TITLE=""
USERNAME="Claude Code"
MESSAGE=""

# --- Color map ---
color_for_type() {
  case "$1" in
    info)       echo 3447003  ;;  # blue
    status)     echo 16776960 ;;  # yellow
    completion) echo 3066993  ;;  # green
    error)      echo 15158332 ;;  # red
    *) echo "Unknown type: $1" >&2; exit 1 ;;
  esac
}

# --- Default title ---
title_for_type() {
  case "$1" in
    info)       echo "Info"       ;;
    status)     echo "Status"     ;;
    completion) echo "Completed"  ;;
    error)      echo "Error"      ;;
  esac
}

# --- Parse args ---
require_value() {
  local flag="$1" remaining="$2"
  if [[ "$remaining" -lt 2 ]]; then
    echo "Error: $flag requires a value" >&2
    echo "Usage: send-discord.sh [--type info|status|completion|error] [--title TITLE] [--username NAME] MESSAGE" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type|-t)     require_value "$1" "$#"; TYPE="$2";     shift 2 ;;
    --title|-T)    require_value "$1" "$#"; TITLE="$2";    shift 2 ;;
    --username|-u) require_value "$1" "$#"; USERNAME="$2"; shift 2 ;;
    -*)            echo "Unknown option: $1" >&2; exit 1 ;;
    *)             MESSAGE="$1";  shift ;;
  esac
done

# --- Validate ---
if [[ -z "${DISCORD_WEBHOOK_URL:-}" ]]; then
  echo "Error: DISCORD_WEBHOOK_URL environment variable is not set." >&2
  exit 1
fi

if [[ -z "$MESSAGE" ]]; then
  echo "Error: No message provided." >&2
  echo "Usage: send-discord.sh [--type info|status|completion|error] [--title TITLE] [--username NAME] MESSAGE" >&2
  exit 1
fi

COLOR=$(color_for_type "$TYPE")
EMBED_TITLE="${TITLE:-$(title_for_type "$TYPE")}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# --- Build JSON safely with jq ---
PAYLOAD=$(jq -n \
  --arg username "$USERNAME" \
  --arg title "$EMBED_TITLE" \
  --arg description "$MESSAGE" \
  --argjson color "$COLOR" \
  --arg footer "Sent by $USERNAME" \
  --arg timestamp "$TIMESTAMP" \
  '{
    username: $username,
    embeds: [{
      title: $title,
      description: $description,
      color: $color,
      footer: { text: $footer },
      timestamp: $timestamp
    }]
  }')

# --- Send ---
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$DISCORD_WEBHOOK_URL")

if [[ "$HTTP_CODE" -ge 200 && "$HTTP_CODE" -lt 300 ]]; then
  echo "Sent ($HTTP_CODE)"
else
  echo "Error: Discord returned HTTP $HTTP_CODE" >&2
  exit 1
fi
