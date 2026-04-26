"""``steward doctor`` — diagnose a sibling repo (or the whole agent corpus)
against the AgentCulture sibling pattern.

Two modes:

* ``--scope self <target>`` (default): same checks the previous ``verify``
  verb ran — `portability` (delegates to steward's own vendored
  `portability-lint.sh --all`) and `skills-convention` (every `SKILL.md`
  has a sibling `scripts/` directory + matching frontmatter `name`).
  Aggregates findings; exits non-zero if any check produced findings.
* ``--scope siblings``: walks ``<workspace_root>/*/culture.yaml``,
  scores every declared agent against a corpus-derived baseline,
  writes ``docs/steward/steward-suggestions.md`` into each target,
  and refreshes ``docs/perfect-patient.md`` in the steward checkout.
  Diagnostic-only — does not exit non-zero on per-agent findings.

The roadmap's ``--apply`` repair mode (create missing `scripts/`,
`.markdownlint-cli2.yaml`, etc.) is not yet implemented; corpus mode
is diagnose-only and self mode never writes anything regardless.
"""

from __future__ import annotations

import argparse
import json as json_mod
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from steward.cli._commands import _corpus
from steward.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, StewardError
from steward.cli._output import emit_diagnostic, emit_result

FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
PORTABILITY_LINT_RELPATH = Path(".claude/skills/pr-review/scripts/portability-lint.sh")


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


def _find_git_root(start: Path) -> Path | None:
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return directory
    return None


def _resolve_steward_repo_root() -> Path:
    """Locate the steward git checkout root (where docs/, .claude/, etc. live).

    Used by corpus mode to write `docs/perfect-patient.md` into the
    right place, and by `_resolve_steward_portability_lint` indirectly
    via the same walk.
    """
    start = Path.cwd().resolve()
    repo_root = _find_git_root(start)
    if repo_root is None:
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message="not inside a git checkout",
            remediation="run from inside a Steward git checkout",
        )
    if not (repo_root / PORTABILITY_LINT_RELPATH).is_file():
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message="not inside the Steward git checkout",
            remediation=(
                f"run from inside a Steward checkout that contains " f"{PORTABILITY_LINT_RELPATH}"
            ),
        )
    return repo_root


def _resolve_steward_portability_lint() -> Path:
    """Locate steward's own vendored ``portability-lint.sh``.

    Walks up from cwd, but **stops at the git repository boundary** (mirrors
    the resolver in :mod:`steward.cli._commands.show`). Running steward's
    own copy — instead of executing whatever script the *target* repo ships —
    keeps ``doctor`` to a fixed, known-trusted code surface.
    """
    start = Path.cwd().resolve()
    repo_root = _find_git_root(start)

    current = start
    while True:
        candidate = current / PORTABILITY_LINT_RELPATH
        if candidate.is_file():
            return candidate
        if current == repo_root or current.parent == current:
            break
        if repo_root is None:
            break
        current = current.parent

    hint = f"run from inside a Steward git checkout that contains {PORTABILITY_LINT_RELPATH}"
    raise StewardError(
        code=EXIT_ENV_ERROR,
        message="steward's portability-lint.sh not found",
        remediation=hint,
    )


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
                    message=f"frontmatter name {match.group(1)!r} != dir {skill_dir.name!r}",
                )
            )
    return findings


def _check_portability(target: Path) -> list[Finding]:
    """Run steward's own vendored ``portability-lint.sh --all`` against the
    target's working tree.

    The script is resolved from the steward checkout (not the target), then
    invoked with ``cwd=target`` so its ``git ls-files`` lists target files.
    This means ``doctor`` works whether or not the target has vendored its
    own copy of the lint, and limits subprocess execution to a known-trusted
    script.
    """
    script = _resolve_steward_portability_lint()
    # bandit S603: argv is a fixed two-element list (resolved script path +
    # literal "--all"); no shell, no expansion. Script path comes from
    # _resolve_steward_portability_lint() which is constrained to the
    # current git checkout, so an attacker can't substitute a different
    # portability-lint.sh from an ancestor directory.
    try:
        completed = subprocess.run(  # noqa: S603
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
        "doctor",
        help="Diagnose Culture agents — single repo, or the whole sibling corpus.",
        description=(
            "Read-only diagnosis. With no flags or `--scope self`, runs "
            "portability + skills-convention checks against a single repo "
            "(see docs/sibling-pattern.md). With `--scope siblings`, walks "
            "every culture.yaml in the workspace, writes a per-target "
            "report, and refreshes docs/perfect-patient.md."
        ),
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Path to a sibling repo directory (required for --scope self).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON to stdout instead of human-readable lines on stderr.",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=sorted(CHECKS.keys()),
        help="Run only the named check (repeatable). Default: run all checks.",
    )
    parser.add_argument(
        "--scope",
        choices=["self", "siblings"],
        default="self",
        help=(
            "self (default): single-repo checks against TARGET. "
            "siblings: walk every culture.yaml in the workspace and write "
            "per-target reports."
        ),
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help=(
            "Override the workspace root for --scope siblings (default: "
            "parent of the steward checkout)."
        ),
    )
    parser.add_argument(
        "--no-write-reports",
        dest="write_reports",
        action="store_false",
        default=True,
        help="(--scope siblings) Don't write docs/steward/steward-suggestions.md into targets.",
    )
    parser.add_argument(
        "--no-refresh-perfect-patient",
        dest="refresh_perfect_patient",
        action="store_false",
        default=True,
        help="(--scope siblings) Don't regenerate docs/perfect-patient.md.",
    )
    parser.add_argument(
        "--perfect-patient-out",
        type=Path,
        default=None,
        help=(
            "(--scope siblings) Override the path for the synthesized "
            "perfect-patient.md (default: <steward-root>/docs/perfect-patient.md)."
        ),
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    if args.scope == "siblings":
        return _handle_siblings(args)
    return _handle_self(args)


def _handle_self(args: argparse.Namespace) -> int:
    if not args.target:
        raise StewardError(
            code=EXIT_USER_ERROR,
            message="target path is required for --scope self",
            remediation="pass a path to a sibling repo, e.g. `steward doctor ../culture`",
        )
    target = _resolve_target(args.target)
    selected = args.check or sorted(CHECKS.keys())
    findings: list[Finding] = []
    for name in selected:
        findings.extend(CHECKS[name](target))

    if args.json:
        # Structured output is the command's *result* — goes to stdout per
        # the steward stdout/stderr split.
        emit_result(json_mod.dumps([f.to_dict() for f in findings], indent=2))
    elif findings:
        # Human-readable findings are diagnostics — stderr by default.
        for f in findings:
            emit_diagnostic(f"{f.check}: {f.path}: {f.message}")
    else:
        emit_result(f"doctor clean ({len(selected)} checks against {target})")

    return 0 if not findings else 1


def _handle_siblings(args: argparse.Namespace) -> int:
    steward_root = _resolve_steward_repo_root()
    workspace_root = (
        args.workspace_root.expanduser().resolve()
        if args.workspace_root is not None
        else steward_root.parent
    )
    if not workspace_root.is_dir():
        raise StewardError(
            code=EXIT_USER_ERROR,
            message=f"workspace root is not a directory: {workspace_root}",
            remediation="pass --workspace-root <existing-dir> or run from a Steward checkout",
        )

    # Skip steward itself: per-self diagnosis is what `--scope self` is for.
    agents = _corpus.discover_agents(workspace_root, skip_repos={steward_root.name})

    baseline = _corpus.synthesize_baseline(agents)

    if args.refresh_perfect_patient:
        pp_path = (
            args.perfect_patient_out.expanduser().resolve()
            if args.perfect_patient_out is not None
            else steward_root / _corpus.PERFECT_PATIENT_RELPATH
        )
        pp_path.parent.mkdir(parents=True, exist_ok=True)
        pp_path.write_text(_corpus.render_perfect_patient(baseline) + "\n")

    selected_repo_checks = args.check or sorted(CHECKS.keys())

    # Group agents by repo so we score per-repo once, write per-repo once.
    repos: dict[Path, list[_corpus.Agent]] = {}
    for a in agents:
        repos.setdefault(a.repo_path, []).append(a)

    structured: list[dict[str, str]] = []
    write_log: list[tuple[Path, str]] = []

    for repo_path, repo_agents in sorted(repos.items(), key=lambda kv: kv[0].name):
        # Repo-level checks (portability + skills-convention) run once per repo.
        repo_findings: list[Finding] = []
        for name in selected_repo_checks:
            try:
                repo_findings.extend(CHECKS[name](repo_path))
            except StewardError as err:
                # Surface env errors per-repo without aborting the whole walk.
                repo_findings.append(
                    Finding(check=name, path=".", message=f"check failed: {err.message}")
                )

        # Per-agent checks (yaml shape + baseline alignment).
        agent_findings: list[_corpus.AgentFinding] = []
        for a in repo_agents:
            agent_findings.extend(_corpus.score_culture_yaml_shape(a, baseline))
            agent_findings.extend(_corpus.score_agent_against_baseline(a, baseline))

        for f in repo_findings:
            structured.append(
                {
                    "scope": "repo",
                    "repo": repo_path.name,
                    "agent": "",
                    "check": f.check,
                    "severity": "warning",
                    "message": f.message,
                }
            )
        for af in agent_findings:
            structured.append({"scope": "agent", **af.to_dict()})

        if args.write_reports:
            body = _corpus.render_repo_report(repo_path, repo_agents, repo_findings, agent_findings)
            try:
                path, status = _corpus.write_repo_report(repo_path, body)
            except OSError as exc:
                emit_diagnostic(f"warning: could not write report into {repo_path.name}: {exc}")
                continue
            write_log.append((path, status))

    if args.json:
        emit_result(json_mod.dumps(structured, indent=2))
    else:
        if not agents:
            emit_diagnostic(f"no culture.yaml agents discovered under {workspace_root}")
        else:
            emit_result(
                f"doctor clinic: {len(agents)} agent(s) across {len(repos)} repo(s) "
                f"under {workspace_root}"
            )
            if args.refresh_perfect_patient:
                emit_diagnostic(f"perfect-patient.md refreshed at {pp_path}")
            for path, status in write_log:
                emit_diagnostic(f"  {status}: {path}")
            for entry in structured:
                if entry["scope"] == "repo":
                    emit_diagnostic(f"  [{entry['repo']}] {entry['check']}: {entry['message']}")
                else:
                    emit_diagnostic(
                        f"  [{entry['repo']}/{entry['agent']}] "
                        f"{entry['severity']} {entry['check']}: {entry['message']}"
                    )

    # Corpus mode is diagnostic — exit 0 unless we couldn't even start.
    return 0
