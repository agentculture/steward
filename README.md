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

See [`CLAUDE.md`](CLAUDE.md) for project-shape, build/test/publish details, and
the skills convention.

## License

MIT — see [`LICENSE`](LICENSE).
