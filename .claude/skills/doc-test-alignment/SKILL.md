---
name: doc-test-alignment
description: >
  Verify that committed docs (README.md, CLAUDE.md, SKILL.md descriptions) still
  describe what the code and tests actually do. Use at the end of a plan, before
  PR creation, or when the user says "check doc-test alignment", "verify docs",
  or "do the docs still match the code". STUB — implementation TBD; today this
  skill is a placeholder describing the intended workflow.
---

# doc-test-alignment (stub)

This skill is a stub. The real workflow is intentionally not yet implemented —
the file exists so that `steward verify` can find it and so contributors who
land here know it is on the roadmap, not forgotten.

## Intended workflow (when implemented)

1. **README.md command examples** — extract every fenced shell block in
   `README.md`, run each against the current checkout, fail if any
   exits non-zero or produces output that contradicts the surrounding prose.
2. **CLAUDE.md "build/test/publish" lines** — same treatment for the commands
   listed under that section.
3. **SKILL.md descriptions vs scripts** — for each `.claude/skills/<name>/`,
   diff the SKILL.md `description` field against `scripts/*` filenames and
   help text. Surface disagreements (e.g. SKILL.md says "runs lint and bumps"
   but `scripts/` has no lint script).
4. **Test-name vs assertion drift** — flag tests whose name mentions a
   feature the assertions no longer touch (e.g.
   `test_show_command_runs_skill_script` should still actually run a skill
   script).

## Why this is a stub

Each of the four checks above is independently non-trivial. Shipping a partial
implementation would either silently pass when it shouldn't, or false-positive
on intentional doc-vs-code differences. The right path is to land them one at
a time, with tests, behind a `steward verify --check doc-test-alignment` flag.
That work is tracked in `docs/sibling-pattern.md` (the "Roadmap" section in
`CLAUDE.md` names the parent verbs).

## What this stub guarantees today

- The skill directory exists, so `steward verify`'s skills-convention check
  finds the standard layout (SKILL.md + `scripts/`).
- `scripts/.gitkeep` keeps the empty `scripts/` directory in git.
- This `SKILL.md` is the contract for what the skill will do — when the
  implementation lands, it must satisfy this description or the description
  must move first.
