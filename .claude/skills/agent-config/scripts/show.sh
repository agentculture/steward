#!/usr/bin/env bash
# Show a Culture agent's full configuration in one view:
# CLAUDE.md, the parallel culture.yaml, and the .claude/skills/ index.
#
# Usage: show.sh <path-or-agent-suffix>
#
# Path mode:   show.sh ../culture
# Suffix mode: show.sh daria   (resolved via culture_server_yaml in skills.local.yaml)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"

CFG="$REPO_ROOT/.claude/skills.local.yaml"
[ -f "$CFG" ] || CFG="$REPO_ROOT/.claude/skills.local.yaml.example"

read_cfg() {
    python3 -c "
import yaml, sys
d = yaml.safe_load(open(sys.argv[1])) or {}
v = d.get(sys.argv[2], '')
print(v if v is not None else '')
" "$CFG" "$1"
}

target="${1:-}"
if [ -z "$target" ]; then
    echo "Usage: $(basename "$0") <path-or-agent-suffix>" >&2
    exit 2
fi

if [ -d "$target" ]; then
    DIR="$target"
else
    SERVER_YAML_RAW="$(read_cfg culture_server_yaml)"
    SERVER_YAML="${SERVER_YAML_RAW/#\~/$HOME}"
    if [ ! -f "$SERVER_YAML" ]; then
        echo "no server manifest at $SERVER_YAML — set culture_server_yaml in $CFG" >&2
        echo "or pass an explicit path instead of suffix '$target'" >&2
        exit 1
    fi
    DIR=$(python3 - "$SERVER_YAML" "$target" <<'PY'
import sys, yaml, pathlib
manifest_path, suffix = sys.argv[1], sys.argv[2]
m = yaml.safe_load(pathlib.Path(manifest_path).read_text()) or {}
agents = m.get('agents', {})
entry = agents.get(suffix)
if entry is None:
    sys.exit(f"no agent registered with suffix {suffix!r} in {manifest_path}")
print(entry['directory'] if isinstance(entry, dict) else entry)
PY
)
fi

DIR="${DIR/#\~/$HOME}"

echo "=== $DIR/CLAUDE.md ==="
if [ -f "$DIR/CLAUDE.md" ]; then cat "$DIR/CLAUDE.md"; else echo "(missing)"; fi
echo
echo "=== $DIR/culture.yaml ==="
if [ -f "$DIR/culture.yaml" ]; then cat "$DIR/culture.yaml"; else echo "(missing)"; fi
echo
echo "=== $DIR/.claude/skills/ ==="
found=0
for s in "$DIR"/.claude/skills/*/SKILL.md; do
    [ -f "$s" ] || continue
    found=1
    name=$(awk '/^name:/{print $2; exit}' "$s")
    desc=$(awk '
        /^description:/ {
            sub(/^description:[[:space:]]*/, "")
            buf = $0
            flag = 1
            next
        }
        flag && /^[a-z_-]+:/ { flag = 0 }
        flag { buf = buf " " $0 }
        END { gsub(/^[[:space:]]+|[[:space:]]+$/, "", buf); print buf }
    ' "$s")
    printf "  %-30s %s\n" "$name" "${desc:0:120}"
done
[ "$found" -eq 0 ] && echo "  (no skills)"
