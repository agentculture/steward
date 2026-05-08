---
name: cicd
description: >
  Steward's CI/CD lane: open PR (auto-wait for Qodo/Copilot), push fixes
  (re-poll bots), triage feedback, reply, resolve. Adds a portability lint
  (no absolute /home paths, no per-user dotfile refs in committed docs),
  an alignment-delta check when CLAUDE.md or culture.yaml change, and
  greenfield-aware test/version-bump steps. Use when: creating PRs in
  steward, handling review feedback, polling CI status, or the user says
  "create PR", "review comments", "address feedback", "resolve threads".
  Renamed from `pr-review` in steward 0.7.0.
---

# CI/CD — Steward edition

Steward's PRs touch agent prompts, `culture.yaml` configs, and cross-project
guidance. The generic `pr-review` skills don't know that, so they miss two
classes of bugs Steward keeps producing:

- **Path leaks** — committing absolute home-directory paths that work only on
  the author's machine. (PR #1 had four of these.)
- **Per-user config dependencies** — referencing a dotfile under the user's
  home directory in repo guidance, breaking reproducibility for other
  contributors and CI.

This skill specializes Culture's `pr-review` flow to catch both up front, plus
an alignment-delta step when Steward-affecting files change. The workflow is
encapsulated in `scripts/workflow.sh` — follow that, not a manual checklist.

## Prerequisites

Hard requirements: `gh` (GitHub CLI), `jq`, `bash`, `python3` (stdlib only),
`curl` (used by `pr-status.sh`).

Soft requirement: `PyYAML` is needed **only for suffix mode** of the sibling
`agent-config` skill, where it parses Culture's server manifest. Path mode
and every `cicd` script work without it. If suffix mode runs without
PyYAML it exits with a clear install hint.

Per-machine paths (sibling-project layout) live in
`.claude/skills.local.yaml`; see the committed `.example` for the schema.

## How to run

`scripts/workflow.sh` is the entry point. Subcommands:

| Command | Purpose |
|---------|---------|
| `workflow.sh lint` | Portability lint on the current diff (staged + unstaged). |
| `workflow.sh open-pr --title T [--body-file F] [--wait SECS] [...]` | `gh pr create` then sleep 180s (or `--wait SECS`) and fetch reviewer comments in one shot. Use after pushing the initial branch. |
| `workflow.sh poll <PR>` | Fetch and display all review comments. |
| `workflow.sh poll-readiness <PR> [--max-iters N] [--interval SECS]` | Loop until qodo + Copilot are both ready (or the PR closes / iteration cap hits). Headline on stdout, per-iteration diagnostics on stderr. Direct wrapper around `scripts/poll-readiness.sh`. |
| `workflow.sh wait-after-push <PR> [--wait SECS]` | Sleep 180s (or `--wait SECS`) then re-fetch comments. Use after pushing fixes. |
| `workflow.sh await <PR>` | Poll for reviewer readiness (default 30 × 60s ≈ 30 min cap; tune with `STEWARD_PR_AWAIT_ITERS` and `STEWARD_PR_AWAIT_INTERVAL`), then run `pr-status.sh` (CI checks + SonarCloud quality gate, OPEN issues, hotspots) and `pr-comments.sh` (inline / issue / top-level / SonarCloud-new-issues sections). Exits non-zero on SonarCloud `ERROR` or unresolved threads. Setting the legacy `STEWARD_PR_AWAIT_SECONDS=<n>` falls back to a fixed sleep with a deprecation warning. |
| `workflow.sh delta` | Dump each sibling project's `CLAUDE.md` head + `culture.yaml`. |
| `workflow.sh reply <PR>` | Batch reply (JSONL on stdin) and resolve threads. |
| `workflow.sh help` | Print this list. |

The vendored single-comment helpers — `pr-reply.sh`, `pr-status.sh` — live
next to `workflow.sh` and are usable directly when batching isn't appropriate.

## Polling for reviewer readiness

Two modes, same looper (`scripts/poll-readiness.sh`). Both watch for:

- **qodo ready** — an issue comment whose body contains `Code Review by Qodo`
  AND does NOT contain qodo's "still analysing" placeholder
  (`Looking for bugs?`).
- **Copilot ready** — at least one top-level review with a non-empty body.

The looper exits 0 the moment both signals fire (or the PR is `MERGED` /
`CLOSED`), 1 on TIMEOUT, 2 on bad usage. Per-iteration heartbeats go to
stderr so the headline on stdout can be cleanly captured.

### Synchronous (the simple case)

Use `workflow.sh await <PR>` after `gh pr create`. The `await` subcommand
runs the looper, then dumps `pr-status.sh` + `pr-comments.sh`. Default cap
is 30 iterations × 60s; tune with `STEWARD_PR_AWAIT_ITERS` and
`STEWARD_PR_AWAIT_INTERVAL`. The main session burns context during the
wait — fine for a few minutes, wasteful past ~5.

### Asynchronous (preferred for long waits)

Hand the wait to a **background subagent** so the main session pays the
cache cost only once, when readiness fires. Invoke the `Agent` tool with:

- `subagent_type: general-purpose`
- `run_in_background: true`
- `description: "Poll PR <N> for reviewer readiness"`
- `prompt`: the template below, with `<PR>` and `<OWNER/REPO>` substituted.

```text
You are a background poller for GitHub PR <PR> at <OWNER/REPO>. Run:

    bash .claude/skills/cicd/scripts/poll-readiness.sh \
        --repo <OWNER/REPO> --max-iters 30 --interval 60 <PR>

The script returns 0 when qodo and Copilot are both ready (or the PR is
MERGED/CLOSED), 1 on TIMEOUT. Capture its stdout (the headline) and emit
it as your final report verbatim, then stop. Do not triage, do not run
pr-status.sh, do not call any other commands — readiness reporting only.
The parent agent will refetch and triage when your notification arrives.
```

When the subagent returns, run `bash .claude/skills/cicd/scripts/workflow.sh await <PR>` (or just `pr-status.sh` + `pr-comments.sh`) to triage. The user can interrupt the subagent at any time with TaskStop.

This pattern is borrowed from sibling repo
[`agentculture/cfafi`](https://github.com/agentculture/cfafi)'s `poll`
skill — Steward vendors only the looper here rather than promoting `poll`
to its own first-class skill until other Steward verbs need the same
primitive.

## End-to-end flow

```text
git checkout -b <type>/<desc>
# ... edit ...
.claude/skills/cicd/scripts/workflow.sh lint
git commit -am "..." && git push -u origin <branch>
gh pr create --title "..." --body "..."   # title <70 chars, body signed "- <nick> (Claude)"
.claude/skills/cicd/scripts/workflow.sh await <PR>   # readiness loop, then CI + SonarCloud + all comments
# triage; if CLAUDE.md/culture.yaml/.claude/skills changed:
.claude/skills/cicd/scripts/workflow.sh delta
# fix, re-lint, push
.claude/skills/cicd/scripts/workflow.sh reply <PR> < replies.jsonl
gh pr checks <PR>
# Wait for human merge — never merge yourself.
```

Branch naming: `fix/<desc>`, `feat/<desc>`, `docs/<desc>`, `skill/<name>`.
PR / comment signature: `- <nick> (Claude)`, where `<nick>` comes from
the agent's own `culture.yaml` — first agent's `suffix` — falling back
to the git-repo basename when no `culture.yaml` is present. The reply
script resolves this via `scripts/_resolve-nick.sh` and auto-appends the
signature only when the body isn't already signed, so JSONL reply
entries can include or omit it. Hand-rolled `gh pr create` and
`gh issue comment` calls should follow the same convention.

## Triage rules

For every comment, decide **FIX** or **PUSHBACK** with reasoning.

Default to **FIX** for: portability complaints (always valid for Steward —
recurring bug class), test or doc requests, style nits aligned with workspace
conventions.

Default to **PUSHBACK** for: architecture opinions that conflict with workspace
`CLAUDE.md` or the all-backends rule; greenfield false-positives (e.g. "add
tests" before there's any source — defer to a later PR, don't refuse).

### Alignment-delta rule

If the PR touches `CLAUDE.md`, `culture.yaml`, or anything under
`.claude/skills/`, run `workflow.sh delta` **before** declaring FIX or
PUSHBACK on each comment. The script dumps the head of every sibling
project's `CLAUDE.md` plus the full `culture.yaml`, using `sibling_projects`
from `skills.local.yaml`. Note any sibling that needs a follow-up PR and
mention it in your reply.

## Greenfield-aware steps

The lint and the workflow script are always-on. Stack-specific steps are
conditional and currently no-op (greenfield repo):

```bash
[ -d tests ] && [ -f pyproject.toml ] && uv run pytest tests/ -x -q
[ -f pyproject.toml ] && bump_version_per_project_convention   # see project README
[ -f .markdownlint-cli2.yaml ] && markdownlint-cli2 "$(git diff --name-only --cached '*.md')"
```

Revisit each line as the corresponding stack element actually lands.

## Reply etiquette

Every comment must get a reply — no silent fixes. Always pass `--resolve`
when batch-replying so threads close automatically. Reference the
review-comment IDs in the fix-up commit message.

SonarCloud is queried in two places: `pr-status.sh` (quality gate, OPEN
issues, hotspots) and the Section-4 dump in `pr-comments.sh` (new-issue
list). Both derive the project key as `<owner>_<repo>`; override with
`SONAR_PROJECT_KEY=<key>` for non-standard naming, and they silently skip
when the project isn't on SonarCloud. Steward isn't yet a registered mesh
agent, so the post-merge IRC ping that Culture's `pr-review` includes is
still skipped — that returns when Steward joins the mesh.
