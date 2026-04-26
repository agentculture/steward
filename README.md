# steward

Steward aligns and maintains resident agents across Culture projects.

## Install

```bash
pip install steward-cli
```

Or, with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install steward-cli
```

## Usage

```bash
steward --version
steward --help

# Show a Culture agent's full configuration in one view
# (CLAUDE.md + the parallel culture.yaml + .claude/skills/ index).
# Run from inside a Steward checkout — the command finds the agent-config
# skill script via a walk-up from the current working directory.
steward show ../culture
steward show ../daria
```

`steward show` is a thin wrapper over the `agent-config` skill at
`.claude/skills/agent-config/scripts/show.sh`. The skill remains the canonical
implementation; the CLI is the typed entry point.

```bash
# Diagnose a single sibling repo against the AgentCulture sibling pattern
# (portability + skills-convention checks). Exits non-zero on findings.
steward doctor ../culture
steward doctor ../culture --json --check portability

# Walk every culture.yaml in the workspace, score each declared agent
# against the corpus baseline, and write per-repo feedback into
# <target>/docs/steward/steward-suggestions.md. Diagnostic-only.
steward doctor --scope siblings
```

`steward doctor` is read-only diagnosis. `--scope self` (default) runs the
single-repo invariant checks against `TARGET`. `--scope siblings` walks every
`culture.yaml` in the workspace, refreshes
[`docs/perfect-patient.md`](docs/perfect-patient.md) from the corpus, and
writes per-target feedback into each sibling's
`docs/steward/steward-suggestions.md`. The repair mode (`--apply`) is on the
roadmap but not implemented yet.

See [`docs/sibling-pattern.md`](docs/sibling-pattern.md) for the contract
`doctor` honors and [`docs/perfect-patient.md`](docs/perfect-patient.md) for
the auto-generated corpus baseline.

See [`CLAUDE.md`](CLAUDE.md) for project-shape, build/test/publish details, and
the skills convention.

## License

MIT — see [`LICENSE`](LICENSE).
