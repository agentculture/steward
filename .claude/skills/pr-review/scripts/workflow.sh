#!/usr/bin/env bash
# Steward pr-review workflow entry point.
#
# Subcommands:
#   lint              run the portability lint on the staged diff
#   poll <PR>         fetch and display review comments
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

read_list() {
    python3 -c "
import yaml, sys
d = yaml.safe_load(open(sys.argv[1])) or {}
for v in (d.get(sys.argv[2]) or []):
    print(v)
" "$CFG" "$1"
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
        sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# *//'
        ;;
    *)
        echo "unknown subcommand: $cmd" >&2
        echo "run '$(basename "$0") help' for usage." >&2
        exit 2
        ;;
esac
