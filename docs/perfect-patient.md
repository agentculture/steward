# Perfect patient

> Hand-curated. This is the canonical baseline every healthy AgentCulture
> sibling is expected to match. Doctor regenerates a *prescription* form
> into `.prescriptions/<slug>/perfect-patient.md` on every `--scope siblings`
> run; diff this file against that prescription to see what the corpus
> currently says vs. what the canonical bar is.
>
> Synthesized snapshot at the time this file was last hand-curated
> (2026-04-26): 8 agents across 6 repos.

## Required `culture.yaml` fields

Present in ≥80% of agents.

- `backend`
- `suffix`

## Recommended `culture.yaml` fields

Present in 30–80% of agents.

- `acp_command`
- `model`

## Common skills baseline

Skills present in ≥80% of agent repos.

None yet.

## Recommended skills

Every healthy AgentCulture sibling is expected to vendor these — derived
from the steward-owned upstream copies in `docs/skill-sources.md`.

- `pr-review` — Branch, commit, push, create PR, wait for automated
  reviewers, fetch comments, triage / fix / pushback, reply, resolve
  threads. Steward owns the canonical workflow.
- `run-tests` — Run pytest with parallel execution and coverage.
  Coverage source is read from `pyproject.toml`'s
  `[tool.coverage.run]`, so the same script works in any sibling.
- `version-bump` — Bump semver in `pyproject.toml` and prepend a
  Keep-a-Changelog entry. Required on every PR per the
  `version-check` CI job.
- `gh-issues` — Fetch GitHub issues with full body and comments via
  `gh issue view`. Auto-detects the repo; `--repo` overrides.
- `notebooklm` — Generate GitHub blob URLs for repo docs, ready to
  paste into NotebookLM (or any external doc-ingestion tool).
- `sonarclaude` — Query SonarCloud for quality gate, issues, metrics,
  hotspots; supports the `accept` flow with mandatory rationale
  comment for pushback. Project key resolves from `$SONAR_PROJECT`
  or `--project KEY`.
- `pypi-maintainer` — Switch a PyPI package install between
  production PyPI, TestPyPI dev builds, and a local editable
  checkout. Required for any sibling that publishes a package and
  needs to verify TestPyPI builds before promotion.

## Optional skills

Useful affordances that are not load-bearing — a sibling without them
is still considered healthy.

- `discord-notify` — Send a Discord webhook embed (info / status /
  completion / error). Requires `DISCORD_WEBHOOK_URL` in env. Useful
  for agents that run long tasks the user wants to be paged about.

## Conditional skills

Each is required only when the sibling matches a condition; report it
as a gap only against repos that match.

- `jekyll-test` — Build a Jekyll site and validate output (custom
  color scheme applied, permalinks resolved, just-the-docs navigation
  consistent). **Condition:** the repo contains a `_config.yml`
  (i.e. ships a Jekyll / GitHub Pages / Cloudflare Pages site).

## Common `CLAUDE.md` sections

Top-level `## …` headings present in ≥80% of agent repos.

None yet.
