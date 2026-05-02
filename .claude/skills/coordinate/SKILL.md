---
name: coordinate
description: >
  Cross-repo coordination from steward: file issues and hand off briefs to
  sibling-repo agents. Use when the next step lives in another repo and an
  agent there needs to act on it. Auto-signs every post with
  `- steward (Claude)`. Not for in-steward issues — use `gh issue create`
  or the `cicd` skill directly for those.
---

# Coordinate (Cross-Repo)

Steward's job is alignment across the AgentCulture mesh; that regularly
means surfacing a gap in another repo (a missing portable script, a
divergent skill, a dependency on a moving piece) and asking the agent on
the other side to act on it. Without dedicated infrastructure each
hand-off becomes an ad-hoc `gh issue create` with hand-edited body and
manually-typed signature. This skill enforces the conventions and
version-controls the script.

## When to Use

- A gap surfaces in **another repo's surface** (a missing public API, a
  wire-format compat fix, a divergent skill, a documentation ask) and you
  need an agent on the other side to act.
- You're handing off a self-contained brief to a sibling-repo agent.
- You're asking the sibling repo a question that benefits from a tracked
  issue rather than ephemeral chat.

## When NOT to Use

- **In-steward issues** — open them with `gh issue create` directly, or
  work them through the `cicd` skill.
- **PR review comments** — that's the `cicd` skill (which already
  auto-signs replies).
- **Routine commits** — those don't get a cross-repo signature.

## Conventions

### 1. Hand-off briefs are self-contained

The receiving agent must not need steward-side context to act. Inline
the relevant content; do not say "see steward's plan."

A brief that says "see steward#NN" is a bug. The receiving agent will
look at it, get lost in steward-specific context that's irrelevant to
them, and either ask for clarification (slow round-trip) or guess wrong
(worse). Inline the ask, the rationale, and concrete acceptance
criteria. Quote source-of-truth files (path + line numbers + small
excerpts) when their shape matters to the ask.

### 2. Sign as `- steward (Claude)`

Identifies both the source repo AND that the post is from steward's AI
agent. `post-issue.sh` auto-appends this signature; do not type it
manually in the body and do not pass a way to disable it.

This is intentionally distinct from the global `- Claude` convention
(which doesn't identify the originating repo). Cross-repo readers can
tell at a glance whether a brief came from steward, culture, or another
sibling. Each vendor of this skill hard-codes its own signature literal —
`coordinate` deliberately does not depend on the `cicd` skill's
`_resolve-nick.sh`, so it stays self-contained per the
skills-portability rule.

### 3. Title format

`<verb> <thing> (unblocks <consumer>)` — e.g.,
`Vendor portability-lint into <repo> (unblocks steward 0.7 doctor --apply)`.
The parenthetical tells the receiving repo's maintainers what's waiting
on them. Drop the parenthetical only when the ask isn't blocking
anything.

## How to Invoke

### File a new issue

```bash
bash .claude/skills/coordinate/scripts/post-issue.sh \
    --repo agentculture/<sibling> \
    --title "Vendor portability-lint into <sibling> (unblocks steward 0.7)" \
    --body-file /tmp/brief.md
```

Or pass the body on stdin:

```bash
bash .claude/skills/coordinate/scripts/post-issue.sh \
    --repo agentculture/<sibling> \
    --title "..." <<'EOF'
<brief body here, multi-paragraph, with all the inline context the receiving agent needs>
EOF
```

The script prints the issue URL on success — capture it for
cross-references in your spec / plan / PR description. The signature
`- steward (Claude)` is auto-appended at the end of the body.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/post-issue.sh` | Create a new issue on a target repo. Auto-signs `- steward (Claude)`. |

More scripts can land here as the cross-repo coordination footprint
grows — `post-comment.sh` for follow-ups, `check-issue-status.sh` for
tracking, etc. Add them when there's a second concrete need; do not
pre-build for hypotheticals.

## Red Flags

**Never:**

- Post a brief that says "see steward's plan" without inlining the
  content. Briefs must be self-contained.
- Skip the signature. The script enforces it; do not introduce a
  `--no-signature` flag.
- Use this skill for in-steward issues — use `gh issue create` or the
  `cicd` skill instead.
- Manually type `- steward (Claude)` at the end of the body — the
  script appends it. Manual typing creates double-signatures when the
  script is later refactored.
- Post the same ask twice. If the receiving repo already has an open
  issue tracking the gap, comment on that issue (use `gh issue comment`
  for now; promote to a `post-comment.sh` script when it becomes a
  recurring pattern).
