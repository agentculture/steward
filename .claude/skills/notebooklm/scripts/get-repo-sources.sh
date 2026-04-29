#!/usr/bin/env bash
# get-repo-sources — Generate GitHub URLs for repo docs, ready for NotebookLM
set -euo pipefail

# --- Defaults ---
INCLUDE_ALL=false
PLAIN=false
BRANCH=""

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)       INCLUDE_ALL=true; shift ;;
    --plain)     PLAIN=true; shift ;;
    --branch)    BRANCH="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: get-repo-sources.sh [--all] [--plain] [--branch NAME]"
      echo "  --all      Include plans, specs, and changelogs"
      echo "  --plain    Output plain URLs only (no headers)"
      echo "  --branch   Override branch (default: auto-detect)"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- Detect repo root ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2; exit 1
}
cd "$REPO_ROOT"

# --- Detect GitHub URL ---
REMOTE_URL="$(git remote get-url origin 2>/dev/null)" || {
  echo "Error: no 'origin' remote found" >&2; exit 1
}

# Normalise to https://github.com/OWNER/REPO
GITHUB_URL="$REMOTE_URL"
GITHUB_URL="${GITHUB_URL%.git}"
if [[ "$GITHUB_URL" == git@github.com:* ]]; then
  GITHUB_URL="https://github.com/${GITHUB_URL#git@github.com:}"
fi

# --- Detect branch ---
if [[ -z "$BRANCH" ]]; then
  BRANCH="$(git branch --show-current 2>/dev/null || echo "main")"
fi

BASE_URL="${GITHUB_URL}/blob/${BRANCH}"

# --- Collect all .md files from remote branch (only files that exist on GitHub) ---
ALL_FILES=$(git ls-tree -r --name-only "origin/${BRANCH}" 2>/dev/null \
  | grep '\.md$' \
  | grep -v -E '^(\.github/|\.claude/|\.pytest_cache/|node_modules/|\.venv/|__pycache__/|\.mypy_cache/)' \
  | sort)

# --- Filter ---
filter_file() {
  local f="$1"
  # Always exclude dot-dirs and lock files
  [[ "$f" == .github/* ]] && return 1

  if [[ "$INCLUDE_ALL" == "false" ]]; then
    # Exclude plans, specs, changelogs by default
    [[ "$f" == *superpowers/plans/* ]] && return 1
    [[ "$f" == *superpowers/specs/* ]] && return 1
    [[ "$f" == CHANGELOG.md ]] && return 1
  fi
  return 0
}

FILTERED=()
for f in $ALL_FILES; do
  if filter_file "$f"; then
    FILTERED+=("$f")
  fi
done

if [[ ${#FILTERED[@]} -eq 0 ]]; then
  echo "No documentation files found." >&2
  exit 1
fi

# --- Categorise ---
declare -a CAT_CORE=() CAT_ARCH=() CAT_START=() CAT_FEATURES=() CAT_PROTOCOL=()
declare -a CAT_CLIENTS=() CAT_USECASES=() CAT_PACKAGES=() CAT_PLANS=() CAT_SPECS=() CAT_OTHER=()

categorise() {
  local f="$1"
  local base
  base="$(basename "$f")"

  # Path-based categories first (more specific)
  case "$f" in
    *protocol/*)         CAT_PROTOCOL+=("$f"); return ;;
    *clients/*)          CAT_CLIENTS+=("$f"); return ;;
    *use-cases/*)        CAT_USECASES+=("$f"); return ;;
    *packages/*)         CAT_PACKAGES+=("$f"); return ;;
    *superpowers/plans*) CAT_PLANS+=("$f"); return ;;
    *superpowers/specs*) CAT_SPECS+=("$f"); return ;;
    *plugins/*)          CAT_OTHER+=("$f"); return ;;
    *skills/*)           CAT_OTHER+=("$f"); return ;;
  esac

  # Root-level core files (only match files at repo root)
  case "$f" in
    README.md|CLAUDE.md|index.md) CAT_CORE+=("$f"); return ;;
    CHANGELOG.md)                 CAT_OTHER+=("$f"); return ;;
  esac

  # By filename keywords
  case "$base" in
    layer*|overview*|design*|server-architecture*|*-spec*)
      CAT_ARCH+=("$f"); return ;;
    getting-started*|cli*|grow-your-agent*)
      CAT_START+=("$f"); return ;;
    *) ;;
  esac

  # Docs directory features
  if [[ "$f" == docs/* ]]; then
    CAT_FEATURES+=("$f")
  else
    CAT_OTHER+=("$f")
  fi
}

for f in "${FILTERED[@]}"; do
  categorise "$f"
done

# --- Output ---
print_urls() {
  local label="$1"; shift
  local -n arr=$1

  if [[ ${#arr[@]} -eq 0 ]]; then return; fi

  if [[ "$PLAIN" == "false" ]]; then
    echo ""
    echo "--- ${label} ---"
  fi
  for f in "${arr[@]}"; do
    echo "${BASE_URL}/${f}"
  done
}

if [[ "$PLAIN" == "false" ]]; then
  echo "=== Documentation Links for NotebookLM ==="
  echo "Repository: ${GITHUB_URL}"
  echo "Branch: ${BRANCH}"
  echo "Files: ${#FILTERED[@]}"
fi

print_urls "Core"           CAT_CORE
print_urls "Architecture"   CAT_ARCH
print_urls "Getting Started" CAT_START
print_urls "Features"       CAT_FEATURES
print_urls "Protocol"       CAT_PROTOCOL
print_urls "Clients"        CAT_CLIENTS
print_urls "Use Cases"      CAT_USECASES
print_urls "Packages"       CAT_PACKAGES
print_urls "Plans"          CAT_PLANS
print_urls "Specs"          CAT_SPECS
print_urls "Other"          CAT_OTHER

if [[ "$PLAIN" == "false" ]]; then
  echo ""
  echo "=== Plain URLs (copy-paste block) ==="
  echo ""
  for f in "${FILTERED[@]}"; do
    echo "${BASE_URL}/${f}"
  done
fi
