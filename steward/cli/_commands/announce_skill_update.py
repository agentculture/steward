"""``steward announce-skill-update`` — broadcast a migration brief to the
known consumers of a steward-vendored skill.

Renders the canonical six-section brief from live state (the upstream
``scripts/`` listing, a ``CHANGELOG.md`` excerpt, and the consumer list
from ``docs/skill-sources.md``), then pipes per-consumer through
``.claude/skills/communicate/scripts/post-issue.sh`` (which preserves the
auto-signature ``- steward (Claude)``).

This verb is steward-specific: it knows steward's ledger format, its
template location, and its "skills supplier" role. The portable
primitives (``post-issue.sh``, ``fetch-issues.sh``, ``mesh-message.sh``)
stay in the ``communicate`` skill so downstream vendors of that skill
inherit only what they need.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from steward.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, StewardError
from steward.cli._output import emit_diagnostic, emit_result

POST_ISSUE_RELPATH = Path(".claude/skills/communicate/scripts/post-issue.sh")
TEMPLATE_RELPATH = Path(
    ".claude/skills/communicate/scripts/templates/skill-update-brief.md"
)
LEDGER_RELPATH = Path("docs/skill-sources.md")
CHANGELOG_RELPATH = Path("CHANGELOG.md")
SKILLS_RELPATH = Path(".claude/skills")
DEFAULT_ORG = "agentculture"

PLACEHOLDER_KEYS = (
    "SKILL",
    "UPSTREAM_SCRIPT_COUNT",
    "UPSTREAM_SCRIPT_LIST",
    "CHANGELOG_BLOCK",
    "DELTA_BLOCK",
    "NOTE_BLOCK",
)


def _find_git_root(start: Path) -> Path | None:
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return directory
    return None


def _resolve_repo_root() -> Path:
    """Locate the steward repo root.

    A directory only counts as steward if it carries
    ``.claude/skills/communicate/scripts/post-issue.sh`` — same
    git-boundary discipline as ``doctor._resolve_steward_repo_root``.
    """
    start = Path.cwd().resolve()
    repo_root = _find_git_root(start)
    if repo_root is None:
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message="not inside a git checkout",
            remediation="run from a steward checkout",
        )
    if not (repo_root / POST_ISSUE_RELPATH).is_file():
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message=f"missing {POST_ISSUE_RELPATH} — not a steward checkout?",
            remediation="run from a steward repo that vendors the communicate skill",
        )
    return repo_root


def _consumers_from_ledger(ledger_text: str, skill: str) -> list[str]:
    """Parse the 'Downstream copies' cell of ``docs/skill-sources.md``.

    Row shape::

        | `cicd` | `steward` (...) | `cfafi` (still ...), `culture` (...) | ... |

    For each comma-separated chunk in the third cell, the first
    backtick-wrapped token is the consumer's bare repo name. An em-dash
    (``—``) or hyphen marker means no recorded consumers.
    """
    for line in ledger_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue
        # First cell may list multiple backticked skill names
        # (e.g. `cfafi`, `cfafi-write` in the ledger today). Extract all
        # tokens and check membership rather than exact-match the cell.
        skill_tokens = re.findall(r"`([^`]+)`", cells[0])
        if skill not in skill_tokens:
            continue
        cell = cells[2]
        if cell in ("", "—", "-"):
            return []
        consumers: list[str] = []
        for chunk in cell.split(","):
            match = re.search(r"`([^`]+)`", chunk)
            if match:
                consumers.append(match.group(1))
        return consumers
    return []


def _changelog_excerpt(text: str, *, since: str | None, skill: str) -> str:
    """Slice ``CHANGELOG.md`` for the brief.

    With ``since``: every ``## [VERSION]`` block from the top down to but
    excluding the ``[since]`` block. With ``since=None``: every block
    whose body mentions ``skill``.
    """
    blocks = re.split(r"(?m)^(?=## \[)", text)
    output: list[str] = []
    for block in blocks:
        if not block.startswith("## ["):
            continue
        match = re.match(r"## \[([^\]]+)\]", block)
        if not match:
            continue
        version = match.group(1)
        if since is not None:
            if version == since:
                break
            output.append(block)
        else:
            if skill in block:
                output.append(block)
    return "".join(output).rstrip() + "\n"


def _upstream_scripts(scripts_dir: Path) -> list[str]:
    """Return the alphabetical list of script *files* in ``scripts/``.

    Subdirectories (``templates/``) are skipped; only top-level files
    count, matching the bash wrapper's ``find -maxdepth 1 -type f``.
    """
    return sorted(p.name for p in scripts_dir.iterdir() if p.is_file())


def _render_brief(
    template_path: Path,
    *,
    skill: str,
    upstream_scripts: list[str],
    changelog_block: str,
    note_block: str = "",
    delta_block: str = "",
) -> str:
    """Substitute ``{{NAME}}`` placeholders, strip lint-only HTML
    comments, and collapse blank-line runs.
    """
    raw = template_path.read_text()
    # Strip single-line HTML comments (used for markdownlint disables in
    # the template source — invisible on GitHub but noisy in the raw
    # issue body).
    raw = re.sub(r"^<!--.*?-->\n", "", raw, flags=re.MULTILINE)
    script_list_md = "\n".join(f"- `{name}`" for name in upstream_scripts)
    fields = {
        "SKILL": skill,
        "UPSTREAM_SCRIPT_COUNT": str(len(upstream_scripts)),
        "UPSTREAM_SCRIPT_LIST": script_list_md,
        "CHANGELOG_BLOCK": changelog_block,
        "DELTA_BLOCK": delta_block,
        "NOTE_BLOCK": note_block,
    }
    for key in PLACEHOLDER_KEYS:
        raw = raw.replace("{{" + key + "}}", fields.get(key, ""))
    raw = re.sub(r"\n{3,}", "\n\n", raw).lstrip("\n")
    return raw


def _normalize_repo(name: str, *, org: str) -> str:
    return name if "/" in name else f"{org}/{name}"


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "announce-skill-update",
        help="Broadcast a migration brief to consumers of a vendored skill.",
        description=(
            "Render the canonical 'vendored skill drifted' brief from "
            "live state (upstream scripts/ listing + CHANGELOG excerpt + "
            "consumer list from docs/skill-sources.md) and post it to "
            "each consumer via communicate's post-issue.sh."
        ),
    )
    parser.add_argument("--skill", required=True, help="Skill name in .claude/skills/<NAME>/.")
    parser.add_argument(
        "--to",
        action="append",
        default=[],
        metavar="OWNER/REPO",
        help="Override consumer list (repeat). Bare names get --org prefix.",
    )
    parser.add_argument(
        "--org",
        default=DEFAULT_ORG,
        help=f"Default org for bare consumer names (default: {DEFAULT_ORG}).",
    )
    parser.add_argument(
        "--since",
        metavar="VERSION",
        help="CHANGELOG cutoff (exclusive). Without it, keyword-filter by skill name.",
    )
    parser.add_argument(
        "--note-file",
        type=Path,
        metavar="PATH",
        help="Free-text appended after the upstream script list (skill-specific gotchas).",
    )
    parser.add_argument(
        "--title",
        help="Override the default issue title.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered brief to stdout instead of posting.",
    )
    parser.add_argument(
        "--list",
        dest="list_only",
        action="store_true",
        help="Print derived consumer list and exit.",
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root()

    upstream_scripts_dir = repo_root / SKILLS_RELPATH / args.skill / "scripts"
    if not upstream_scripts_dir.is_dir():
        raise StewardError(
            code=EXIT_USER_ERROR,
            message=f"no upstream skill at .claude/skills/{args.skill}/scripts/",
            remediation="check spelling, or vendor the skill into this repo first",
        )

    if args.to:
        consumers = [_normalize_repo(r, org=args.org) for r in args.to]
    else:
        ledger_path = repo_root / LEDGER_RELPATH
        ledger_text = ledger_path.read_text() if ledger_path.is_file() else ""
        consumers = [
            _normalize_repo(c, org=args.org)
            for c in _consumers_from_ledger(ledger_text, args.skill)
        ]

    if not consumers:
        raise StewardError(
            code=EXIT_USER_ERROR,
            message=f"no consumers found for skill '{args.skill}'",
            remediation=(
                "pass --to OWNER/REPO explicitly, or add a row + downstream "
                "entry to docs/skill-sources.md"
            ),
        )

    if args.list_only:
        emit_result("\n".join(consumers))
        return 0

    template_path = repo_root / TEMPLATE_RELPATH
    if not template_path.is_file():
        raise StewardError(
            code=EXIT_ENV_ERROR,
            message=f"missing brief template at {TEMPLATE_RELPATH}",
            remediation="restore the template from steward main",
        )

    changelog_path = repo_root / CHANGELOG_RELPATH
    if changelog_path.is_file():
        changelog_text = changelog_path.read_text()
        if args.since is not None and f"## [{args.since}]" not in changelog_text:
            # Without this guard, _changelog_excerpt's exact-match cutoff
            # never trips and we'd inline the entire CHANGELOG into the
            # brief — silently producing an oversized, misleading post.
            raise StewardError(
                code=EXIT_USER_ERROR,
                message=f"--since {args.since} not found in CHANGELOG.md",
                remediation="pass an existing version (see CHANGELOG headings)",
            )
        changelog_block = _changelog_excerpt(
            changelog_text, since=args.since, skill=args.skill
        )
        if not changelog_block.strip():
            changelog_block = (
                f"_(no CHANGELOG entries mention `{args.skill}` since cutoff)_"
            )
    else:
        changelog_block = f"_(no CHANGELOG.md found at {CHANGELOG_RELPATH})_"

    note_block = ""
    if args.note_file is not None:
        if not args.note_file.is_file():
            raise StewardError(
                code=EXIT_USER_ERROR,
                message=f"--note-file not found: {args.note_file}",
                remediation="check the path",
            )
        note_block = "## Skill-specific notes\n\n" + args.note_file.read_text() + "\n"

    upstream_scripts = _upstream_scripts(upstream_scripts_dir)
    brief = _render_brief(
        template_path,
        skill=args.skill,
        upstream_scripts=upstream_scripts,
        changelog_block=changelog_block,
        note_block=note_block,
    )
    title = args.title or f"Resync vendored `{args.skill}` skill from steward (auto-broadcast)"

    if args.dry_run:
        emit_result(f"TITLE: {title}\n")
        emit_result(brief)
        emit_result("--- Would post to: ---")
        emit_result("\n".join(consumers))
        return 0

    post_issue = repo_root / POST_ISSUE_RELPATH
    failures = 0
    for repo in consumers:
        emit_diagnostic(f">>> {repo}")
        # bandit S603: argv is a fixed list; repo / title come from
        # validated argparse input; body is piped on stdin (post-issue.sh
        # supports it via `[[ ! -t 0 ]]`), never expanded by the shell.
        # Stdin avoids the repo-local staging file the earlier
        # implementation used (which polluted the working tree under
        # .local/ and could clobber concurrent runs).
        try:
            completed = subprocess.run(  # noqa: S603
                [str(post_issue), "--repo", repo, "--title", title],
                input=brief,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            # Match doctor.py:172-186 — surface env errors with a
            # remediation hint instead of letting _dispatch wrap as
            # "unexpected".
            raise StewardError(
                code=EXIT_ENV_ERROR,
                message=f"could not execute {post_issue} (consumer {repo}): {exc}",
                remediation="ensure the script exists and is executable (chmod +x)",
            ) from exc
        if completed.stdout:
            sys.stdout.write(completed.stdout)
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        if completed.returncode != 0:
            emit_diagnostic(f"ERROR: post failed for {repo}")
            failures += 1

    emit_diagnostic(
        f"posted: {len(consumers) - failures}/{len(consumers)}"
        + (f"; failures: {failures}" if failures else "")
    )
    return 1 if failures else 0
