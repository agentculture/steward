"""``steward show`` — wraps the agent-config skill's show.sh.

The skill (``.claude/skills/agent-config/scripts/show.sh``) is the canonical
implementation. The CLI is just a typed surface so people can run
``steward show ../culture`` instead of remembering the script path.

If the skill script is missing (e.g. someone ``pip install``ed steward-cli
without cloning the repo), the command exits with a clear error pointing at
where the skill should live.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from steward.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, StewardError


def _resolve_skill_script() -> Path:
    """Locate ``.claude/skills/agent-config/scripts/show.sh``.

    Walks up from cwd looking for a ``.claude/skills/agent-config`` directory;
    first match wins. This lets ``steward show`` work from anywhere inside a
    Steward checkout.
    """
    current = Path.cwd().resolve()
    while True:
        candidate = current / ".claude" / "skills" / "agent-config" / "scripts" / "show.sh"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    raise StewardError(
        code=EXIT_ENV_ERROR,
        message="agent-config skill script not found",
        remediation=(
            "run from inside a Steward checkout that contains "
            ".claude/skills/agent-config/scripts/show.sh"
        ),
    )


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "show",
        help="Show a Culture agent's full configuration in one view.",
        description=(
            "Surface a Culture agent's CLAUDE.md, parallel culture.yaml, and "
            ".claude/skills/ index. Wraps the agent-config skill script."
        ),
    )
    parser.add_argument(
        "target",
        help="Path to a project directory or a registered agent suffix.",
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    script = _resolve_skill_script()
    # Capture and forward via Python streams so pytest's capsys/capfd both
    # see the output. Going through sys.stdout/sys.stderr.write keeps the
    # split (skill stdout → CLI stdout, skill stderr → CLI stderr).
    try:
        completed = subprocess.run(  # noqa: S603 - argv is fixed, target is user-supplied positional
            [str(script), args.target],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message=f"could not execute {script}: {exc}",
            remediation="ensure the script is executable (chmod +x)",
        ) from exc
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise StewardError(
            code=EXIT_USER_ERROR if completed.returncode == 2 else EXIT_ENV_ERROR,
            message=f"agent-config script exited {completed.returncode}",
            remediation=f"see stderr from {script.name}",
        )
    return 0
