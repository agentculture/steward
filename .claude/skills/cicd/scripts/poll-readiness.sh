#!/usr/bin/env bash
set -euo pipefail

# poll-readiness.sh — wait until both automated PR reviewers (qodo + Copilot)
# have posted their full reviews, OR the PR is merged/closed, OR an iteration
# cap is hit.
#
# Designed to be invoked two ways:
#   (a) Synchronously by `workflow.sh await` (stdin/stdout local to the
#       caller — main session burns context during the wait).
#   (b) Asynchronously by a background subagent (Agent tool with
#       run_in_background:true). The subagent owns the wait so the main
#       session pays the cache cost only once, at completion.
#
# Usage:
#   poll-readiness.sh [--repo OWNER/REPO] [--max-iters N] [--interval SECS] PR_NUMBER
#
# Defaults: --max-iters 30, --interval 60   (≈30-minute hard cap)
#
# Exit codes:
#   0  Both qodo and Copilot ready, OR PR state is MERGED / CLOSED.
#   1  TIMEOUT after --max-iters with at least one reviewer still pending.
#   2  Bad usage.
#
# Output:
#   stdout — final headline (≤10 lines), suitable for capture.
#   stderr — per-iteration diagnostics ("still waiting (qodo: …, copilot: …)").
#
# Detection heuristics (mirror cfafi's `poll` skill):
#   qodo ready    = ISSUE COMMENTS section contains "Code Review by Qodo"
#                   AND does NOT contain "Looking for bugs?" (qodo's
#                   "still analysing" placeholder).
#   Copilot ready = TOP-LEVEL REVIEWS header reports a count > 0.
#
# Dependencies: gh, jq, bash, curl  (same as the rest of the skill).

usage() {
    cat >&2 <<'EOF'
Usage: poll-readiness.sh [--repo OWNER/REPO] [--max-iters N] [--interval SECS] PR_NUMBER

Defaults: --max-iters 30, --interval 60.
Exit 0 when both qodo and Copilot have posted (or PR closed),
exit 1 on TIMEOUT, exit 2 on bad usage.
EOF
    exit 2
}

require_value() {
    if [[ $# -lt 2 ]]; then
        echo "Missing value for $1" >&2
        usage
    fi
}

REPO=""
MAX_ITERS=30
INTERVAL=60
PR_NUMBER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)       require_value "$@"; REPO="$2"; shift 2 ;;
        --max-iters)  require_value "$@"; MAX_ITERS="$2"; shift 2 ;;
        --interval)   require_value "$@"; INTERVAL="$2"; shift 2 ;;
        -h|--help)    usage ;;
        --) shift; break ;;
        -*) echo "Unknown flag: $1" >&2; usage ;;
        *)  PR_NUMBER="$1"; shift ;;
    esac
done

[[ -z "$PR_NUMBER" ]] && usage
[[ "$PR_NUMBER" =~ ^[0-9]+$ ]] || { echo "PR_NUMBER must be a positive integer" >&2; exit 2; }
[[ "$MAX_ITERS" =~ ^[0-9]+$ ]] || { echo "--max-iters must be a positive integer" >&2; exit 2; }
[[ "$INTERVAL"  =~ ^[0-9]+$ ]] || { echo "--interval must be a positive integer"  >&2; exit 2; }

if [[ -z "$REPO" ]]; then
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PR_URL="https://github.com/${REPO}/pull/${PR_NUMBER}"

emit_headline() {
    # $1 final state, $2 qodo status, $3 copilot status, $4 iter count, $5 next-step hint
    cat <<EOF
PR URL:        ${PR_URL}
Final state:   $1
qodo:          $2
Copilot:       $3
Iterations:    $4 / ${MAX_ITERS}
Next step:     $5
EOF
}

iter=0
qodo_status="not-posted"
copilot_status="not-posted"

while (( iter < MAX_ITERS )); do
    iter=$((iter + 1))

    # 1. Short-circuit on closed/merged.
    pr_state=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state -q .state 2>/dev/null || echo "UNKNOWN")
    if [[ "$pr_state" == "MERGED" || "$pr_state" == "CLOSED" ]]; then
        emit_headline "$pr_state" "$qodo_status" "$copilot_status" "$iter" \
            "PR was ${pr_state,,} before reviewers finished — no triage needed."
        exit 0
    fi

    # 2. Fetch comments via the vendored sibling fetcher.
    if ! comments=$(bash "$SCRIPT_DIR/pr-comments.sh" --repo "$REPO" "$PR_NUMBER" 2>/dev/null); then
        echo "iter ${iter}: pr-comments.sh failed; will retry" >&2
        sleep "$INTERVAL"
        continue
    fi

    # 3. qodo readiness — body contains "Code Review by Qodo" AND not the placeholder.
    if grep -qF "Code Review by Qodo" <<<"$comments"; then
        if grep -qF "Looking for bugs?" <<<"$comments"; then
            qodo_status="placeholder-only"
        else
            qodo_status="ready"
        fi
    else
        qodo_status="not-posted"
    fi

    # 4. Copilot readiness — TOP-LEVEL REVIEWS header count > 0.
    copilot_count=$(grep -oE 'TOP-LEVEL REVIEWS \([0-9]+\)' <<<"$comments" | grep -oE '[0-9]+' | head -1 || true)
    copilot_count=${copilot_count:-0}
    if (( copilot_count > 0 )); then
        copilot_status="ready"
    else
        copilot_status="not-posted"
    fi

    # 5. Done?
    if [[ "$qodo_status" == "ready" && "$copilot_status" == "ready" ]]; then
        emit_headline "OPEN" "ready" "ready" "$iter" \
            "Run \`workflow.sh await ${PR_NUMBER}\` (or pr-comments.sh) and triage."
        exit 0
    fi

    echo "iter ${iter}/${MAX_ITERS}: qodo=${qodo_status}, copilot=${copilot_status}; sleeping ${INTERVAL}s" >&2
    if (( iter < MAX_ITERS )); then
        sleep "$INTERVAL"
    fi
done

# Fell off the loop — TIMEOUT.
emit_headline "TIMEOUT" "$qodo_status" "$copilot_status" "$MAX_ITERS" \
    "Hit ${MAX_ITERS}-iteration cap; re-run poll-readiness.sh or check PR manually."
exit 1
