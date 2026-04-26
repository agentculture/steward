"""End-to-end tests for `steward verify`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from steward.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_verify_against_steward_repo_passes(capsys: pytest.CaptureFixture[str]) -> None:
    """Steward should pass `steward verify` on itself.

    This is the dog-food test: if steward can't verify steward, the pattern
    isn't internally consistent.
    """
    rc = main(["verify", str(REPO_ROOT)])
    captured = capsys.readouterr()
    assert rc == 0, f"verify failed:\n{captured.out}\n{captured.err}"
    assert "verify clean" in captured.out


def test_verify_unknown_target_fails_user_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-directory target exits 1 with a structured error on stderr."""
    rc = main(["verify", "/nonexistent/path/that/should/not/exist"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "error: target is not a directory" in captured.err


def test_verify_json_output_is_parseable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--json` emits a JSON list (empty when clean)."""
    rc = main(["verify", "--json", str(REPO_ROOT)])
    captured = capsys.readouterr()
    assert rc == 0
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert parsed == []


def test_verify_skills_convention_catches_missing_scripts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Skill with SKILL.md but no scripts/ dir is reported."""
    skill = tmp_path / ".claude" / "skills" / "broken"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: broken\ndescription: x\n---\n")
    rc = main(["verify", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "missing scripts/ directory" in captured.out


def test_verify_skills_convention_catches_name_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SKILL.md whose frontmatter name differs from the dir name is reported."""
    skill = tmp_path / ".claude" / "skills" / "real-name"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: wrong-name\ndescription: x\n---\n")
    rc = main(["verify", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "frontmatter name 'wrong-name' != dir 'real-name'" in captured.out
