---
name: pr-review
description: >
  Steward-specific PR workflow: branch, commit, push, PR, wait for Qodo/Copilot,
  triage, fix, reply, resolve. Adds a portability lint (no absolute /home paths,
  no per-user dotfile refs in committed docs), an alignment-delta check when
  CLAUDE.md or culture.yaml change, and greenfield-aware test/version-bump
  steps. Use when: creating PRs in steward, handling review feedback, or the
  user says "create PR", "review comments", "address feedback", "resolve threads".
---

# PR Review — Steward edition

Steward's PRs touch agent prompts, `culture.yaml` configs, and cross-project
guidance. The generic `pr-review` skills don't know that, so they miss two
classes of bugs Steward keeps producing:

- **Path leaks** — committing `/home/<user>/git/...` paths that work only on
  the author's machine. (PR #1 had four of these.)
- **Per-user config dependencies** — referencing a dotfile under the user's
  home directory in repo guidance, breaking reproducibility for other
  contributors and CI.

This skill specializes Culture's `pr-review` to catch both up front, plus an
alignment-delta step when Steward-affecting files change.

## Prerequisites

All scripts are local — vendored under `.claude/skills/pr-review/scripts/`.
External tool dependencies: `gh` (GitHub CLI) and `jq`. Per-machine paths
(sibling-project layout) live in `.claude/skills.local.yaml`; see the
committed `.example` for the schema.

## Workflow at a glance

```text
git checkout -b <type>/<desc>
# ... edit ...
.claude/skills/pr-review/scripts/workflow.sh lint     # before staging
git add <files> && git commit -m "..."
git push -u origin <branch>
gh pr create --title "..." --body "..."
sleep 300
.claude/skills/pr-review/scripts/workflow.sh poll <PR>
# ... triage; if CLAUDE.md/culture.yaml changed:
.claude/skills/pr-review/scripts/workflow.sh delta
# ... fix, re-lint, push ...
.claude/skills/pr-review/scripts/workflow.sh reply <PR> <<< '{"comment_id":N,"body":"Fixed — ...\n\n- Claude"}'
gh pr checks <PR>
# Wait for human merge — never merge yourself
```

## Step 1 — Branch

If on `main`, branch first.

| Type | Pattern |
|------|---------|
| Bug fix | `fix/<short-desc>` |
| Feature | `feat/<short-desc>` |
| Docs | `docs/<short-desc>` |
| Skill | `skill/<skill-name>` |

Before adding work to an existing branch, check for an open PR:

```bash
gh pr view --json number,title,state --jq '{number,title,state}' 2>/dev/null
```

If a PR is open and your changes are unrelated, stop and ask the user before
piling on.

## Step 2 — Make changes, lint, commit

### 2a — Edit

Make the changes.

### 2b — Portability lint

```bash
.claude/skills/pr-review/scripts/workflow.sh lint
```

Catches:

- Hard-coded `/home/<user>/...` paths in any tracked text file.
- Per-user `~/.<dotfile>` config references in `*.md`, `*.yaml`, `*.toml`,
  `*.json`. Carve-outs: `~/.claude/skills/.../scripts/` (vendored tool calls)
  and `~/.culture/` (Culture mesh data the skills are supposed to read).

If anything is flagged, fix it before staging. Acceptable replacements:

- `../culture` / `../daria` for sibling projects (with the workspace-layout
  assumption documented up top of `CLAUDE.md`).
- `https://github.com/agentculture/culture` for repo URLs.
- A repo-local `.markdownlint-cli2.yaml` or equivalent.
- `$WORKSPACE/...` only if you also document the env var.

### 2c — Greenfield-aware test/version steps

```bash
[ -d tests ] && [ -f pyproject.toml ] && uv run pytest tests/ -x -q
[ -f pyproject.toml ] && bump_version_per_project_convention   # see project README
[ -f .markdownlint-cli2.yaml ] && markdownlint-cli2 "$(git diff --name-only --cached '*.md')"
```

While Steward is greenfield, every conditional is a no-op — that's fine.
Revisit each line as the corresponding stack element lands.

### 2d — Commit

```bash
git add <specific-files>
git commit -m "$(cat <<'EOF'
<imperative subject under 70 chars>

<short body explaining the why>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Step 3 — Push and create PR

```bash
git push -u origin <branch-name>
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
- <bullets>

## Test plan
- [ ] <items>

- Claude
EOF
)"
```

PR title under 70 chars. Sign the body `- Claude` (workspace convention).

## Step 4 — Wait for automated reviewers

Qodo and Copilot need ~5 minutes to post.

```bash
sleep 300
```

## Step 5 — Poll for comments

```bash
.claude/skills/pr-review/scripts/workflow.sh poll <PR>
```

Re-poll every 60s until either a comment shows up or three consecutive empty
polls (reviewer is silent / not configured).

## Step 6 — Triage each comment

For every comment, decide **FIX** or **PUSHBACK**, with reasoning. Default to
FIX for:

- Portability complaints (always valid for Steward — recurring bug class).
- Test or doc requests.
- Style nits aligned with workspace conventions.

Default to PUSHBACK for:

- Architecture opinions that conflict with workspace `CLAUDE.md` or the
  all-backends rule.
- Greenfield false-positives ("add tests" before there's any source — defer,
  don't refuse).

### Steward alignment-delta rule

If the PR touches `CLAUDE.md`, `culture.yaml`, or anything under
`.claude/skills/`, before declaring FIX or PUSHBACK run:

```bash
.claude/skills/pr-review/scripts/workflow.sh delta
```

This dumps the head of each sibling project's `CLAUDE.md` and the full
`culture.yaml`, using the `sibling_projects` list from `skills.local.yaml`.
Note any sibling that needs a follow-up PR and mention it in your reply.

## Step 7 — Fix and push

Make the fixes, **re-run the portability lint**, commit referencing the
review-comment IDs, push.

## Step 8 — Reply and resolve

```bash
.claude/skills/pr-review/scripts/workflow.sh reply <PR> <<'EOF'
{"comment_id": <id>, "body": "Fixed — <short summary>.\n\n- Claude"}
{"comment_id": <id>, "body": "Pushback — <reasoning>.\n\n- Claude"}
EOF
```

Single-comment variant:

```bash
.claude/skills/pr-review/scripts/pr-reply.sh --resolve <PR> <id> \
    "Fixed — <summary>.\n\n- Claude"
```

Always sign with `- Claude`. Always pass `--resolve`. Every comment must get
a reply — no silent fixes.

## Step 9 — Verify clean state

```bash
gh pr checks <PR>
gh pr view <PR> --json state,mergeable
```

Goal: every comment thread has a reply, checks are green or unchanged from
before the fix-up. Steward currently has no SonarCloud integration — skip
the sonarclaude step Culture's skill includes.

## Step 10 — Hand off

**Never merge yourself.** A human merges on the GitHub site.

Steward isn't a registered mesh agent yet, so skip the IRC ping that
Culture's flow ends with. Once Steward joins the mesh, revisit this step.
