# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-26

### Added

- `steward verify <path>` — read-only diagnosis of a sibling repo against the
  AgentCulture sibling pattern. Two checks today: `portability` (delegates to
  the target's `portability-lint.sh --all`) and `skills-convention` (every
  `SKILL.md` has a sibling `scripts/` directory and a matching frontmatter
  `name`). `--json`, `--check <name>` (repeatable), exits 1 on any finding.
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

- bump.py docstring no longer overstates what gets updated; the __init__.py rewrite is conditional and is a no-op for steward (3143024085).

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
