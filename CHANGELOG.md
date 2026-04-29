# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-04-29

### Added

- docs note in CLAUDE.md and .gitignore comment describing the planned --from-github URL workflow that will replace the override use case (clone the URL into .patients/<slug>/, run --scope siblings against that clone).

### Changed

- doctor write paths are now derived from constants only: <steward_root>/docs/perfect-patient.md for the corpus baseline; <sibling>/docs/steward/steward-suggestions.md for per-sibling reports (with sibling paths from directory listing of --workspace-root, not free-form input). The clone-and-run pattern (`git clone X .patients/<slug>/` + `--workspace-root .patients/<slug>/`) is the supported workflow for regenerating against a different sibling set; --from-github URL will automate it.
- tests/test_cli_doctor_siblings.py write-coverage test now builds a fake steward checkout inside tmp_path (git-init + vendored portability-lint.sh) so the regenerated baseline writes into tmp, never touching REPO_ROOT/docs/perfect-patient.md.

## [0.6.1] - 2026-04-29

### Fixed

- pythonsecurity:S2083 (round 2): _resolve_perfect_patient_path now re-anchors the user-supplied override to workspace via candidate.relative_to(workspace), so the returned path is structurally workspace + validated-relative-tail. This satisfies SonarCloud taint analysis, which did not recognize the previous is_relative_to() check as a sanitizer.
- CI lint failure: black/isort formatting on the test files appended in earlier commits (auto-generated test blocks bypassed local format hooks).

## [0.6.0] - 2026-04-29

### Added

- Workspace-confinement on --perfect-patient-out: paths outside the steward workspace are rejected at the CLI boundary with a remediation hint pointing at .patients/
- Gitignored .patients/ directory at the workspace root for review-mode baselines you do not want committed
- 4 new pytest cases covering _resolve_perfect_patient_path: default, inside-workspace, outside-workspace, and traversal rejection
- CLAUDE.md sections: Workspace-confined writes (and .patients/), Doctor mutation-safety contract

### Changed

- docs/sibling-pattern.md mutation-safety row #5 distinguishes repair-mutation verbs (require --apply) from diagnostic outputs (write by default, skippable via --no-*); retires the contradiction Qodo flagged in PR #9 review
- tests/test_cli_doctor_siblings.py uses .patients/ inside the real REPO_ROOT for the override-write smoke test, with try/finally cleanup

## [0.5.0] - 2026-04-29

### Added

- bats test suite (51 cases) under tests/shell/ covering arity contracts of the 7 vendored skill scripts + portability-lint
- pre-commit config (.pre-commit-config.yaml) wiring markdownlint-cli2 + portability-lint
- CI jobs: doctor (steward eats own dogfood), shellcheck (severity=warning), bats
- Marker-preserved manual-ratchet section in docs/perfect-patient.md (steward.cli._commands._corpus.merge_manual_ratchet)
- CLAUDE.md Quality gates section listing all local checks; README.md Skill supplier role paragraph

### Changed

- portability-lint.sh now fails when working tree has untracked files but the diff vs HEAD is empty (caught a real near-miss in PR #8)
- docs/perfect-patient.md restructured: corpus-derived header + Required/Recommended/Common sections, then a manual-ratchet block (preserved across regeneration) holding the curated Recommended/Optional/Conditional skill tiers

### Fixed

- pr-status.sh: removed unused SONARQUBE_ISSUE variable (shellcheck SC2034)
- portability-lint.sh: silenced false-positive shellcheck SC2088 on intentional literal-tilde regex patterns

## [0.4.0] - 2026-04-29

### Added

- pypi-maintainer skill (renamed from change-package, generalized for any PyPI package)
- jekyll-test skill with end-to-end build + validation script
- Vendored discord-notify, gh-issues, notebooklm, run-tests, sonarclaude skills (canonical home is now steward)
- perfect-patient.md: Optional and Conditional skill tiers (manually curated)

### Changed

- perfect-patient.md Recommended skills tier expanded to include the 7 newly vendored skills
- skill-sources.md: 7 new upstream entries listing steward as canonical owner
- run-tests script: coverage source now resolves from pyproject.toml [tool.coverage.run] (portable across siblings)
- sonarclaude script: project key now resolves from $SONAR_PROJECT or --project (no hard-coded default)

## [0.3.2] - 2026-04-26

### Changed

- `README.md` — document `steward doctor`. The previous Usage section listed only `steward show`, leaving the second verb (added in 0.2.0 as `verify`, renamed in 0.3.0, refined in 0.3.1) invisible to anyone who only reads the README. Adds both scopes (`--scope self` default, `--scope siblings`), the `--json` / `--check` flags, the `--apply` roadmap caveat, and cross-links to `docs/sibling-pattern.md` (the contract `doctor` honors) and `docs/perfect-patient.md` (the auto-generated corpus baseline).

## [0.3.1] - 2026-04-26

### Changed

- `docs/perfect-patient.md` — first real corpus snapshot, generated by running `steward doctor --scope siblings` against the `agentculture` workspace (8 agents across 6 sibling repos: agex, culture, culture-sonar-cli, daria, reachy_nova, shushu). Replaces the placeholder shipped in 0.3.0. Required `culture.yaml` fields settle at `backend` + `suffix`; `acp_command` and `model` fall in the recommended band; common skills baseline is empty so far while `pr-review` and `run-tests` show up as recommended.
- Skill bullets in the synthesized `perfect-patient.md` now carry a high-level one-liner per skill, sourced from each `SKILL.md`'s frontmatter `description:` (first-wins across the corpus, trimmed to the first sentence or 200 chars). Adds `Baseline.skill_descriptions: dict[str, str]` and a new `_skill_bullets` renderer; bare-bullet fallback when no description can be parsed. Reader can now scan the baseline and see what each skill ideally does without opening the upstream repo.

### Fixed

- `render_perfect_patient` no longer emits markdown that fails `markdownlint`. The empty-set placeholder switched from `_(none)_` (tripped MD036 emphasis-as-heading) to plain `None yet.`, and `_refresh_perfect_patient` no longer appends an extra trailing newline on top of the one the renderer already produces (which previously left a blank EOF line and tripped MD012).

## [0.3.0] - 2026-04-26

### Added

- `steward doctor --scope siblings` walks every `culture.yaml` in the workspace, scores each declared agent against a corpus-derived baseline, writes per-target feedback into `<target>/docs/steward/steward-suggestions.md` (gated by a marker line so hand-written content there is preserved), and refreshes `docs/perfect-patient.md` in the steward checkout. Diagnostic-only — corpus mode never exits non-zero on per-agent drift.
- `docs/perfect-patient.md` — committed placeholder; populated on each `--scope siblings` run with required/recommended `culture.yaml` fields, the common skills baseline, common `CLAUDE.md` sections, and corpus stats.
- `steward/cli/_commands/_corpus.py` — pure helpers (`discover_agents`, `synthesize_baseline`, `render_perfect_patient`, `score_culture_yaml_shape`, `score_agent_against_baseline`, `write_repo_report`) used by `doctor --scope siblings`. Tested in isolation by `tests/test_corpus.py`.
- `tests/test_corpus.py` and `tests/test_cli_doctor_siblings.py` — unit + end-to-end coverage for corpus mode (discovery handles both `agents:` lists and flat root-level `suffix:` shapes; baseline classification by frequency; report writer is idempotent and preserves hand-written content; JSON output shape; empty-workspace diagnostic; --no-write-reports / --no-refresh-perfect-patient gates).

### Changed

- **Renamed `steward verify` → `steward doctor`** (single-repo mode). Same checks (`portability`, `skills-convention`), same flags (`--json`, `--check`), same exit semantics (non-zero on findings). New flags: `--scope {self,siblings}` (default `self` is backward-compatible with `verify`), `--workspace-root`, `--no-write-reports`, `--no-refresh-perfect-patient`, `--perfect-patient-out`. No `verify` alias kept — this is a breaking CLI change.
- Added `pyyaml>=6.0` as the first runtime dependency. Required to parse sibling `culture.yaml` manifests in corpus mode; the existing `agent-config` skill already shells out to a Python+PyYAML one-liner, so the dep was implicit.
- `docs/sibling-pattern.md` and `CLAUDE.md` Roadmap section rewritten to describe `doctor`'s two scopes (self / siblings) and reposition the planned `--apply` repair handlers as the next layer.

## [0.2.0] - 2026-04-26

### Added

- `steward verify <path>` — read-only diagnosis of a sibling repo against the
  AgentCulture sibling pattern. Two checks today: `portability` (runs steward's
  own vendored `portability-lint.sh --all` with `cwd=<target>`, so the target
  doesn't need to vendor it and `verify` only ever executes a known-trusted
  script) and `skills-convention` (every `SKILL.md` has a sibling `scripts/`
  directory and a matching frontmatter `name`). Aggregates findings across all
  selected checks; human-readable findings go to stderr, `--json` puts the
  structured findings list on stdout. `--check <name>` repeatable. Exits 1 if
  any finding was reported.
- `docs/sibling-pattern.md` — single source of truth for the AgentCulture
  sibling pattern (12 required artifacts, 5 machine-checkable invariants,
  5 deterministic repairs). Consumed by `steward verify`; will be consumed
  by the future `steward doctor`.
- `docs/skill-sources.md` — per-skill upstream declarations and vendoring
  policy so `doctor` can vendor deterministically.
- `.claude/skills/doc-test-alignment/` — stub skill describing the intended
  doc/test alignment workflow. Implementation TBD.
- `tests/test_skills_convention.py` — repo-level invariants for steward's own
  skills (every skill has SKILL.md + scripts/, frontmatter name matches dir,
  no per-user/home-dir paths in skill scripts).
- `tests/test_cli_verify.py` — end-to-end tests for the new verb, including a
  dogfood test that runs `steward verify` against steward itself.

### Changed

- `CLAUDE.md` gains a "Roadmap (CLI surface)" section naming `verify` and
  `doctor` as the next two verbs.
- `.markdownlint-cli2.yaml` header comment reworded to avoid tripping the
  portability lint with its own self-reference (caught by the new
  `tests/test_cli_verify.py` dogfood test on first run).
- `tests/test_cli.py` help-output assertion loosened to match individual
  verb names instead of the literal `{show}` group, so adding verbs doesn't
  break it.

## [0.1.2] - 2026-04-26

### Added

- `.markdownlint-cli2.yaml` at repo root mirroring afi-cli/cfafi (3143024675).
- `lint` job in tests.yml running black --check, isort --check, flake8, bandit -c pyproject.toml, and markdownlint-cli2 (3143024677).
- `.flake8` config so flake8 honors the 100-char line length and ignores E203/W503 (matches black).

### Changed

- `steward show` walk-up now stops at the git repo boundary so the script is only ever resolved within the user's current checkout (3143024681; eliminates the path-injection risk).
- `bump.py` changelog formatter emits single blank lines between elements (markdownlint MD012 compliant). Past triple-newlines in the 0.1.1 entry cleaned up.
- Tightened the `version-bump` SKILL.md: dropped the numbered Workflow section, replaced with short prose pointing to the script (3143024680).
- Replaced the inline `# noqa: S603 - explanation` syntax in show.py with a separate explanatory comment block above and a bare `# noqa: S603` (SonarCloud python:S7632).

### Fixed

- CLAUDE.md: code-block fence now `text`-tagged (markdownlint MD040).

## [0.1.1] - 2026-04-26

### Changed

- test_python_m_steward_version uses sys.executable instead of literal python (3143024074).
- show.sh returns exit 2 for user errors (unknown suffix) and exit 1 for env errors (missing manifest, missing PyYAML); the steward CLI maps these to USER_ERROR/ENV_ERROR respectively (3143024081).

### Fixed

- bump.py docstring no longer overstates what gets updated; the `__init__.py` rewrite is conditional and is a no-op for steward (3143024085).

## [0.1.0] - 2026-04-26

### Added

- `pyproject.toml` (steward-cli) with hatchling backend, `steward = "steward.cli:main"` entry point, Python ≥3.12. Zero runtime dependencies.
- `steward/` package: `__init__.py` (importlib.metadata version lookup), `__main__.py` (`python -m steward`), `cli/` (argparse entry point modeled on afi-cli's pattern with structured `StewardError` plumbing).
- `steward show <target>` subcommand that wraps the `agent-config` skill's `show.sh`. Walks up from cwd to locate the script; fails cleanly with a remediation hint if not in a Steward checkout.
- `tests/test_cli.py` — pytest suite covering `--version`, no-args help, unknown-subcommand error path, the `show` happy path against this repo, and `show` outside a Steward checkout.
- `.github/workflows/tests.yml` — pytest on every PR + push to main, with a `version-check` job that fails if `pyproject.toml` version isn't bumped (mirrors the cfafi convention; allows the initial scaffold via the "no main version yet" branch).
- `.github/workflows/publish.yml` — push to main publishes to PyPI via OIDC Trusted Publishing; PRs publish a `.dev<run_number>` to TestPyPI for smoke-testing. Fork PRs are skipped (no OIDC context).
- `.claude/skills/version-bump/` — vendored from afi-cli; bumps `pyproject.toml` and prepends a Keep-a-Changelog entry.

### Changed

- `CLAUDE.md` — drop the "greenfield" framing, document the build/test/publish convention, and replace "Conventions to apply when scaffolding" with "Conventions in use".
- `README.md` — add Install + Usage sections.
