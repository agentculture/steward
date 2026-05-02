"""Unit tests for the pr-review skill's nick-resolution script.

The script resolves the agent's nick from `culture.yaml` (first agent's
`suffix`), falling back to the git-repo basename. Both branches and the
multi-agent ordering guarantee are exercised here so the
`pr-reply.sh`-side signature stays stable across siblings.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "pr-review" / "scripts" / "_resolve-nick.sh"


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q"],
        cwd=path,
        check=True,
    )


def _run(cwd: Path) -> str:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture(autouse=True)
def _require_git_and_script() -> None:
    if not SCRIPT.exists():
        pytest.skip("resolve-nick script not present in this checkout")
    if shutil.which("git") is None:
        pytest.skip("git not available")
    if shutil.which("bash") is None:
        pytest.skip("bash not available")


def test_culture_yaml_first_agent_wins(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "culture.yaml").write_text(
        "agents:\n- suffix: alpha\n  backend: claude\n- suffix: beta\n  backend: acp\n"
    )
    assert _run(tmp_path) == "alpha"


def test_falls_back_to_repo_basename_when_no_yaml(tmp_path: Path) -> None:
    repo = tmp_path / "my-agent"
    repo.mkdir()
    _git_init(repo)
    assert _run(repo) == "my-agent"


def test_flat_root_shape_resolves_to_suffix(tmp_path: Path) -> None:
    """Single-agent repos can use a flat root-level manifest:

        suffix: solo
        backend: claude

    instead of an `agents:` list. The resolver must still find `solo`
    so the regex can't be tightened to require list-prefix indentation.
    """
    _git_init(tmp_path)
    (tmp_path / "culture.yaml").write_text("suffix: solo\nbackend: claude\n")
    assert _run(tmp_path) == "solo"


def test_quoted_suffix_is_unwrapped(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / "culture.yaml").write_text("agents:\n- suffix: 'quoted'\n  backend: claude\n")
    assert _run(tmp_path) == "quoted"
