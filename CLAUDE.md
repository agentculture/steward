# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace layout assumption

Path references in this file assume Steward is checked out **alongside** its sibling Culture projects in the same parent directory — i.e. `<workspace>/steward/`, `<workspace>/culture/`, `<workspace>/daria/`. If your checkout layout differs, treat sibling paths below as descriptive (they name the project, not a guaranteed filesystem location).

## What this project is

Steward aligns and maintains **resident agents** across Culture projects. It is a sibling to [`culture`](https://github.com/agentculture/culture) (the IRC-based agent mesh) and [`daria`](https://github.com/agentculture/daria) (the awareness agent) within the broader Organic Development framework — see the workspace-level `CLAUDE.md` (one directory above this repo, when present) for the cross-project overview and the all-backends rule that governs Culture.

"Resident agents" here means the long-lived agent processes that Culture spawns per machine/peer (e.g. `culture start <agent-name>`). Steward's role is to keep those agents' configuration, prompts, and lifecycle policies coherent across the mesh — not to run agents itself.

## Project shape

Distributed as **`steward-cli`** on PyPI (Trusted Publishing). The Python package is `steward`; the binary is `steward`. Layout follows the afi-cli pattern (top-level package, no `src/`):

```text
steward/                    # Python package (pip install steward-cli)
├── __init__.py             # __version__ via importlib.metadata("steward-cli")
├── __main__.py             # python -m steward
└── cli/
    ├── __init__.py         # argparse main(); _StewardArgumentParser
    ├── _errors.py          # StewardError + EXIT_USER_ERROR / EXIT_ENV_ERROR
    ├── _output.py          # emit_result / emit_error / emit_diagnostic
    └── _commands/          # subcommand modules; each has register(sub) + handler
        └── show.py         # `steward show <target>` → wraps agent-config skill
tests/                      # pytest suite
.claude/skills/             # see "Skills convention" below
.github/workflows/          # tests.yml + publish.yml (OIDC Trusted Publishing)
pyproject.toml              # version source-of-truth
CHANGELOG.md                # Keep-a-Changelog
```

## Build / test / publish

- **Install for dev:** `uv sync` (or `uv pip install -e .` then `uv pip install --group dev`).
- **Run CLI from source:** `uv run steward --version` / `uv run python -m steward show ../culture`.
- **Tests:** `uv run pytest -n auto -v`. CI runs on every PR + push to main.
- **Version bump:** `python3 .claude/skills/version-bump/scripts/bump.py {patch|minor|major}` — updates `pyproject.toml` and prepends a CHANGELOG entry. **Required on every PR** (the `version-check` CI job comments on the PR and fails the run if the version matches main; AgentCulture rule, no exceptions for docs/config-only changes).
- **Publish:** push to `main` triggers `.github/workflows/publish.yml` → builds with `uv build` → publishes `steward-cli` to PyPI via Trusted Publishing (no API tokens). PRs publish a `.dev<run_number>` to TestPyPI for smoke-testing. Fork PRs are skipped (no OIDC context). The release is whatever version is in `pyproject.toml` at merge time.

## Conventions in use

- **Packaging:** `uv` + `pyproject.toml` (hatchling backend), `[project.scripts]` entry point.
- **Tests:** `pytest` (xdist + cov-xml in CI). Tests live under `tests/`.
- **Lint:** `flake8`, `bandit`, `black`, `isort`. Run via uv (`uv run black steward tests`, etc.).
- **Versioning:** single source of truth in `pyproject.toml`. `steward.__version__` is read at import time from package metadata — there is no separate `__version__` literal to keep in sync.
- **Markdown:** `markdownlint-cli2` against a repo-local `.markdownlint-cli2.yaml` once one is committed. Don't depend on a per-user home-directory config.

## Skills convention

Every skill in `.claude/skills/<name>/` ships:

1. `SKILL.md` — explains *why* and *when* to use it. Frontmatter + short prose; no inline 10-step walk-throughs.
2. `scripts/<entry-point>.sh` (or `.py`) — the script that automates the workflow. Following the skill should be "run this script," not "do these ten manual steps." If a skill doesn't have a script, write one before relying on it.
3. **No external path dependencies.** Scripts must not reach into another skill's home-directory copy or any other location outside this repo. If a skill needs functionality from elsewhere, vendor it into the skill's own `scripts/` directory. This makes skills portable across Culture projects (Steward's mission is alignment; that requires copy-paste portability).

Per-machine paths (Culture server manifest location, sibling-project paths, etc.) live in **`.claude/skills.local.yaml`** (git-ignored). A committed `.claude/skills.local.yaml.example` documents every key. Skills read the local file, falling back to the example when the local copy hasn't been created yet.

Steward is a "skills supplier" for the Culture mesh. When a skill stabilizes here, the next step is propagating it to sibling projects (`culture`, `daria`, etc.) — the all-backends rule applied to skills.

## Roadmap (CLI surface)

The current CLI ships one verb (`steward show`). The next two verbs are
`verify` (read-only diagnosis against the AgentCulture sibling pattern) and
`doctor` (diagnose-and-fix; default dry-run, `--apply` to commit). Together
they encode steward's mission as code instead of prose:

- `steward verify <path>` — score a target repo against `docs/sibling-pattern.md`.
  Aggregates findings across all selected checks, then exits non-zero if any
  finding was reported. Human-readable findings go to stderr; `--json` emits
  the structured findings list to stdout. The first cut runs steward's own
  vendored `.claude/skills/pr-review/scripts/portability-lint.sh` against the
  target (so the target doesn't need to vendor it), plus a skills-convention
  check (every `SKILL.md` has a sibling `scripts/` entry-point).
- `steward doctor <path>` — repair what `verify` flagged, where the repair is
  unambiguous (missing `scripts/` directory, missing `.markdownlint-cli2.yaml`,
  missing `.claude/skills.local.yaml.example`, etc.). Larger emissions (CLI
  scaffold) land later as additional repair handlers, eventually consuming
  `../afi-cli/afi/cite/_engine.py` rather than re-implementing it.

Per-skill upstreams (which repo owns the canonical copy of `version-bump`,
`pr-review`, etc.) are recorded in `docs/skill-sources.md` so `doctor` can
vendor deterministically.

## Working with Culture from here

Steward will need to read or write Culture artifacts (agent definitions, server configs, mesh links). Useful entry points:

- Culture CLI: `culture` (server lifecycle, agent start/stop, mesh linking).
- Culture project: [`agentculture/culture`](https://github.com/agentculture/culture) — has its own `CLAUDE.md` with the all-backends rule (any feature added to one of `claude`/`codex`/`copilot`/`acp` backends must land in all four). Sibling-relative path: `../culture` (assumes the workspace layout above).
- Daria: [`agentculture/daria`](https://github.com/agentculture/daria) — reference for an agent that observes and acts on Culture state. Sibling-relative path: `../daria`.

If Steward grows a config schema or CLI surface, treat the all-backends rule as load-bearing: alignment logic must not silently assume one backend.
