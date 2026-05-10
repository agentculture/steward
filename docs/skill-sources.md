# Skill supplier — canonical skills

Steward acts as the **skill supplier** for the AgentCulture mesh: it owns the
canonical copy of most cross-sibling skills (`cicd`, `version-bump`,
`run-tests`, `notebooklm`, `sonarclaude`, `pypi-maintainer`,
`agent-config`, `discord-notify`, `jekyll-test`, `doc-test-alignment`,
`communicate`).
Siblings copy those skills into their own `.claude/skills/` and may modify
them. Nothing imports across repos at runtime — this is the **cite,
don't import** pattern: each consumer owns and may diverge from its copy.

This file is the deterministic upstream/downstream map. Each skill has
exactly one canonical source repo (the **upstream** column). Other repos
hold downstream copies that may lag and should periodically re-sync from
upstream. The planned `steward doctor --apply` mode will consult this file
when vendoring a skill into a target sibling so the choice is unambiguous;
today the map is human-readable only — `--apply` is on the roadmap and the
codebase does not yet read this file.

| Skill | Upstream | Downstream copies (known) | Notes |
|-------|----------|---------------------------|-------|
| `agent-config` | `steward` (`.claude/skills/agent-config/`) | — | Steward-specific (resolves Culture agent suffixes); not portable as-is. |
| `discord-notify` | `steward` (`.claude/skills/discord-notify/`) | — | Generic webhook notifier; needs `DISCORD_WEBHOOK_URL` env. Optional in the sibling baseline. |
| `doc-test-alignment` | `steward` (`.claude/skills/doc-test-alignment/`) | — | Stub; real implementation TBD. |
| `jekyll-test` | `steward` (`.claude/skills/jekyll-test/`) | — | Conditional — only meaningful for siblings that ship a Jekyll / Pages / Cloudflare Pages site (detected via `_config.yml`). |
| `notebooklm` | `steward` (`.claude/skills/notebooklm/`) | — | Generates GitHub blob URLs for repo docs; auto-detects branch + remote. |
| `cicd` | `steward` (`.claude/skills/cicd/`) | `cfafi` (still named `pr-review`), `culture` (still named `pr-review`) | Steward owns the canonical workflow; renamed from `pr-review` in steward 0.7.0. Downstream copies may keep the old name on their own cadence and may add reviewer-specific wiring (Qodo/Copilot, etc.). |
| `communicate` | `steward` (`.claude/skills/communicate/`) | `culture` (still named `coordinate`) | Cross-repo + mesh communication: file issues / hand off briefs to sibling-repo agents (auto-signed), comment on existing issues, fetch issues from sibling repos to inline state into briefs, and send live messages to Culture mesh channels (unsigned — nick is the speaker). Renamed from `coordinate` in steward 0.8.0 when mesh-message.sh joined post-issue.sh; absorbed `gh-issues` (as `fetch-issues.sh`) in 0.9.1. As of steward 0.11.0, issue I/O is backed by `agtag` (>=0.1) — signature resolves from the local `culture.yaml` (override via `--as`). Mesh-message remains a `culture channel message` wrapper pending agtag's v0.2 mesh transport. |
| `pypi-maintainer` | `steward` (`.claude/skills/pypi-maintainer/`) | — | Switches a PyPI package install between pypi / test-pypi / local. Generalised from the original culture-specific `change-package`. |
| `run-tests` | `steward` (`.claude/skills/run-tests/`) | — | Coverage source resolves from `[tool.coverage.run]` in `pyproject.toml`, so the script is portable across siblings without modification. |
| `sonarclaude` | `steward` (`.claude/skills/sonarclaude/`) | — | SonarCloud API client. Project key resolves from `$SONAR_PROJECT` or `--project KEY`. |
| `version-bump` | `steward` (`.claude/skills/version-bump/`) | `cfafi`, `afi-cli` | Pure Python, prepends Keep-a-Changelog entry; no per-repo customization needed. |
| `cfafi`, `cfafi-write` | `cfafi` (`.claude/skills/cfafi*/`) | — | CloudFlare-specific; not vendored elsewhere. |
| `poll` | `cfafi` (`.claude/skills/poll/`) | — | Background-reviewer subagent; candidate for promotion to `steward` if it stabilizes. |

## Vendoring policy

- **Cite, don't import.** Skills are copied into the consuming repo, not
  symlinked or installed as a dependency. Each consumer owns and may modify
  their copy.
- **Re-sync explicitly.** When upstream changes, downstream copies do not
  auto-update. `steward doctor --skill <name>` is the intended re-sync path
  (TBD).
- **Diverge intentionally.** A downstream copy may diverge for repo-specific
  reasons (e.g. `cfafi`'s `cicd` / `pr-review` adds CloudFlare-API reviewers).
  Record the divergence in the downstream `SKILL.md`'s frontmatter
  `description`.

## When a skill should be promoted upstream

A skill currently owned downstream (e.g. `poll` in `cfafi`) should be promoted
to `steward` when:

1. At least one other sibling has copy-pasted it, OR
2. Its scripts have no repo-specific assumptions (no hard-coded API
   credentials, no per-product paths), AND
3. Its `SKILL.md` describes a pattern (not a single product's workflow).

Promotion is a manual decision — `steward doctor` will not move skills
between repos.
