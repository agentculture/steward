# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.4] - 2026-05-09

### Added

- **Test coverage push: 88.93% → 95.25%.** PR #22 wired the SonarCloud
  coverage upload but the bot was reporting an honest 88.9% on every
  PR; this release adds 17 targeted tests across two new files
  (`tests/test_cli_show.py`, `tests/test_version_fallback.py`) and the
  existing `tests/test_cli_doctor.py` / `tests/test_corpus.py`. New
  coverage hits the easy + medium uncovered lines:
  - `_check_skills_convention` — missing SKILL.md and missing
    frontmatter-`name:` branches.
  - `cli._dispatch` catch-all — non-`StewardError` exceptions get
    wrapped instead of leaking a traceback.
  - `show.py` — running outside any git repo, propagating non-zero
    script exit + stderr, and `OSError` from a non-executable script.
  - `_corpus.py` — `_classify` empty-counter, non-dict YAML rows,
    malformed/missing SKILL.md frontmatter (5 sub-paths), description
    truncation past 200 chars, CLAUDE.md `## ` heading extraction,
    and the `synthesize_perfect_patient` wrapper.
  - `_errors.py` — `StewardError.to_dict()` round-trip.
  - `__init__.py` — `PackageNotFoundError` version fallback (run via a
    Python subprocess that monkeypatches `importlib.metadata.version`,
    since the test environment always has the package installed).
  Test count: 75 → 92. The remaining ~5% is structurally hard (subprocess
  coverage of `__main__.py`, OSError on file I/O during write_repo_report)
  and is documented in the new test-file headers so future readers don't
  chase ghosts.

## [0.9.3] - 2026-05-09

### Added

- **CI-based SonarCloud analysis with code-coverage upload.** The
  existing CI test job already produced `coverage.xml` (pytest-cov), but
  nothing pushed it to SonarCloud — auto-analysis can't ingest external
  coverage, so the bot's "Coverage on New Code" line read `0.0%` on
  every PR. Now wired:
  - New `sonar-project.properties` at repo root declares the project key
    (`agentculture_steward`), source/test layout, and
    `sonar.python.coverage.reportPaths=coverage.xml`.
  - `.github/workflows/tests.yml` adds a `SonarSource/sonarqube-scan-action`
    step after pytest, with `SONAR_TOKEN` from repo secrets and
    `fetch-depth: 0` on checkout (Sonar needs full git history for
    accurate "new code" blame attribution).
  - **Manual prerequisite (one-time):** disable Auto-Analysis in
    SonarCloud (Project → Administration → Analysis Method → switch to
    "Use CI-based analysis"). Otherwise the auto-analysis run races the
    CI scan and the coverage upload is ignored.

### Removed

- The "(0.0% Coverage on New Code)" embarrassment from PR comments.

## [0.9.2] - 2026-05-09

### Fixed

- `cicd/scripts/pr-comments.sh` Section 4 (SonarCloud): three bugs caught
  by qodo on culture's vendored copy of steward 0.9.0
  ([culture#359](https://github.com/agentculture/culture/pull/359),
  patched culture-side under a `# culture-divergence:` header in
  [`41d0e28`](https://github.com/agentculture/culture/commit/41d0e28)).
  Resolves [#19](https://github.com/agentculture/steward/issues/19).
  - **Curl-error distinction.** A real transport failure (DNS, network,
    rate-limit, SonarCloud outage) used to be swallowed by `|| echo '{}'`
    and reported as "project not registered." Curl exit is now captured
    separately and the script prints
    `(curl failed contacting sonarcloud.io — section skipped; …)` so
    operators can tell the two cases apart.
  - **URL-encoded project key.** `SONAR_PROJECT_KEY` overrides containing
    `&`, `=`, or whitespace no longer corrupt the query string; the value
    is passed through `jq -nr '$v|@uri'` before splicing.
  - **Higher `ps` cap with overflow warning.** Bumped `ps=100` →
    `ps=500` (overridable via `SONAR_PS=<n>`, matching the
    `SONAR_PROJECT_KEY` override pattern already in this script) and
    added a one-line warning when `paging.total > issues|length` that
    quotes the exact `SONAR_PS=<total>` value to re-run with, so the
    guidance is actionable instead of telling the operator to "raise ps"
    with no knob to turn.

## [0.9.1] - 2026-05-09

### Added

- `communicate/scripts/fetch-issues.sh` — fetch GitHub issues with
  body + comments via `gh issue view --json …`. Supports single issue,
  range (`191-197`), list (`191 195 197`), and `--repo OWNER/REPO`.
  Passing `--json` explicitly avoids the "Projects (classic) deprecated"
  error that bare `gh issue view` triggers. Resolves
  [#18](https://github.com/agentculture/steward/issues/18).

### Changed

- `communicate` skill description and SKILL.md updated to advertise three
  channels (post / fetch / mesh) instead of two, so harness skill discovery
  surfaces fetch-issues for prompts like "fetch issue #N".
- `docs/skill-sources.md` — communicate row now mentions fetch; the
  canonical-skills opening list dropped `gh-issues`.

### Removed

- Standalone `.claude/skills/gh-issues/` skill — its sole script
  (`gh-issues.sh`) moved into `communicate` as `fetch-issues.sh` so
  cross-repo issue I/O (post + fetch) lives in one skill, matching
  communicate's mission.

### Fixed

## [0.9.0] - 2026-05-08

### Added

- `cicd/scripts/poll-readiness.sh` — readiness loop that exits when all
  required reviewers have posted (or PR closes / cap hits). Mirrors the
  detection heuristic from cfafi's `poll` skill: qodo body contains
  `Code Review by Qodo` AND NOT `Looking for bugs?` placeholder; Copilot
  has at least one top-level review.
- Configurable required-reviewer set via `--require qodo[,copilot]` and
  the `STEWARD_PR_REVIEWERS` env var. Default is **qodo only** because
  Copilot's automated PR-review bot stopped posting top-level reviews on
  agentculture repos in 2026; Copilot status is still detected and
  reported in the headline, just not gated on.
- `workflow.sh poll-readiness <PR>` subcommand wrapping the looper for
  direct/standalone use.
- SonarCloud Section 4 in `pr-comments.sh` (new-issue list, `<owner>_<repo>`
  derived key with `SONAR_PROJECT_KEY` override).
- `SKILL.md` — "Polling for reviewer readiness" section documenting both
  the synchronous `await` path and the preferred asynchronous
  background-subagent pattern (Agent tool with `run_in_background: true`).

### Changed

- `workflow.sh await <PR>` no longer fixed-sleeps for 5 minutes. Default is
  now 30 iterations × 60s of readiness polling; tune with
  `STEWARD_PR_AWAIT_ITERS` and `STEWARD_PR_AWAIT_INTERVAL`.
- `STEWARD_PR_AWAIT_SECONDS` is preserved as a deprecated back-compat shim
  that re-enables the legacy fixed-sleep with a warning on stderr.

### Fixed

- Stale `SKILL.md` Reply-etiquette claim that "Steward currently has no
  SonarCloud integration" — pr-status.sh has queried SonarCloud since the
  cicd rename; pr-comments.sh now does too.

## [0.8.0] - 2026-05-03

### Added

- `scripts/mesh-message.sh` — thin wrapper around `culture channel message` for live mesh pings (unsigned: IRC nick is the speaker).
- Per-channel signature rule in `communicate/SKILL.md`: GitHub issues auto-sign `- steward (Claude)`; mesh messages stay unsigned.

### Changed

- Renamed `coordinate` skill to `communicate` and broadened it to cover Culture mesh ops (`mesh-message.sh` alongside `post-issue.sh`).

## [0.7.0] - 2026-05-02

### Added

- New `coordinate` skill (`.claude/skills/coordinate/`, vendored from
  culture). Wraps `gh issue create` with a self-contained-brief
  convention and an auto-appended `- steward (Claude)` signature so a
  steward agent can hand off work to a sibling-repo agent. Single
  entry-point `scripts/post-issue.sh`.
- `cicd` skill (formerly `pr-review`) gains two scripts vendored from
  culture's PR-flow toolkit:
  - `scripts/create-pr-and-wait.sh` — `gh pr create` + sleep 180s +
    fetch reviewer comments in one shot, exposed as
    `workflow.sh open-pr`.
  - `scripts/wait-and-check.sh` — sleep 180s and re-fetch comments
    after pushing fixes, exposed as `workflow.sh wait-after-push <PR>`.
  Both honor a `--wait SECS` flag. Lighter-weight than the existing
  `await` subcommand, which gates on SonarCloud + unresolved threads.
- `_corpus.PROMOTED_SKILLS` — curated set of skill names that the
  baseline ratchet always merges into the recommended skills,
  regardless of corpus frequency. Initial member: `coordinate`.
  Description default is used only when no corpus SKILL.md provides
  one. Mirrors the 0.4.0 pattern of intentionally raising the bar.

### Changed

- **Renamed `pr-review` skill → `cicd`**. The directory moved (history
  preserved via `git mv`); `doctor.py:38`'s
  `PORTABILITY_LINT_RELPATH`, all docs, tests, and the
  `.claude/skills/agent-config/SKILL.md` inventory line were updated.
  `docs/skill-sources.md` records the rename and keeps `cfafi` and
  `culture` listed as downstream copies that still carry the old
  `pr-review` name on their own cadence (no breakage; downstream
  consumers track the rename when they next vendor).
- `docs/perfect-patient.md` regenerated. New `coordinate` entry under
  recommended skills via the `PROMOTED_SKILLS` ratchet, and the
  GitHub-signing block now references `cicd` instead of `pr-review`.

## [0.6.0] - 2026-05-02

### Added

- `pr-review` skill: `workflow.sh await <PR>` subcommand — sleeps 5 minutes
  (or `STEWARD_PR_AWAIT_SECONDS=<n>`), then runs `pr-status.sh` (CI checks,
  SonarCloud quality gate, OPEN issues, hotspots) and `pr-comments.sh`
  (Qodo / Copilot / SonarCloud / CF Pages comments). Exits non-zero on
  SonarCloud `ERROR` or unresolved threads. Replaces the old
  `sleep 300 && workflow.sh poll <PR>` two-step in the SKILL.md flow so a
  Claude following the skill no longer misses SonarCloud findings.

### Changed

- README.md: rewritten as a public-facing introduction to steward's role —
  sibling-pattern owner, perfect-patient maintainer, skill supplier — with a
  mermaid architecture diagram, real `steward show` / `steward doctor` /
  `steward doctor --scope siblings` sample output, and a status table for
  implemented checks vs planned repair automation. Closes
  [#11](https://github.com/agentculture/steward/issues/11).
- docs/sibling-pattern.md: defines "sibling repo" up front and adds a
  "Perfect patient" subsection clarifying which baseline sections regenerate
  vs are manually curated.
- docs/skill-sources.md: retitled "Skill supplier — canonical skills" with a
  framing intro on the cite-don't-import vendoring model.

## [0.5.0] - 2026-05-02

### Added

- `culture.yaml` for steward itself (`suffix: steward`) so the in-repo `_resolve-nick.sh` finds the nick via the standard path instead of the basename fallback. (The corpus walker still skips the steward repo by name, by design.)
- `pr-review` skill: `_resolve-nick.sh` resolves the agent's nick from `culture.yaml`'s first agent `suffix`, falling back to the git-repo basename.
- `pr-review` skill: `pr-reply.sh --print-body` flag emits the would-be POST body for tests / dry runs.
- `perfect-patient.md`: new "GitHub message signing" section codifying the `- <nick> (Claude)` convention.

### Changed

- `pr-reply.sh` signs posts as `- <nick> (Claude)` instead of the static `- Claude`, so multi-agent PR threads identify which sibling spoke.
- `pr-review` SKILL.md documents the new convention and its resolution chain.

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
