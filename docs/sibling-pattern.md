# AgentCulture sibling pattern

The shape every AgentCulture sibling repo (`steward`, `cfafi`, `ghafi`, `daria`,
…) is expected to wear. This document is the single source of truth that
`steward verify` and `steward doctor` consume.

The companion file `sibling-pattern.json` (TBD; emit from this doc) is the
machine-readable form. Until it lands, the checks `verify` runs are hard-coded
in `steward/cli/_commands/verify.py`; this document remains the human-readable
contract that those hard-coded checks are expected to honor.

## Required artifacts

| # | Artifact | Path | Why |
|---|----------|------|-----|
| 1 | Toolchain | `pyproject.toml` (hatchling, Python ≥3.12, zero runtime deps where possible) | Uniform install/build/publish across the mesh. |
| 2 | Top-level package | `<pkg>/__init__.py`, `<pkg>/__main__.py` | `__version__` via `importlib.metadata`; `python -m <pkg>` works. |
| 3 | CLI scaffolding | `<pkg>/cli/__init__.py`, `cli/_errors.py`, `cli/_output.py`, `cli/_commands/` | The afi-cli pattern: structured errors, stdout/stderr split, `--json`. |
| 4 | Agent-first verbs | `cli/_commands/{learn,explain,whoami}.py` | `learn`/`explain` are the agent-affordance verbs; `whoami` is the smallest auth probe. |
| 5 | Mutation safety | Any write verb defaults to dry-run; `--apply` to commit | Agents call CLIs in loops; safe-by-default is mandatory. |
| 6 | Tests | `tests/test_cli_*.py`, pytest-xdist, coverage | CI gate; no untested verb ships. |
| 7 | CI | `.github/workflows/tests.yml`, `.github/workflows/publish.yml` | Tests + lint + version-check; PyPI/TestPyPI via Trusted Publishing. |
| 8 | Changelog | `CHANGELOG.md` (Keep-a-Changelog) | Bumped on every PR by the `version-bump` skill. |
| 9 | Skills | `.claude/skills/<name>/SKILL.md` + `scripts/` entry-point per skill | Convention: no external path deps, no per-user dotfile refs. |
| 10 | Per-machine config | `.claude/skills.local.yaml.example` (committed) + `.claude/skills.local.yaml` (git-ignored) | Skills read the local file, fall back to the example. |
| 11 | Lint configs | `.flake8`, `.markdownlint-cli2.yaml` (repo-local) | No reliance on per-user home-directory configs. |
| 12 | `CLAUDE.md` | Project shape, build/test/publish commands, conventions | What future Claude instances need that isn't discoverable from a 30-second `ls`. |

## Invariants (machine-checkable)

The full set of invariants the AgentCulture sibling pattern asserts. The
**Status** column reflects what is wired into `steward verify` *today*; items
marked `(planned)` are described here as the contract `verify` is expected to
grow into.

- **portability** *(implemented as `--check portability`)* — no
  `/home/<user>/...` paths in tracked files; no `~/.<dotfile>` config refs in
  committed `.md`/`.yaml`/`.toml`/`.json`/`.jsonc` outside the carve-outs
  (`~/.claude/skills/.../scripts/`, `~/.culture/`).
  *Source:* `.claude/skills/pr-review/scripts/portability-lint.sh`.
- **skills-convention** *(implemented as `--check skills-convention`)* —
  every `.claude/skills/<name>/SKILL.md` has a sibling
  `.claude/skills/<name>/scripts/` directory, **and** the SKILL.md frontmatter
  `name` equals the directory name. (The "every skill has at least one
  entry-point script" invariant is satisfied by the directory existing today
  to keep the check noise-free; tightening to "directory has ≥1 file" is
  *(planned)*.)
- **changelog-format** *(planned)* — `CHANGELOG.md` has at least one
  `## [x.y.z] - YYYY-MM-DD` heading.
- **lint-config-local** *(planned)* — `.markdownlint-cli2.yaml` exists at the
  repo root (no reliance on per-user home configs).

## Repairs (machine-fixable, run by `steward doctor`)

`steward doctor` is **not yet implemented** (see `CLAUDE.md`'s Roadmap
section); the table below is the contract it will honor when it lands. A
repair is included only if it is **deterministic and idempotent**. Where the
right answer depends on judgement, `doctor` will report the gap and stop.

| Invariant violated | Planned repair |
|--------------------|----------------|
| `.claude/skills/<name>/scripts/` missing | Create the empty directory + a stub entry-point script. |
| `.markdownlint-cli2.yaml` missing | Vendor steward's copy verbatim. |
| `.claude/skills.local.yaml.example` missing | Vendor a minimal template documenting the `culture_server_yaml` and `sibling_projects` keys. |
| `CHANGELOG.md` missing | Create a Keep-a-Changelog skeleton with one `## [Unreleased]` heading. |
| `SKILL.md` frontmatter `name` ≠ dir name | Reported only — too many false-positive renames to auto-correct. |
| Hard-coded `/home/...` path in tracked file | Reported only — fix requires understanding intent. |

## Skill upstream policy

Per-skill upstream declarations live in `docs/skill-sources.md`. `doctor`
consults that file when vendoring a skill into a target sibling: each skill
has exactly one canonical source repo, and `doctor` copies from there.

## Out of scope (for the pattern, not for steward)

- Pre-commit hooks (suggested but not required; siblings vary on this).
- Specific CI runners or Python versions beyond ≥3.12.
- Anything Culture-mesh-specific (server manifest, agent definitions) — that
  belongs in `docs/` of the relevant Culture-side project, not in this pattern.
