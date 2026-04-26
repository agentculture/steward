---
name: agent-config
description: >
  Show a Culture agent's full configuration in one view: CLAUDE.md, the parallel
  culture.yaml, and the agent's local skills. Use when reviewing an agent for
  alignment, before changing a system_prompt, when triaging a PR that touches
  agent definitions, or when the user says "show agent <name>" / "what does
  <agent> look like" / "audit agent config". Steward-specific.
---

# Agent Config — surface a Culture agent in one view

Steward's job is keeping resident agents aligned across Culture projects. To
reason about alignment you need to see, in one place, the three artifacts that
together define an agent:

1. **`CLAUDE.md`** — prompt-side guidance (what Claude Code sessions in that
   repo are told).
2. **`culture.yaml`** — runtime-side config (`agents:` list with `suffix`,
   `backend`, `model`, `system_prompt`, `channels`, `tags`, `acp_command`,
   `extras`). Lives parallel to `CLAUDE.md` at the project root.
3. **`.claude/skills/*/SKILL.md`** — per-project skills the agent can invoke.

If any of these drifts away from the others (prompt says one thing,
`system_prompt` says another, skills assume a third), the agent is misaligned.
That's what Steward is supposed to catch.

## When to use

- Before editing a `system_prompt` in any sibling project's `culture.yaml`.
- When a PR diff touches `CLAUDE.md` or `culture.yaml` in any sibling project.
- During a Steward alignment audit (cross-project consistency check).
- Before answering a question about what an agent does — read it, don't guess.

## How to run

One script, two ways to call it:

```bash
# Path mode — point at any directory containing CLAUDE.md + culture.yaml
.claude/skills/agent-config/scripts/show.sh ../culture

# Suffix mode — resolves a registered agent suffix via the Culture server's
# manifest (location set by culture_server_yaml in skills.local.yaml)
.claude/skills/agent-config/scripts/show.sh daria
```

Output is three sections: CLAUDE.md, culture.yaml, and a one-line summary
per local skill (name + description, truncated to 120 chars).

## What to look at in `culture.yaml`

| Field | Why it matters |
|-------|----------------|
| `suffix` | Identifies the agent on the mesh. |
| `backend` | One of `claude` / `codex` / `copilot` / `acp`. The all-backends rule means a feature in one must land in all four. |
| `model` | Drift here changes behavior silently. |
| `system_prompt` | Must not contradict `CLAUDE.md`. |
| `channels` | Where the agent listens. Must match what `CLAUDE.md` claims it does. |
| `tags`, `extras`, `acp_command` | Backend-specific; check against the canonical example in `culture/packages/agent-harness/culture.yaml`. |

## Alignment checks

After `show.sh`, ask three questions about the agent:

1. **Does `system_prompt` (in `culture.yaml`) contradict `CLAUDE.md`?** If
   `CLAUDE.md` says "this agent runs the deploy" but `system_prompt` says "you
   are a casual chat assistant," that's drift.
2. **Are the `channels` listed in `culture.yaml` the channels `CLAUDE.md`
   claims the agent participates in?** Mismatch = silent absence on the mesh.
3. **Is the `backend` consistent with the all-backends rule?** If the agent is
   `claude` only and a sibling agent doing the same job is `codex` only,
   feature drift between the two is inevitable.

Report findings as a short bulleted list — not a pass/fail. Drift is for
humans to decide on; this skill is read-only.

## Inventory of skills already present in the workspace

Captured during Steward's first audit (2026-04). Use this to recognize what
already exists before scaffolding something new — duplication is a Steward
anti-goal. Append discoveries here so the next session inherits them.

**PR / code review** — `pr-review` (multiple copies across culture,
culture-sonar-cli, daria, codex-guide, plus the user-level canonical version);
`review-and-fix`; `superpowers:receiving-code-review`,
`superpowers:requesting-code-review`.

**Agent lifecycle / mesh ops** — `culture` (multiple copies); `culture-irc` /
`irc` (multiple copies); `daria`.

**Build / verify** — `run-tests` (culture, culture-sonar-cli).

**Introspection** — `claude-code-guide:introspect`,
`codex-guide:codex-guide-introspect`.

**Onboarding / docs** — `ask`, `onboard`, `codex-guide-ask`,
`codex-guide-onboarding`.

**Gamification** — `game-mode`, `level-up`, `visualize-setup`,
`migrate-to-claude`.

## Notes

- `show.sh` is read-only. It never edits agent files. Drift is reported, not
  auto-fixed.
- The canonical `culture.yaml` parser lives at
  `culture/culture/config.py:load_culture_yaml(directory, suffix)` returning
  `AgentConfig`. If parsing gets non-trivial in this skill, shell out to a
  `culture` CLI command instead of re-parsing.
- The script handles both `directory` keys and bare-string values in the
  server manifest's `agents:` mapping.
