"""End-to-end tests for ``steward announce-skill-update``.

Mirrors the test conventions in ``tests/test_cli_doctor.py``: invoke the
CLI through ``steward.cli.main`` and assert on captured stdout/stderr +
exit code.

Network-touching paths (the actual ``post-issue.sh`` invocation) are
covered by a single subprocess-mock test; the rest run against either
the real on-disk steward state (for happy-path realism) or pytest
``tmp_path`` fakes (for parser edge cases).
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from steward.cli import main
from steward.cli._commands import announce_skill_update as asu

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------- pure-function helpers (no CLI plumbing) ----------


def test_consumers_from_ledger_handles_em_dash() -> None:
    """A `—` marker in the downstream cell means no recorded consumers."""
    text = "| `foo` | `steward` (...) | — | notes |\n"
    assert asu._consumers_from_ledger(text, "foo") == []


def test_consumers_from_ledger_extracts_first_backtick_token_per_chunk() -> None:
    """Each comma-separated chunk contributes its first backtick token."""
    text = (
        "| `cicd` | `steward` (...) "
        "| `cfafi` (still named `pr-review`), `culture` (still named `pr-review`) "
        "| n |\n"
    )
    assert asu._consumers_from_ledger(text, "cicd") == ["cfafi", "culture"]


def test_consumers_from_ledger_unknown_skill_returns_empty() -> None:
    text = "| `cicd` | `steward` | `cfafi` | n |\n"
    assert asu._consumers_from_ledger(text, "nonexistent") == []


def test_changelog_excerpt_with_since_excludes_cutoff_block() -> None:
    """`--since 0.6.0` produces output containing 0.7.0 but not 0.6.0."""
    text = (
        "## [0.7.0] - 2026-05-02\n\n### Added\n- foo\n\n"
        "## [0.6.0] - 2026-04-30\n\n### Added\n- bar\n\n"
        "## [0.5.0] - 2026-04-01\n\n### Added\n- baz\n"
    )
    out = asu._changelog_excerpt(text, since="0.6.0", skill="anything")
    assert "## [0.7.0]" in out
    assert "## [0.6.0]" not in out
    assert "## [0.5.0]" not in out


def test_changelog_excerpt_without_since_filters_by_skill_keyword() -> None:
    """Without `--since`, only blocks mentioning the skill survive."""
    text = (
        "## [0.7.0] - 2026-05-02\n\n### Added\n- new cicd subcommand\n\n"
        "## [0.6.0] - 2026-04-30\n\n### Added\n- unrelated thing\n"
    )
    out = asu._changelog_excerpt(text, since=None, skill="cicd")
    assert "## [0.7.0]" in out
    assert "## [0.6.0]" not in out


def test_normalize_repo_passes_explicit_owner_through() -> None:
    assert asu._normalize_repo("octo/repo", org="agentculture") == "octo/repo"


def test_normalize_repo_prefixes_bare_name_with_org() -> None:
    assert asu._normalize_repo("auntiepypi", org="agentculture") == "agentculture/auntiepypi"
    assert asu._normalize_repo("auntiepypi", org="otherorg") == "otherorg/auntiepypi"


# ---------- CLI integration ----------


def test_list_against_real_ledger_returns_known_consumers(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--skill cicd --list` returns the consumers from the live ledger."""
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["announce-skill-update", "--skill", "cicd", "--list"])
    captured = capsys.readouterr()
    assert rc == 0, f"failed:\n{captured.out}\n{captured.err}"
    lines = captured.out.strip().splitlines()
    assert "agentculture/cfafi" in lines
    assert "agentculture/culture" in lines


def test_list_unknown_skill_errors_with_clear_message(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["announce-skill-update", "--skill", "nonexistent-skill", "--list"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no upstream skill" in captured.err


def test_dry_run_renders_six_canonical_sections(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The brief renders the six canonical headers from the template."""
    monkeypatch.chdir(REPO_ROOT)
    rc = main(
        [
            "announce-skill-update",
            "--skill",
            "cicd",
            "--to",
            "agentculture/auntiepypi",
            "--since",
            "0.6.0",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    body = captured.out
    for header in (
        "## What's stale",
        "## Cite locations",
        "## What's in the upstream now",
        "## What to do",
        "## Acceptance criteria",
        "## References",
    ):
        assert header in body, f"missing section: {header}"


def test_dry_run_lists_every_upstream_script(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The brief lists every file currently in the upstream scripts/ dir."""
    monkeypatch.chdir(REPO_ROOT)
    rc = main(
        [
            "announce-skill-update",
            "--skill",
            "cicd",
            "--to",
            "agentculture/auntiepypi",
            "--since",
            "0.6.0",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    scripts_dir = REPO_ROOT / ".claude" / "skills" / "cicd" / "scripts"
    for script in scripts_dir.iterdir():
        if script.is_file():
            assert f"`{script.name}`" in captured.out, f"missing: {script.name}"


def test_dry_run_with_no_consumers_errors_clearly(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A skill with no ledger row and no `--to` exits with a useful hint."""
    monkeypatch.chdir(REPO_ROOT)
    # version-bump exists in the ledger with `cfafi, afi-cli` consumers,
    # so use a skill with no ledger row by passing a real skill name that
    # has no downstream entry. agent-config has `—` in the consumers cell.
    rc = main(
        [
            "announce-skill-update",
            "--skill",
            "agent-config",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "no consumers found" in captured.err
    assert "--to OWNER/REPO" in captured.err


def test_missing_skill_arg_errors(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    with pytest.raises(SystemExit):
        main(["announce-skill-update", "--list"])
    captured = capsys.readouterr()
    assert "--skill" in captured.err


def test_post_invokes_post_issue_with_expected_argv_and_stdin_body(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-dry-run invocation calls post-issue.sh once per consumer
    with `--repo` / `--title` argv and the brief body piped on stdin
    (no `--body-file`, no repo-local staging directory).
    """
    monkeypatch.chdir(REPO_ROOT)
    captured_calls: list[tuple[list[str], str | None]] = []

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        captured_calls.append((list(argv), kwargs.get("input")))
        return mock.Mock(returncode=0, stdout="https://github.com/x/y/issues/1\n", stderr="")

    with mock.patch.object(asu.subprocess, "run", side_effect=fake_run):
        rc = main(
            [
                "announce-skill-update",
                "--skill",
                "cicd",
                "--to",
                "agentculture/auntiepypi",
                "--to",
                "agentculture/cfafi",
                "--since",
                "0.6.0",
            ]
        )
    capsys.readouterr()  # drain
    assert rc == 0
    assert len(captured_calls) == 2
    for argv, stdin_body in captured_calls:
        assert argv[0].endswith("post-issue.sh")
        assert "--repo" in argv
        assert "--title" in argv
        assert "--body-file" not in argv  # bug #3 fix: stdin, not file
        assert stdin_body is not None and "## What's stale" in stdin_body
    repos_called = [argv[argv.index("--repo") + 1] for argv, _ in captured_calls]
    assert repos_called == ["agentculture/auntiepypi", "agentculture/cfafi"]
    # bug #3 fix: no repo-local staging directory should be created.
    assert not (REPO_ROOT / ".local" / "announce-skill-update.body.md").exists()


# ---------- Qodo PR #24 review feedback ----------


def test_since_with_unknown_version_errors_clearly(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug #1: --since with a version not in CHANGELOG must fail fast,
    not silently inline the entire CHANGELOG.
    """
    monkeypatch.chdir(REPO_ROOT)
    rc = main(
        [
            "announce-skill-update",
            "--skill",
            "cicd",
            "--to",
            "agentculture/auntiepypi",
            "--since",
            "99.99.99",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "--since 99.99.99 not found" in captured.err
    assert "pass an existing version" in captured.err


def test_post_oserror_surfaces_env_error_not_unexpected(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug #2: subprocess.run raising OSError (missing/non-exec script)
    must classify as EXIT_ENV_ERROR with a chmod hint, matching
    doctor.py's pattern.
    """
    monkeypatch.chdir(REPO_ROOT)
    with mock.patch.object(asu.subprocess, "run", side_effect=OSError("Exec format error")):
        rc = main(
            [
                "announce-skill-update",
                "--skill",
                "cicd",
                "--to",
                "agentculture/auntiepypi",
                "--since",
                "0.6.0",
            ]
        )
    captured = capsys.readouterr()
    assert rc == 2  # EXIT_ENV_ERROR
    assert "could not execute" in captured.err
    assert "post-issue.sh" in captured.err
    assert "chmod +x" in captured.err
    # Must NOT be the generic _dispatch fallback wrapper.
    assert "unexpected" not in captured.err


def test_consumers_from_ledger_handles_multi_skill_first_cell() -> None:
    """Bug #4: ledger rows with multiple backticked skill names in the
    first cell (e.g. `cfafi`, `cfafi-write`) must still match for any
    of the listed names.
    """
    text = "| `cfafi`, `cfafi-write` | `cfafi` (...) | `someconsumer` | n |\n"
    assert asu._consumers_from_ledger(text, "cfafi") == ["someconsumer"]
    assert asu._consumers_from_ledger(text, "cfafi-write") == ["someconsumer"]
    assert asu._consumers_from_ledger(text, "unrelated") == []
