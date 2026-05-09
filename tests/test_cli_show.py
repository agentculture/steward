"""Edge-case tests for ``steward show``.

The happy-path test lives in ``test_cli.py``
(``test_show_command_runs_skill_script_against_repo_root``); this file
covers the script-resolution failure modes and subprocess error paths
that the happy path doesn't reach: running outside any git repo,
script that exits non-zero with stderr, and non-executable script
(`OSError` from ``subprocess.run``).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from steward.cli import main


def _stage_show_script(repo: Path, body: str) -> Path:
    """Drop a fake agent-config show.sh inside a faux git checkout under ``repo``."""
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    script_dir = repo / ".claude" / "skills" / "agent-config" / "scripts"
    script_dir.mkdir(parents=True)
    script = script_dir / "show.sh"
    script.write_text(body)
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_show_outside_any_git_repo_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running ``steward show`` from a non-git cwd errors cleanly.

    Targets ``show.py`` lines 51-53: when ``_find_git_root`` returns
    ``None``, the resolution walk inspects only cwd (never ancestors)
    and breaks on the first iteration.
    """
    monkeypatch.chdir(tmp_path)  # no .git anywhere up the tree (tmp_path is fresh)
    rc = main(["show", "anything"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "agent-config skill script not found" in captured.err


def test_show_propagates_script_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Non-zero exit + stderr from show.sh is forwarded and surfaces an error.

    Targets ``show.py`` lines 108-115: ``completed.stderr`` write and
    the ``returncode != 0`` branch that maps exit codes onto
    ``StewardError``.
    """
    _stage_show_script(
        tmp_path,
        "#!/usr/bin/env bash\necho 'oh no' >&2\nexit 2\n",
    )
    monkeypatch.chdir(tmp_path)
    rc = main(["show", "doesnt-matter"])
    captured = capsys.readouterr()
    assert rc != 0
    # stderr from the script is forwarded …
    assert "oh no" in captured.err
    # … and the StewardError remediation also lands on stderr.
    assert "agent-config script exited 2" in captured.err


def test_show_handles_non_executable_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A show.sh that exists but isn't executable raises ``OSError``,
    which ``_handle`` wraps into a ``StewardError`` with a chmod hint.

    Targets ``show.py`` lines 100-105 (the ``except OSError`` branch
    around ``subprocess.run``).
    """
    script = _stage_show_script(
        tmp_path,
        "#!/usr/bin/env bash\necho ok\n",
    )
    # Strip every executable bit. ``subprocess.run`` then raises
    # ``PermissionError`` (an ``OSError`` subclass) when the kernel
    # refuses ``execve``.
    script.chmod(script.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    monkeypatch.chdir(tmp_path)

    # Skip if we're somehow root and the chmod didn't take effect
    # (e.g. running tests as root in a container).
    if os.access(script, os.X_OK):
        pytest.skip("running as root or fs ignores exec bit; can't trigger PermissionError")

    rc = main(["show", "doesnt-matter"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "could not execute" in captured.err
    assert "chmod +x" in captured.err
