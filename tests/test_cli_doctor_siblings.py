"""End-to-end tests for `steward doctor --scope siblings`.

Builds a fake workspace under ``tmp_path`` containing a few sibling
repos (each with a ``culture.yaml``), runs the CLI against it via
``--workspace-root``, and asserts on:

- the per-target ``docs/steward/steward-suggestions.md`` file
- the synthesized ``docs/perfect-patient.md`` in the steward checkout
- the JSON output shape

Note: corpus mode still resolves the steward checkout from cwd
(needed for `docs/perfect-patient.md` and the vendored
``portability-lint.sh``). Tests use the real steward checkout for
that — only the *workspace* is faked.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from steward.cli import main
from steward.cli._commands import _corpus

REPO_ROOT = Path(__file__).resolve().parent.parent


def _seed_sibling(workspace: Path, name: str, agents: list[dict]) -> Path:
    repo = workspace / name
    repo.mkdir()
    (repo / "culture.yaml").write_text(yaml.safe_dump({"agents": agents}))
    return repo


def test_doctor_siblings_writes_reports_and_perfect_patient(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _seed_sibling(workspace, "alpha", [{"suffix": "a", "backend": "claude"}])
    _seed_sibling(
        workspace,
        "beta",
        [
            {"suffix": "b", "backend": "claude", "model": "x"},
            {"suffix": "c", "backend": "acp"},
        ],
    )
    # `--perfect-patient-out` is constrained to live inside the steward
    # workspace. .patients/ is the gitignored convention for review-mode
    # baselines (see CLAUDE.md). Write to a uniquely-named sub-path there
    # and clean up after — keeps the test side-effect-free in git terms.
    patients_dir = REPO_ROOT / ".patients"
    pp_out = patients_dir / f"test-{tmp_path.name}.md"

    # corpus mode resolves the steward checkout from cwd; run from the real one.
    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        rc = main(
            [
                "doctor",
                "--scope",
                "siblings",
                "--workspace-root",
                str(workspace),
                "--perfect-patient-out",
                str(pp_out),
            ]
        )
    finally:
        os.chdir(cwd)

    captured = capsys.readouterr()
    try:
        assert rc == 0, f"unexpected failure:\n{captured.out}\n{captured.err}"
        assert "doctor clinic" in captured.out
        assert "3 agent(s) across 2 repo(s)" in captured.out

        # Each target now has the report file with the marker.
        for repo_name in ("alpha", "beta"):
            report = workspace / repo_name / _corpus.REPORT_RELPATH
            assert report.is_file(), f"missing report for {repo_name}"
            text = report.read_text()
            assert _corpus.REPORT_MARKER_PREFIX in text
            assert "# Steward suggestions" in text

        # perfect-patient.md got refreshed at the override location.
        assert pp_out.is_file()
        assert "# Perfect patient" in pp_out.read_text()
    finally:
        # Clean up the .patients/ artifact we created (gitignored, but
        # leaving stale files around between runs is sloppy).
        if pp_out.exists():
            pp_out.unlink()
        # Remove the .patients/ dir if we made it empty.
        if patients_dir.is_dir() and not any(patients_dir.iterdir()):
            patients_dir.rmdir()


def test_doctor_siblings_json_output_is_parseable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _seed_sibling(workspace, "alpha", [{"suffix": "a", "backend": "claude"}])

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        rc = main(
            [
                "doctor",
                "--scope",
                "siblings",
                "--json",
                "--no-write-reports",
                "--no-refresh-perfect-patient",
                "--workspace-root",
                str(workspace),
            ]
        )
    finally:
        os.chdir(cwd)

    captured = capsys.readouterr()
    assert rc == 0
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    # Every entry must carry the documented fields.
    for entry in parsed:
        assert "scope" in entry
        assert "repo" in entry
        assert "check" in entry
        assert "message" in entry


def test_doctor_siblings_no_write_skips_report_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _seed_sibling(workspace, "alpha", [{"suffix": "a", "backend": "claude"}])

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        rc = main(
            [
                "doctor",
                "--scope",
                "siblings",
                "--no-write-reports",
                "--no-refresh-perfect-patient",
                "--workspace-root",
                str(workspace),
            ]
        )
    finally:
        os.chdir(cwd)

    capsys.readouterr()  # drain output
    assert rc == 0
    assert not (workspace / "alpha" / _corpus.REPORT_RELPATH).exists()


def test_doctor_siblings_empty_workspace_is_a_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        rc = main(
            [
                "doctor",
                "--scope",
                "siblings",
                "--no-refresh-perfect-patient",
                "--workspace-root",
                str(workspace),
            ]
        )
    finally:
        os.chdir(cwd)

    captured = capsys.readouterr()
    assert rc == 0
    assert "no culture.yaml agents discovered" in captured.err
