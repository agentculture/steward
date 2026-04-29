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


def _seed_fake_steward_root(parent: Path) -> Path:
    """Build the minimum directory tree that satisfies _resolve_steward_repo_root.

    `_resolve_steward_repo_root` requires (1) a git checkout (it walks up
    from cwd looking for `.git/`) and (2) the vendored portability-lint.sh
    at the canonical relpath. Replicate both here, copying the real script
    byte-for-byte so the tests exercise the actual file. Used to keep
    `--scope siblings` write tests fully tmpdir-scoped — never polluting
    the real REPO_ROOT/docs/perfect-patient.md.
    """
    import subprocess

    fake_root = parent / "fake_steward"
    scripts = fake_root / ".claude" / "skills" / "pr-review" / "scripts"
    scripts.mkdir(parents=True)
    real = REPO_ROOT / ".claude" / "skills" / "pr-review" / "scripts" / "portability-lint.sh"
    (scripts / "portability-lint.sh").write_bytes(real.read_bytes())
    (scripts / "portability-lint.sh").chmod(0o755)
    # `_find_git_root` looks for `.git/`; init a bare repo to satisfy that.
    subprocess.run(["git", "init", "-q", str(fake_root)], check=True)
    return fake_root


def test_doctor_siblings_writes_reports_and_perfect_patient(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Use a fake steward checkout inside tmp_path so the regenerated baseline
    # writes into tmp, not into the real REPO_ROOT/docs/perfect-patient.md.
    # Sibling workspace is a peer directory next to it.
    fake_root = _seed_fake_steward_root(tmp_path)
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

    # corpus mode resolves the steward checkout from cwd; run from the fake one.
    cwd = os.getcwd()
    os.chdir(fake_root)
    try:
        rc = main(
            [
                "doctor",
                "--scope",
                "siblings",
                "--workspace-root",
                str(workspace),
            ]
        )
    finally:
        os.chdir(cwd)

    captured = capsys.readouterr()
    assert rc == 0, f"unexpected failure:\n{captured.out}\n{captured.err}"
    assert "doctor clinic" in captured.out
    assert "3 agent(s) across 2 repo(s)" in captured.out

    # All output now lives under .prescriptions/<slug>/ inside the fake
    # steward checkout. Slug derives from workspace_root's basename ("ws").
    prescription_dir = fake_root / ".prescriptions" / "ws"
    assert prescription_dir.is_dir()

    # Per-sibling reports live alongside the baseline, not inside the
    # sibling repos themselves (doctor never writes into other repos).
    for repo_name in ("alpha", "beta"):
        report = prescription_dir / repo_name / _corpus.REPORT_BASENAME
        assert report.is_file(), f"missing prescription report for {repo_name}"
        text = report.read_text()
        assert _corpus.REPORT_MARKER_PREFIX in text
        assert "# Steward suggestions" in text
        # Doctor must NOT have written into the sibling repo.
        assert not (workspace / repo_name / "docs" / "steward").exists()

    # perfect-patient.md is the prescription form, not the canonical doc.
    pp_out = prescription_dir / _corpus.PERFECT_PATIENT_BASENAME
    assert pp_out.is_file()
    assert "# Perfect patient" in pp_out.read_text()
    # And the canonical committed location is untouched.
    assert not (fake_root / "docs" / "perfect-patient.md").exists()


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
    # No prescription dir should have been created anywhere because we
    # passed both --no-write-reports and --no-refresh-perfect-patient.
    assert not (REPO_ROOT / ".prescriptions" / "ws").exists()
    # And doctor never writes into the sibling repos under any flag combo.
    assert not (workspace / "alpha" / "docs" / "steward").exists()


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
