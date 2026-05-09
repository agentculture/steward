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


def test_doctor_skills_convention_catches_missing_skill_md(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Skill dir with scripts/ but no SKILL.md is reported on stderr."""
    (tmp_path / ".claude" / "skills" / "broken" / "scripts").mkdir(parents=True)
    rc = main(["doctor", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "missing SKILL.md" in captured.err


def test_doctor_skills_convention_catches_missing_name_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SKILL.md whose frontmatter omits `name:` is reported."""
    skill = tmp_path / ".claude" / "skills" / "no-name"
    (skill / "scripts").mkdir(parents=True)
    # Frontmatter with description but no name: — exercises the
    # `if not match` branch in _check_skills_convention.
    (skill / "SKILL.md").write_text("---\ndescription: x\n---\n")
    rc = main(["doctor", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no `name:` field in frontmatter" in captured.err


def test_doctor_json_output_serializes_findings(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--json` on a target with findings emits parseable JSON with all fields.

    Targets ``Finding.to_dict`` (doctor.py:48) — the structured-output
    serializer that the empty-findings JSON test doesn't exercise.
    """
    (tmp_path / ".claude" / "skills" / "broken" / "scripts").mkdir(parents=True)
    rc = main(["doctor", "--json", "--check", "skills-convention", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list) and parsed
    assert {"check", "path", "message"} <= set(parsed[0].keys())
    assert parsed[0]["check"] == "skills-convention"
    assert parsed[0]["message"] == "missing SKILL.md"


def test_find_git_root_locates_repo_for_known_path() -> None:
    """`_find_git_root` returns the steward checkout root when given a
    file path inside it. Targets doctor.py:66 (the loop-body return)."""
    from steward.cli._commands.doctor import _find_git_root

    root = _find_git_root(REPO_ROOT)
    assert root == REPO_ROOT


def test_dispatch_wraps_unexpected_exception(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-StewardError raised by a handler is wrapped, not re-raised.

    Targets the catch-all branch in `steward.cli.__init__._dispatch` —
    the safety net that prevents Python tracebacks from leaking to the
    user when something the handler didn't anticipate goes wrong.
    """
    import argparse

    from steward.cli import _dispatch

    args = argparse.Namespace(
        func=lambda _a: (_ for _ in ()).throw(ValueError("boom")),
    )
    rc = _dispatch(args)
    captured = capsys.readouterr()
    assert rc != 0
    assert "unexpected: ValueError: boom" in captured.err
