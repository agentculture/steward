# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace layout assumption

Path references in this file assume Steward is checked out **alongside** its sibling Culture projects in the same parent directory — i.e. `<workspace>/steward/`, `<workspace>/culture/`, `<workspace>/daria/`. If your checkout layout differs, treat sibling paths below as descriptive (they name the project, not a guaranteed filesystem location).

## What this project is

Steward aligns and maintains **resident agents** across Culture projects. It is a sibling to [`culture`](https://github.com/agentculture/culture) (the IRC-based agent mesh) and [`daria`](https://github.com/agentculture/daria) (the awareness agent) within the broader Organic Development framework — see the workspace-level `CLAUDE.md` (one directory above this repo, when present) for the cross-project overview and the all-backends rule that governs Culture.

"Resident agents" here means the long-lived agent processes that Culture spawns per machine/peer (e.g. `culture start <agent-name>`). Steward's role is to keep those agents' configuration, prompts, and lifecycle policies coherent across the mesh — not to run agents itself.

## Current state

This repo is greenfield. As of the initial commit there is no source, no `pyproject.toml`, no tests, and no build system — just `README.md`, `LICENSE` (MIT, agentculture), and a standard Python `.gitignore` that includes a commented-out `uv.lock` line (Python + uv is the expected stack, matching the rest of the workspace).

**Implication for Claude:** do not fabricate commands, modules, or architecture. When asked to add something, scaffold it deliberately and update this file as conventions emerge. Before claiming "the way we do X here is Y," check whether X actually exists yet.

## Conventions to apply when scaffolding

When the first concrete code arrives, default to the patterns the rest of the workspace already uses (don't reinvent):

- **Packaging:** `uv` + `pyproject.toml` with a `[project.scripts]` entry point. `uv venv && uv pip install -e ".[dev]"`.
- **Tests:** `pytest`, run from the project root.
- **Lint:** `flake8`, `pylint`, `bandit -r src/`, `black`, `isort` — same set as `culture`/`daria`.
- **Versioning:** single source of truth (e.g. `__init__.py` or a `version.py`), bumped via the workspace `version-bump` skill before PRs.
- **Markdown:** `markdownlint-cli2`. Commit a repo-local `.markdownlint-cli2.yaml` at the repo root once a stack is chosen, and lint against that — don't depend on a per-user home-directory config, since results would diverge between contributors and CI.

If you choose differently, write the choice down here so future sessions don't second-guess it.

## Skills convention

Every skill in `.claude/skills/<name>/` ships:

1. `SKILL.md` — explains *why* and *when* to use it. Frontmatter + short prose; no inline 10-step walk-throughs.
2. `scripts/<entry-point>.sh` (or `.py`) — the script that automates the workflow. Following the skill should be "run this script," not "do these ten manual steps." If a skill doesn't have a script, write one before relying on it.
3. **No external path dependencies.** Scripts must not reach into another skill's home-directory copy or any other location outside this repo. If a skill needs functionality from elsewhere, vendor it into the skill's own `scripts/` directory. This makes skills portable across Culture projects (Steward's mission is alignment; that requires copy-paste portability).

Per-machine paths (Culture server manifest location, sibling-project paths, etc.) live in **`.claude/skills.local.yaml`** (git-ignored). A committed `.claude/skills.local.yaml.example` documents every key. Skills read the local file, falling back to the example when the local copy hasn't been created yet.

Steward is a "skills supplier" for the Culture mesh. When a skill stabilizes here, the next step is propagating it to sibling projects (`culture`, `daria`, etc.) — the all-backends rule applied to skills.

## Working with Culture from here

Steward will need to read or write Culture artifacts (agent definitions, server configs, mesh links). Useful entry points:

- Culture CLI: `culture` (server lifecycle, agent start/stop, mesh linking).
- Culture project: [`agentculture/culture`](https://github.com/agentculture/culture) — has its own `CLAUDE.md` with the all-backends rule (any feature added to one of `claude`/`codex`/`copilot`/`acp` backends must land in all four). Sibling-relative path: `../culture` (assumes the workspace layout above).
- Daria: [`agentculture/daria`](https://github.com/agentculture/daria) — reference for an agent that observes and acts on Culture state. Sibling-relative path: `../daria`.

If Steward grows a config schema or CLI surface, treat the all-backends rule as load-bearing: alignment logic must not silently assume one backend.
