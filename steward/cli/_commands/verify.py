"""``steward verify`` — read-only diagnosis of a sibling repo against the
AgentCulture sibling pattern (`docs/sibling-pattern.md`).

First cut: two checks — portability (delegates to the existing
`portability-lint.sh --all`) and skills-convention (every `SKILL.md` has a
sibling `scripts/` directory). Exit non-zero on the first failure. `--json`
emits structured findings to stdout.

Future checks land here behind `--check <name>` flags. The full set of
invariants is enumerated in `docs/sibling-pattern.md` ("Invariants").
"""

from __future__ import annotations

import argparse
import json as json_mod
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from steward.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, StewardError
from steward.cli._output import emit_diagnostic, emit_result

FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


@dataclass
class Finding:
    check: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"check": self.check, "path": self.path, "message": self.message}


def _resolve_target(raw: str) -> Path:
    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        raise StewardError(
            code=EXIT_USER_ERROR,
            message=f"target is not a directory: {raw}",
            remediation="pass a path to a sibling repo checkout",
        )
    return target


def _check_skills_convention(target: Path) -> list[Finding]:
    """Every `.claude/skills/<name>/SKILL.md` has a sibling `scripts/` dir,
    and the SKILL.md frontmatter `name` matches the directory name."""
    findings: list[Finding] = []
    skills_dir = target / ".claude" / "skills"
    if not skills_dir.is_dir():
        return findings  # No skills is fine; not every sibling has them yet.
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            findings.append(
                Finding(
                    check="skills-convention",
                    path=str(skill_dir.relative_to(target)),
                    message="missing SKILL.md",
                )
            )
            continue
        if not (skill_dir / "scripts").is_dir():
            findings.append(
                Finding(
                    check="skills-convention",
                    path=str(skill_dir.relative_to(target)),
                    message="missing scripts/ directory",
                )
            )
        match = FRONTMATTER_NAME_RE.search(skill_md.read_text())
        if not match:
            findings.append(
                Finding(
                    check="skills-convention",
                    path=str(skill_md.relative_to(target)),
                    message="no `name:` field in frontmatter",
                )
            )
        elif match.group(1) != skill_dir.name:
            findings.append(
                Finding(
                    check="skills-convention",
                    path=str(skill_md.relative_to(target)),
                    message=(f"frontmatter name {match.group(1)!r} != " f"dir {skill_dir.name!r}"),
                )
            )
    return findings


def _check_portability(target: Path) -> list[Finding]:
    """Delegate to `.claude/skills/pr-review/scripts/portability-lint.sh --all`
    if present in the *target* repo. Reports a single finding if the script is
    missing (so the target knows it doesn't have the lint vendored yet).
    """
    script = target / ".claude" / "skills" / "pr-review" / "scripts" / "portability-lint.sh"
    if not script.is_file():
        return [
            Finding(
                check="portability",
                path=str(script.relative_to(target)),
                message="portability-lint.sh not vendored in target",
            )
        ]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [str(script), "--all"],
            cwd=target,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message=f"could not execute {script}: {exc}",
            remediation="ensure the script is executable (chmod +x)",
        ) from exc
    if completed.returncode == 0:
        return []
    return [
        Finding(
            check="portability",
            path=".",
            message=(completed.stdout + completed.stderr).strip()
            or f"portability-lint exited {completed.returncode}",
        )
    ]


CHECKS = {
    "skills-convention": _check_skills_convention,
    "portability": _check_portability,
}


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "verify",
        help="Diagnose a sibling repo against the AgentCulture sibling pattern.",
        description=(
            "Read-only diagnosis. Exits 0 if all checks pass, 1 on any "
            "finding. See docs/sibling-pattern.md for the invariants."
        ),
    )
    parser.add_argument(
        "target",
        help="Path to a sibling repo directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON to stdout instead of human-readable lines.",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=sorted(CHECKS.keys()),
        help=("Run only the named check (repeatable). Default: run all checks."),
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    target = _resolve_target(args.target)
    selected = args.check or sorted(CHECKS.keys())
    findings: list[Finding] = []
    for name in selected:
        findings.extend(CHECKS[name](target))

    if args.json:
        emit_result(json_mod.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if findings:
            for f in findings:
                emit_diagnostic(f"{f.check}: {f.path}: {f.message}", stream=sys.stdout)
        else:
            emit_result(f"verify clean ({len(selected)} checks against {target})")

    return 0 if not findings else 1
