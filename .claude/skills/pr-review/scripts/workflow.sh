#!/usr/bin/env bash
# Steward pr-review workflow entry point.
#
# Subcommands:
#   lint              run the portability lint on the current diff (staged + unstaged)
#   poll <PR>         fetch and display review comments
#   await <PR>        sleep 5 min, then check CI + SonarCloud + all comments;
#                     exits non-zero on SonarCloud ERROR or unresolved threads.
#                     Override the wait with STEWARD_PR_AWAIT_SECONDS=<n>.
#   reply <PR>        batch reply to review comments (JSONL on stdin), --resolve
#   delta             dump CLAUDE.md head + culture.yaml for each sibling project
#                     listed in skills.local.yaml (alignment-delta check)
#   help              print this message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"

CFG="$REPO_ROOT/.claude/skills.local.yaml"
[ -f "$CFG" ] || CFG="$REPO_ROOT/.claude/skills.local.yaml.example"

# Read a top-level YAML list from CFG. Schema is intentionally tiny:
#   <key>:
#     - item
#     - item
# Stops at the next top-level key. No PyYAML dependency.
read_list() {
    awk -v key="$1" '
        function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
        {
            line = $0
            sub(/[[:space:]]+#.*$/, "", line)
        }
        in_list && line ~ /^[[:space:]]*-[[:space:]]*/ {
            item = line
            sub(/^[[:space:]]*-[[:space:]]*/, "", item)
            item = trim(item)
            sub(/^["\047]/, "", item); sub(/["\047]$/, "", item)
            if (item != "") print item
            next
        }
        in_list && line ~ /^[^[:space:]#]/ { exit }
        line ~ ("^" key ":[[:space:]]*($|#)") { in_list = 1 }
    ' "$CFG"
}

cmd="${1:-help}"
shift || true

case "$cmd" in
    lint)
        bash "$SCRIPT_DIR/portability-lint.sh"
        ;;
    poll)
        PR="${1:?Usage: workflow.sh poll <PR>}"
        bash "$SCRIPT_DIR/pr-comments.sh" "$PR"
        ;;
    await)
        PR="${1:?Usage: workflow.sh await <PR>}"
        WAIT="${STEWARD_PR_AWAIT_SECONDS:-300}"
        echo "→ waiting ${WAIT}s for Qodo / Copilot / SonarCloud to post …" >&2
        sleep "$WAIT"
        echo "── pr-status ─────────────────────────────────────────────────────────" >&2
        STATUS_OUT=$(bash "$SCRIPT_DIR/pr-status.sh" "$PR" 2>&1) || true
        printf '%s\n' "$STATUS_OUT"
        echo "── pr-comments ───────────────────────────────────────────────────────" >&2
        bash "$SCRIPT_DIR/pr-comments.sh" "$PR" || true
        # Decide pass/fail from the captured pr-status.sh output. Markers:
        #   • "SonarCloud ❌ Quality Gate ERROR" → SonarCloud failed
        #   • "Unresolved: N" with N>0 → unresolved review threads
        SONAR_FAIL=0
        UNRESOLVED=0
        if printf '%s\n' "$STATUS_OUT" | grep -qE 'SonarCloud[[:space:]]+❌[[:space:]]+Quality Gate ERROR'; then
            SONAR_FAIL=1
        fi
        if PENDING=$(printf '%s\n' "$STATUS_OUT" | grep -oE 'Unresolved:[[:space:]]+[0-9]+' | grep -oE '[0-9]+$' | head -1); then
            [ -n "${PENDING:-}" ] && [ "$PENDING" -gt 0 ] && UNRESOLVED=1
        fi
        if [ "$SONAR_FAIL" -eq 1 ] || [ "$UNRESOLVED" -eq 1 ]; then
            echo >&2
            [ "$SONAR_FAIL" -eq 1 ] && echo "✗ SonarCloud quality gate ERROR" >&2
            [ "$UNRESOLVED" -eq 1 ] && echo "✗ ${PENDING} unresolved review thread(s)" >&2
            exit 1
        fi
        echo >&2
        echo "✓ no SonarCloud ERROR, no unresolved threads" >&2
        ;;
    reply)
        PR="${1:?Usage: workflow.sh reply <PR>  (JSONL on stdin)}"
        bash "$SCRIPT_DIR/pr-batch.sh" --resolve "$PR"
        ;;
    delta)
        any=0
        while IFS= read -r sibling; do
            [ -z "$sibling" ] && continue
            any=1
            sibling_abs="$REPO_ROOT/$sibling"
            if [ ! -d "$sibling_abs" ] && [ ! -d "$sibling" ]; then
                echo "=== $sibling ==="
                echo "(not present on disk — skipped)"
                continue
            fi
            target="$sibling_abs"
            [ -d "$target" ] || target="$sibling"
            echo "=== $target ==="
            if [ -f "$target/CLAUDE.md" ]; then
                head -40 "$target/CLAUDE.md"
                echo "..."
            else
                echo "(no CLAUDE.md)"
            fi
            echo "--- culture.yaml ---"
            if [ -f "$target/culture.yaml" ]; then
                cat "$target/culture.yaml"
            else
                echo "(no culture.yaml)"
            fi
            echo
        done < <(read_list sibling_projects)
        [ "$any" -eq 0 ] && echo "(no sibling_projects configured in $CFG)"
        ;;
    help|--help|-h)
        sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# *//'
        ;;
    *)
        echo "unknown subcommand: $cmd" >&2
        echo "run '$(basename "$0") help' for usage." >&2
        exit 2
        ;;
esac
