# Skill upstream sources

Each skill has exactly one canonical source repo. `steward doctor` consults
this file when vendoring a skill into a target sibling so the choice is
deterministic.

When a skill exists in multiple repos, the **upstream** column wins. Other
repos are downstream copies that may lag and should periodically re-sync from
upstream.

| Skill | Upstream | Downstream copies (known) | Notes |
|-------|----------|---------------------------|-------|
| `version-bump` | `steward` (`.claude/skills/version-bump/`) | `cfafi`, `afi-cli` | Pure Python, prepends Keep-a-Changelog entry; no per-repo customization needed. |
| `pr-review` | `steward` (`.claude/skills/pr-review/`) | `cfafi` (variant) | Steward owns the canonical workflow; downstream copies may add reviewer-specific wiring (Qodo/Copilot, etc.). |
| `agent-config` | `steward` (`.claude/skills/agent-config/`) | — | Steward-specific (resolves Culture agent suffixes); not portable as-is. |
| `doc-test-alignment` | `steward` (`.claude/skills/doc-test-alignment/`) | — | Stub; real implementation TBD. |
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
  reasons (e.g. `cfafi`'s `pr-review` adds CloudFlare-API reviewers). Record
  the divergence in the downstream `SKILL.md`'s frontmatter `description`.

## When a skill should be promoted upstream

A skill currently owned downstream (e.g. `poll` in `cfafi`) should be promoted
to `steward` when:

1. At least one other sibling has copy-pasted it, OR
2. Its scripts have no repo-specific assumptions (no hard-coded API
   credentials, no per-product paths), AND
3. Its `SKILL.md` describes a pattern (not a single product's workflow).

Promotion is a manual decision — `steward doctor` will not move skills
between repos.
