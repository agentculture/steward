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
emits diagnostic *output* (per-target feedback files + the synthesized
baseline) by default and provides ``--no-write-reports`` /
``--no-refresh-perfect-patient`` opt-outs for pure dry-run.
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
    """Locate the *Steward* git checkout root.

    A directory only counts as the Steward checkout if it contains the
    vendored ``portability-lint.sh`` at the expected relative path. This
    rejects sibling Culture repos that happen to share the
    ``.claude/skills/`` layout but ship a different lint surface.
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
                f"run from inside a Steward checkout that contains {PORTABILITY_LINT_RELPATH}"
            ),
        )
    return repo_root


def _resolve_steward_portability_lint() -> Path:
    """Locate steward's own vendored ``portability-lint.sh``.

    Anchors to the Steward checkout root via :func:`_resolve_steward_repo_root`,
    then returns ``<root>/<PORTABILITY_LINT_RELPATH>``. This guarantees the
    script we execute is the one shipped by Steward — not whatever
    `.claude/skills/pr-review/scripts/portability-lint.sh` happens to live
    in an ancestor git checkout (e.g. a sibling Culture repo whose layout
    coincides with Steward's).
    """
    return _resolve_steward_repo_root() / PORTABILITY_LINT_RELPATH


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

    The script is resolved from the Steward checkout root (not the
    target), then invoked with ``cwd=target`` so its ``git ls-files``
    lists target files. This means ``doctor`` works whether or not the
    target has vendored its own copy of the lint, and limits subprocess
    execution to a known-trusted script.
    """
    script = _resolve_steward_portability_lint()
    # bandit S603: argv is a fixed two-element list (resolved script path +
    # literal "--all"); no shell, no expansion. Script path comes from
    # _resolve_steward_portability_lint(), which is anchored to the
    # Steward checkout root via _resolve_steward_repo_root() (verified
    # via the vendored portability-lint.sh sentinel), so the executed
    # binary is fixed by the Steward checkout layout.
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


def _resolve_workspace_root(args: argparse.Namespace, steward_root: Path) -> Path:
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
    return workspace_root


def _resolve_perfect_patient_path(steward_root: Path) -> Path:
    """Where `--scope siblings` writes the regenerated baseline.

    Always `<steward_root>/docs/perfect-patient.md`. There is no override —
    the only path steward writes to is derived from the steward checkout
    itself, never from caller-supplied data. Users who want to regenerate
    against a different sibling set should clone that workspace and run
    doctor against it (with `--workspace-root` or by `cd`-ing into it),
    not redirect output via a path flag.
    """
    return steward_root.resolve() / _corpus.PERFECT_PATIENT_RELPATH


def _refresh_perfect_patient(baseline: _corpus.Baseline, pp_path: Path) -> None:
    pp_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = _corpus.render_perfect_patient(baseline)
    # Force UTF-8 explicitly: the rendered markdown contains non-ASCII glyphs
    # (≥, –, etc.) that crash on systems with a non-UTF-8 default locale.
    existing = pp_path.read_text(encoding="utf-8") if pp_path.is_file() else None
    pp_path.write_text(_corpus.merge_manual_ratchet(rendered, existing), encoding="utf-8")


def _run_repo_checks(repo_path: Path, selected_repo_checks: list[str]) -> list[Finding]:
    """Run the per-repo CHECKS, surfacing env errors as findings instead
    of aborting the whole sibling walk."""
    repo_findings: list[Finding] = []
    for name in selected_repo_checks:
        try:
            repo_findings.extend(CHECKS[name](repo_path))
        except StewardError as err:
            repo_findings.append(
                Finding(check=name, path=".", message=f"check failed: {err.message}")
            )
    return repo_findings


def _score_repo_agents(
    repo_agents: list[_corpus.Agent], baseline: _corpus.Baseline
) -> list[_corpus.AgentFinding]:
    agent_findings: list[_corpus.AgentFinding] = []
    for a in repo_agents:
        agent_findings.extend(_corpus.score_culture_yaml_shape(a, baseline))
        agent_findings.extend(_corpus.score_agent_against_baseline(a, baseline))
    return agent_findings


def _structured_repo_entries(
    repo_name: str,
    repo_findings: list[Finding],
    agent_findings: list[_corpus.AgentFinding],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for f in repo_findings:
        out.append(
            {
                "scope": "repo",
                "repo": repo_name,
                "agent": "",
                "check": f.check,
                "severity": "warning",
                "message": f.message,
            }
        )
    for af in agent_findings:
        out.append({"scope": "agent", **af.to_dict()})
    return out


def _emit_human_summary(
    workspace_root: Path,
    agents: list[_corpus.Agent],
    repos: dict[Path, list[_corpus.Agent]],
    args: argparse.Namespace,
    pp_path: Path | None,
    write_log: list[tuple[Path, str]],
    structured: list[dict[str, str]],
) -> None:
    if not agents:
        emit_diagnostic(f"no culture.yaml agents discovered under {workspace_root}")
        return
    emit_result(
        f"doctor clinic: {len(agents)} agent(s) across {len(repos)} repo(s) "
        f"under {workspace_root}"
    )
    if args.refresh_perfect_patient and pp_path is not None:
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


def _handle_siblings(args: argparse.Namespace) -> int:
    steward_root = _resolve_steward_repo_root()
    workspace_root = _resolve_workspace_root(args, steward_root)

    # Skip steward itself: per-self diagnosis is what `--scope self` is for.
    agents, manifest_errors = _corpus.discover_agents(
        workspace_root, skip_repos={steward_root.name}
    )

    baseline = _corpus.synthesize_baseline(agents)

    pp_path: Path | None = None
    if args.refresh_perfect_patient:
        pp_path = _resolve_perfect_patient_path(steward_root)
        _refresh_perfect_patient(baseline, pp_path)

    selected_repo_checks = args.check or sorted(CHECKS.keys())

    # Group agents by repo so we score per-repo once, write per-repo once.
    repos: dict[Path, list[_corpus.Agent]] = {}
    for a in agents:
        repos.setdefault(a.repo_path, []).append(a)

    structured: list[dict[str, str]] = []
    write_log: list[tuple[Path, str]] = []

    # Surface manifest read/parse errors so a broken culture.yaml doesn't
    # silently disappear from the corpus output.
    for err in manifest_errors:
        structured.append(
            {
                "scope": "repo",
                "repo": err.repo_name,
                "agent": "",
                "check": "manifest",
                "severity": "warning",
                "message": err.message,
            }
        )

    for repo_path, repo_agents in sorted(repos.items(), key=lambda kv: kv[0].name):
        repo_findings = _run_repo_checks(repo_path, selected_repo_checks)
        agent_findings = _score_repo_agents(repo_agents, baseline)
        structured.extend(_structured_repo_entries(repo_path.name, repo_findings, agent_findings))

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
        _emit_human_summary(workspace_root, agents, repos, args, pp_path, write_log, structured)

    # Corpus mode is diagnostic — exit 0 unless we couldn't even start.
    return 0
