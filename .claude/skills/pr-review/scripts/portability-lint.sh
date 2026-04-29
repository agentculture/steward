#!/usr/bin/env bash
# Portability lint: catch path leaks and per-user config dependencies in
# committed docs/configs before they ship in a PR. Steward's recurring bug
# class.
#
# Usage:
#   portability-lint.sh                 # default: diff vs HEAD (staged + unstaged)
#   portability-lint.sh --all           # every tracked file in the repo
#   portability-lint.sh --cached [PATHS...]
#                                       # only the staged set, optionally filtered
#                                       # to a subset of paths (used by pre-commit)
#
# Exits 0 if clean, 1 if any leak is found.

set -euo pipefail

mode="${1:-diff}"
case "$mode" in
    --all)
        files=$(git ls-files -- ':(exclude)*.lock')
        ;;
    --cached)
        # Pre-commit invokes us with the staged set + a list of file paths
        # it picked. Honour that subset.
        if [[ $# -gt 1 ]]; then
            # $@ excluding the first positional is the file list pre-commit gave us.
            shift
            files=$(printf '%s\n' "$@" | grep -vE '\.lock$' || true)
        else
            files=$(git diff --cached --diff-filter=AMR --name-only -- ':(exclude)*.lock')
        fi
        ;;
    diff|--diff)
        files=$(git diff --diff-filter=AMR --name-only HEAD -- ':(exclude)*.lock')
        ;;
    *)
        echo "Usage: $(basename "$0") [--all|--cached [PATHS...]]" >&2
        exit 2
        ;;
esac

if [[ -z "$files" ]]; then
    if [[ "$mode" == "--all" ]]; then
        # `--all` against a repo with no tracked files is a real "nothing to do".
        echo "(no tracked files to check)"
        exit 0
    fi
    if [[ "$mode" == "--cached" ]]; then
        # Pre-commit hooks called with no relevant files: a trivial pass.
        echo "(no staged files to check)"
        exit 0
    fi
    # Default mode found no diff against HEAD. That can mean two things:
    #   1. The contributor genuinely has nothing staged or unstaged — fine.
    #   2. The work is in *untracked* files (typical: a new skill, untouched by
    #      `git diff` until staged). Untracked files are exactly where path
    #      leaks tend to ship from. Don't quietly exit 0 in that case.
    untracked=$(git ls-files --others --exclude-standard)
    if [[ -n "$untracked" ]]; then
        echo "❌ portability-lint: working tree has untracked files but the diff" >&2
        echo "   against HEAD is empty. Stage them (or run with --all) before" >&2
        echo "   relying on this check." >&2
        echo "" >&2
        echo "   Untracked:" >&2
        printf '     %s\n' $untracked >&2
        exit 1
    fi
    echo "(no files to check)"
    exit 0
fi

# ----- Check 1: hard-coded /home/<user>/... paths -----
hits1=$(echo "$files" | xargs -r grep -nE '/home/[a-z][a-z0-9_-]+/' 2>/dev/null || true)

# ----- Check 2: per-user dotfile *config* refs in committed docs/configs -----
# Carve-outs (allowed, NOT flagged):
#   - ~/.claude/skills/<x>/scripts/   vendored tool calls
#   - ~/.culture/                     Culture mesh data this skill is supposed to read
md_yaml=$(echo "$files" | grep -E '\.(md|ya?ml|toml|json|jsonc)$' || true)
if [[ -n "$md_yaml" ]]; then
    # shellcheck disable=SC2088  # ~ is a literal in these grep patterns, not a path
    hits2=$(echo "$md_yaml" | xargs -r grep -nE '~/\.[A-Za-z]' 2>/dev/null \
        | grep -vE '~/\.claude/skills/[^[:space:]"]+/scripts/' \
        | grep -vE '~/\.culture/' \
        || true)
else
    hits2=""
fi

fail=0
if [[ -n "$hits1" ]]; then
    echo "❌ Hard-coded /home/<user>/ paths:"
    printf '    %s\n' "$hits1"
    echo "   Fix: use ../sibling, repo URL, or \$WORKSPACE/sibling instead."
    fail=1
fi
if [[ -n "$hits2" ]]; then
    [[ "$fail" -eq 1 ]] && echo
    echo "❌ Per-user ~/.<dotfile> config refs in committed doc/config:"
    printf '    %s\n' "$hits2"
    echo "   Allowed carve-outs: ~/.claude/skills/.../scripts/ (tool calls), ~/.culture/ (mesh data)."
    echo "   Otherwise: commit a repo-local config or document a portable lookup."
    fail=1
fi

[[ "$fail" -eq 0 ]] && echo "✓ portability lint clean ($(echo "$files" | wc -l | tr -d ' ') files checked)"
exit $fail
