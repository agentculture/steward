---
name: pypi-maintainer
description: >
  Switch a PyPI package install between the production index, TestPyPI
  pre-release builds, and a local editable checkout. Use when an agent
  maintains a package and needs to verify a TestPyPI dev build before
  promoting to production, or when the user says "install from
  test-pypi", "switch to local", "change package source", or
  "install from pypi".
---

# PyPI Maintainer

Switch the install source for a package the agent maintains. Three sources
are supported: production PyPI, TestPyPI (pre-release / dev builds), and a
local editable checkout. The same script works for any package an
AgentCulture sibling publishes — pass the package name as the first
argument.

## When to use

- Verifying a PR's TestPyPI dev build before merging.
- Reproducing a user-reported bug against the published version.
- Hot-patching against a local checkout while a fix is in flight.
- Restoring the production install after local-mode debugging.

## Usage

```bash
# Production PyPI
bash .claude/skills/pypi-maintainer/scripts/switch-source.sh <package> pypi

# TestPyPI (pre-release dev builds)
bash .claude/skills/pypi-maintainer/scripts/switch-source.sh <package> test-pypi

# TestPyPI, pinned to a specific dev version
bash .claude/skills/pypi-maintainer/scripts/switch-source.sh <package> test-pypi --version 0.4.0.dev42

# Local editable checkout (defaults to current directory)
bash .claude/skills/pypi-maintainer/scripts/switch-source.sh <package> local

# Local editable from an explicit path
bash .claude/skills/pypi-maintainer/scripts/switch-source.sh <package> local --path ../<package>
```

## Why TestPyPI needs special flags

When a package is published to **both** PyPI and TestPyPI, `uv tool install`
finds the production version on PyPI first and never looks at TestPyPI.
The script passes `--index-strategy unsafe-best-match` so uv compares the
two index sets and picks the highest version, plus `--prerelease=allow`
because TestPyPI builds carry dev suffixes (e.g. `0.4.0.dev42`).

## Workflow

1. Run the appropriate command for the source you want.
2. The script prints the resolved version after install.
3. Cross-check that version against the expected one (PR run number, local
   `pyproject.toml`, etc.) before continuing.

## Arguments

| Position / flag | Meaning |
|-----------------|---------|
| `<package>` (required) | The PyPI distribution name, e.g. `steward-cli`, `culture`, `daria-cli`. |
| `<source>` (required)  | One of `pypi`, `test-pypi`, `local`. |
| `--version VERSION`    | Pin to a specific version (TestPyPI builds typically need this). |
| `--path PATH`          | Local-source-only: path to the editable checkout (default: cwd). |
