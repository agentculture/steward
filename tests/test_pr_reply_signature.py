"""Unit tests for the cicd skill's signature behavior.

`pr-reply.sh --print-body` produces the exact body that would be POSTed
to GitHub without making any network calls. Two branches matter:
unsigned input gets `- <nick> (Claude)` appended; an already-signed
body is left untouched.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude" / "skills" / "cicd" / "scripts" / "pr-reply.sh"
RESOLVE = REPO_ROOT / ".claude" / "skills" / "cicd" / "scripts" / "_resolve-nick.sh"


@pytest.fixture(autouse=True)
def _require_scripts() -> None:
    if not SCRIPT.exists() or not RESOLVE.exists():
        pytest.skip("cicd scripts not present in this checkout")
    if shutil.which("bash") is None:
        pytest.skip("bash not available")


def _print_body(body: str) -> str:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--print-body", "1", "1", body],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_unsigned_body_gets_nick_appended() -> None:
    out = _print_body("hello reviewer")
    assert out.rstrip("\n").endswith("- steward (Claude)")
    assert out.startswith("hello reviewer\n")


def test_already_signed_body_is_left_alone() -> None:
    pre_signed = "thanks\n\n- steward (Claude)"
    out = _print_body(pre_signed).rstrip("\n")
    # Exactly one signature line; no doubled-up signing.
    assert out == pre_signed
    assert out.count("- steward (Claude)") == 1
