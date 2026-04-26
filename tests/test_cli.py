"""End-to-end tests for the steward CLI surface."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from steward import __version__
from steward.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_flag_prints_version_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`steward --version` prints `steward <version>` to stdout and exits 0."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == f"steward {__version__}"


def test_no_args_prints_help_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`steward` with no args prints help to stdout and returns 0 (doesn't error)."""
    rc = main([])
    assert rc == 0
    captured = capsys.readouterr()
    assert "usage: steward" in captured.out
    assert "{show}" in captured.out


def test_unknown_command_exits_with_user_error_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unknown subcommand routes through StewardError → exit 1 + 'error:' on stderr."""
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus"])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert "hint:" in captured.err


def test_show_command_runs_skill_script_against_repo_root(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`steward show <repo-root>` shells out to the agent-config skill and prints
    the three section headers (CLAUDE.md, culture.yaml, .claude/skills/)."""
    # show.sh resolves the script via Path.cwd() walk. Run it from the repo root
    # so the resolver finds .claude/skills/agent-config/scripts/show.sh.
    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        rc = main(["show", str(REPO_ROOT)])
    finally:
        os.chdir(cwd)

    assert rc == 0
    captured = capsys.readouterr()
    # The skill prints headers; CLAUDE.md is guaranteed in this repo, the other
    # two (culture.yaml, .claude/skills/) are also present after this PR.
    assert "=== " in captured.out
    assert "CLAUDE.md" in captured.out


def test_show_command_in_dir_without_skill_fails_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If no Steward checkout is reachable, `show` fails with a clear hint.

    Dispatched-command errors return an exit code (no SystemExit raised);
    only argparse-level errors raise SystemExit.
    """
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        rc = main(["show", "anything"])
    finally:
        os.chdir(cwd)
    assert rc == 2  # EXIT_ENV_ERROR
    captured = capsys.readouterr()
    assert "agent-config skill script not found" in captured.err


def test_python_m_steward_version() -> None:
    """`python -m steward --version` works (proves __main__.py).

    Uses ``sys.executable`` so the subprocess runs in the same interpreter /
    venv as the test runner — important under ``uv run pytest`` where the
    bare ``python`` on PATH may point elsewhere.
    """
    result = subprocess.run(
        [sys.executable, "-m", "steward", "--version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"steward {__version__}"
