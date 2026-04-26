# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
