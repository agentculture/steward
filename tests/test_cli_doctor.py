"""End-to-end tests for `steward doctor` (single-repo mode).

Corpus mode (`--scope siblings`) is exercised in
``tests/test_cli_doctor_siblings.py``; this file covers the single-repo
flow that replaced the old `verify` verb.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from steward.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_doctor_against_steward_repo_passes(capsys: pytest.CaptureFixture[str]) -> None:
    """Steward should pass `steward doctor` on itself.

    This is the dog-food test: if steward can't doctor steward, the pattern
    isn't internally consistent.
    """
    rc = main(["doctor", str(REPO_ROOT)])
    captured = capsys.readouterr()
    assert rc == 0, f"doctor failed:\n{captured.out}\n{captured.err}"
    assert "doctor clean" in captured.out


def test_doctor_unknown_target_fails_user_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-directory target exits 1 with a structured error on stderr."""
    rc = main(["doctor", "/nonexistent/path/that/should/not/exist"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "error: target is not a directory" in captured.err


def test_doctor_self_without_target_errors(capsys: pytest.CaptureFixture[str]) -> None:
    """`steward doctor` with no target and default scope=self errors clearly."""
    rc = main(["doctor"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "target path is required" in captured.err


def test_doctor_json_output_is_parseable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--json` emits a JSON list (empty when clean)."""
    rc = main(["doctor", "--json", str(REPO_ROOT)])
    captured = capsys.readouterr()
    assert rc == 0
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert parsed == []


def test_doctor_skills_convention_catches_missing_scripts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Skill with SKILL.md but no scripts/ dir is reported on stderr."""
    skill = tmp_path / ".claude" / "skills" / "broken"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: broken\ndescription: x\n---\n")
    rc = main(["doctor", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    # Findings are diagnostics → stderr, per the stdout/stderr split in
    # steward.cli._output.
    assert "missing scripts/ directory" in captured.err
    assert captured.out == ""


def test_doctor_skills_convention_catches_name_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SKILL.md whose frontmatter name differs from the dir name is reported."""
    skill = tmp_path / ".claude" / "skills" / "real-name"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: wrong-name\ndescription: x\n---\n")
    rc = main(["doctor", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "frontmatter name 'wrong-name' != dir 'real-name'" in captured.err
    assert captured.out == ""
