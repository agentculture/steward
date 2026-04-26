"""Repo-level invariants for steward's own skills.

These are the same checks `steward verify` will run against any sibling repo,
applied here to steward itself so we eat our own dog food and CI catches
regressions before PR review.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


def _skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_has_skill_md(skill_dir: Path) -> None:
    """Every skill directory ships a SKILL.md."""
    assert (skill_dir / "SKILL.md").is_file(), f"missing SKILL.md in {skill_dir}"


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_has_scripts_directory(skill_dir: Path) -> None:
    """Every skill directory ships a `scripts/` directory.

    Per the skills convention in CLAUDE.md: "Following the skill should be
    'run this script,' not 'do these ten manual steps.'" An empty `scripts/`
    (with `.gitkeep`) is acceptable for stub skills that document the
    contract before the implementation lands.
    """
    scripts = skill_dir / "scripts"
    assert scripts.is_dir(), f"missing scripts/ in {skill_dir}"


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_frontmatter_name_matches_dir(skill_dir: Path) -> None:
    """SKILL.md frontmatter `name` equals the directory name."""
    text = (skill_dir / "SKILL.md").read_text()
    match = FRONTMATTER_NAME_RE.search(text)
    assert match, f"no `name:` field in {skill_dir / 'SKILL.md'}"
    assert (
        match.group(1) == skill_dir.name
    ), f"SKILL.md name {match.group(1)!r} != dir {skill_dir.name!r}"


def test_no_per_user_paths_in_skill_scripts() -> None:
    """No `/home/<user>/...` or per-user `~/.dotfile` refs in skill scripts.

    This is the same rule `portability-lint.sh` enforces on PR diffs, applied
    here at the unit-test level so a single-file change can never reintroduce
    a leak that's missed by the diff lint (e.g. a brand-new file added in a
    commit but the lint only ran on a different range).
    """
    offenders: list[str] = []
    home_re = re.compile(r"/home/[a-z][a-z0-9_-]+/")
    # Match the carve-outs from portability-lint.sh: ~/.claude/skills/.../scripts/
    # and ~/.culture/ are allowed; everything else under ~/. is flagged.
    dotfile_re = re.compile(r"~/\.[A-Za-z][A-Za-z0-9_-]*")
    carve_outs = (
        re.compile(r"~/\.claude/skills/[^\s\"]+/scripts/"),
        re.compile(r"~/\.culture/"),
    )

    for skill_dir in _skill_dirs():
        for path in (skill_dir / "scripts").rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if home_re.search(line):
                    offenders.append(f"{path}:{lineno}: hard-coded /home/ path: {line.strip()}")
                for hit in dotfile_re.finditer(line):
                    span_start = hit.start()
                    # Allow the carve-outs by checking if any carve-out matches at this offset.
                    if any(c.match(line, span_start) for c in carve_outs):
                        continue
                    offenders.append(f"{path}:{lineno}: per-user dotfile ref: {line.strip()}")

    assert not offenders, "skills/scripts portability violations:\n  " + "\n  ".join(offenders)
