"""Unit tests for the corpus helpers under
``steward.cli._commands._corpus``.

End-to-end behaviour is covered by ``test_cli_doctor_siblings.py``;
this file isolates the discover/synthesize/score/write pieces so a
regression in one stage points to a single function.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from steward.cli._commands import _corpus


def _make_repo(
    workspace: Path, name: str, agents: list[dict], skills: list[str] | None = None
) -> Path:
    repo = workspace / name
    repo.mkdir()
    (repo / "culture.yaml").write_text(yaml.safe_dump({"agents": agents}))
    if skills:
        skills_root = repo / ".claude" / "skills"
        for s in skills:
            (skills_root / s / "scripts").mkdir(parents=True)
            (skills_root / s / "SKILL.md").write_text(f"---\nname: {s}\ndescription: x\n---\n")
    return repo


def test_discover_agents_finds_one_per_yaml_row(tmp_path: Path) -> None:
    _make_repo(tmp_path, "alpha", [{"suffix": "a", "backend": "claude"}])
    _make_repo(
        tmp_path,
        "beta",
        [
            {"suffix": "b", "backend": "claude"},
            {"suffix": "c", "backend": "acp", "model": "x"},
        ],
    )

    agents, errors = _corpus.discover_agents(tmp_path)
    suffixes = sorted(a.suffix for a in agents)
    assert suffixes == ["a", "b", "c"]
    assert errors == []


def test_discover_agents_skips_named_repos(tmp_path: Path) -> None:
    _make_repo(tmp_path, "alpha", [{"suffix": "a", "backend": "claude"}])
    _make_repo(tmp_path, "skipme", [{"suffix": "s", "backend": "claude"}])

    agents, _errors = _corpus.discover_agents(tmp_path, skip_repos={"skipme"})
    assert [a.suffix for a in agents] == ["a"]


def test_discover_agents_handles_flat_root_shape(tmp_path: Path) -> None:
    """Single-agent repos use root-level ``suffix:``/``backend:`` instead of an
    ``agents:`` list (e.g. agex, shushu, reachy_nova). Discovery must accept
    both shapes."""
    repo = tmp_path / "shushu"
    repo.mkdir()
    (repo / "culture.yaml").write_text(yaml.safe_dump({"suffix": "shushu", "backend": "claude"}))
    agents, _errors = _corpus.discover_agents(tmp_path)
    assert len(agents) == 1
    assert agents[0].suffix == "shushu"
    assert agents[0].backend == "claude"


def test_discover_agents_skips_nested_manifests(tmp_path: Path) -> None:
    """Sibling-only walk: nested culture.yaml under packages/ is ignored."""
    _make_repo(tmp_path, "alpha", [{"suffix": "a", "backend": "claude"}])
    nested = tmp_path / "alpha" / "packages" / "x"
    nested.mkdir(parents=True)
    (nested / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"suffix": "nested", "backend": "claude"}]})
    )
    agents, _errors = _corpus.discover_agents(tmp_path)
    assert [a.suffix for a in agents] == ["a"]


def test_discover_agents_surfaces_yaml_parse_error(tmp_path: Path) -> None:
    """A malformed culture.yaml must surface as a ManifestError, not vanish."""
    repo = tmp_path / "broken"
    repo.mkdir()
    (repo / "culture.yaml").write_text("agents:\n  - suffix: a\n bad indent\n")
    agents, errors = _corpus.discover_agents(tmp_path)
    assert agents == []
    assert len(errors) == 1
    assert errors[0].repo_name == "broken"
    assert "could not parse" in errors[0].message.lower()


def test_discover_agents_normalizes_null_backend(tmp_path: Path) -> None:
    """Explicit YAML ``null`` backend becomes ``""``, not the string ``"None"``."""
    repo = tmp_path / "alpha"
    repo.mkdir()
    (repo / "culture.yaml").write_text("suffix: a\nbackend:\n")
    agents, _errors = _corpus.discover_agents(tmp_path)
    assert len(agents) == 1
    assert agents[0].backend == ""


def test_synthesize_baseline_classifies_by_frequency(tmp_path: Path) -> None:
    """A field present in 4/5 agents is required; 1/5 is rare (excluded)."""
    # 4 of 5 carry `model`; 1 of 5 carries `tags`.
    rows = [{"suffix": f"a{i}", "backend": "claude", "model": "x"} for i in range(4)] + [
        {"suffix": "rare", "backend": "claude", "tags": ["x"]}
    ]
    _make_repo(tmp_path, "r", rows)
    agents, _errors = _corpus.discover_agents(tmp_path)

    baseline = _corpus.synthesize_baseline(agents)
    # suffix and backend in 5/5 → required.
    assert "suffix" in baseline.required_yaml_keys
    assert "backend" in baseline.required_yaml_keys
    # model in 4/5 = 0.8 → required threshold.
    assert "model" in baseline.required_yaml_keys
    # tags in 1/5 = 0.2 → rare, neither required nor recommended.
    assert "tags" not in baseline.required_yaml_keys
    assert "tags" not in baseline.recommended_yaml_keys


def test_synthesize_baseline_handles_empty_corpus() -> None:
    baseline = _corpus.synthesize_baseline([])
    assert baseline.agent_count == 0
    assert baseline.required_yaml_keys == set()


def test_synthesize_baseline_promotes_curated_skills(tmp_path: Path) -> None:
    """Skills listed in ``PROMOTED_SKILLS`` show up under recommended even
    when the corpus frequency is below the 30% threshold (here: 0%)."""
    _make_repo(tmp_path, "alpha", [{"suffix": "a", "backend": "claude"}])
    agents, _errors = _corpus.discover_agents(tmp_path)
    baseline = _corpus.synthesize_baseline(agents)

    assert _corpus.PROMOTED_SKILLS, "promoted-skills set must not be empty"
    for name, default_desc in _corpus.PROMOTED_SKILLS.items():
        assert (
            name in baseline.recommended_skills
        ), f"{name!r} should be promoted into recommended_skills"
        # Default description is used when the corpus has nothing better.
        assert baseline.skill_descriptions[name] == default_desc


def test_score_against_baseline_flags_missing_promoted_skill(tmp_path: Path) -> None:
    """A repo missing a promoted skill (e.g. ``coordinate``) gets an
    info-severity finding from ``score_agent_against_baseline``. Without
    this, ``PROMOTED_SKILLS`` would only update perfect-patient.md and
    never raise the actual scoring bar."""
    promoted = next(iter(_corpus.PROMOTED_SKILLS))
    _make_repo(tmp_path, "alpha", [{"suffix": "a", "backend": "claude"}], skills=[])
    agents, _errors = _corpus.discover_agents(tmp_path)
    baseline = _corpus.synthesize_baseline(agents)
    findings = _corpus.score_agent_against_baseline(agents[0], baseline)
    matching = [f for f in findings if promoted in f.message]
    assert matching, f"expected a finding for missing promoted skill {promoted!r}"
    assert matching[0].severity == "info"


def test_synthesize_baseline_corpus_description_wins_over_promoted(tmp_path: Path) -> None:
    """If the corpus already has a description for a promoted skill, the
    corpus copy wins (so a downstream's own SKILL.md text is preserved)."""
    promoted = next(iter(_corpus.PROMOTED_SKILLS))
    _make_repo(
        tmp_path,
        "alpha",
        [{"suffix": "a", "backend": "claude"}],
        skills=[promoted],
    )
    agents, _errors = _corpus.discover_agents(tmp_path)
    baseline = _corpus.synthesize_baseline(agents)
    # _make_repo wrote `description: x` into the SKILL.md; that beats the
    # PROMOTED_SKILLS default.
    assert baseline.skill_descriptions[promoted] == "x"


def test_score_culture_yaml_shape_flags_missing_required(tmp_path: Path) -> None:
    _make_repo(
        tmp_path,
        "alpha",
        [
            {"suffix": "a", "backend": "claude", "model": "x"},
            {"suffix": "b", "backend": "claude", "model": "y"},
            {"suffix": "c", "backend": "claude"},  # missing `model`
        ],
    )
    agents, _errors = _corpus.discover_agents(tmp_path)
    baseline = _corpus.synthesize_baseline(agents)
    # model in 2/3 = 0.67 → recommended (between 0.30 and 0.80).
    assert "model" in baseline.recommended_yaml_keys

    # Score the agent missing `model` against the baseline.
    target = next(a for a in agents if a.suffix == "c")
    findings = _corpus.score_culture_yaml_shape(target, baseline)
    messages = [f.message for f in findings]
    assert any("missing recommended field `model`" in m for m in messages)


def test_score_against_baseline_flags_missing_skills(tmp_path: Path) -> None:
    """4/5 repos carry `common-skill`; the 1 that doesn't gets flagged."""
    _make_repo(
        tmp_path,
        "alpha",
        [{"suffix": "a", "backend": "claude"}],
        skills=["common-skill"],
    )
    _make_repo(
        tmp_path,
        "beta",
        [{"suffix": "b", "backend": "claude"}],
        skills=["common-skill"],
    )
    _make_repo(
        tmp_path,
        "gamma",
        [{"suffix": "c", "backend": "claude"}],
        skills=[],  # missing the common skill — the agent we'll score
    )
    _make_repo(
        tmp_path,
        "delta",
        [{"suffix": "d", "backend": "claude"}],
        skills=["common-skill"],
    )
    _make_repo(
        tmp_path,
        "epsilon",
        [{"suffix": "e", "backend": "claude"}],
        skills=["common-skill"],
    )
    agents, _errors = _corpus.discover_agents(tmp_path)
    baseline = _corpus.synthesize_baseline(agents)
    # common-skill in 4/5 repos = 0.80 → required threshold.
    assert "common-skill" in baseline.required_skills

    target = next(a for a in agents if a.suffix == "c")
    findings = _corpus.score_agent_against_baseline(target, baseline)
    messages = [f.message for f in findings]
    assert any("missing baseline skill `common-skill`" in m for m in messages)


def test_render_perfect_patient_has_expected_sections(tmp_path: Path) -> None:
    _make_repo(tmp_path, "alpha", [{"suffix": "a", "backend": "claude"}])
    agents, _errors = _corpus.discover_agents(tmp_path)
    body = _corpus.render_perfect_patient(_corpus.synthesize_baseline(agents))

    assert "# Perfect patient" in body
    assert "Required `culture.yaml` fields" in body
    assert "Common skills baseline" in body
    assert "## GitHub message signing" in body
    assert "`- <nick> (Claude)`" in body
    assert "Corpus stats" in body


def test_skill_bullets_carry_frontmatter_descriptions(tmp_path: Path) -> None:
    """Skills in the rendered baseline get a one-liner pulled from
    their SKILL.md frontmatter `description:`. First-encountered repo
    wins so the output is stable across runs."""
    repo = tmp_path / "alpha"
    repo.mkdir()
    (repo / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"suffix": "a", "backend": "claude"}]})
    )
    (repo / ".claude" / "skills" / "run-tests" / "scripts").mkdir(parents=True)
    (repo / ".claude" / "skills" / "run-tests" / "SKILL.md").write_text(
        "---\nname: run-tests\n"
        "description: Run pytest with parallel execution and coverage. "
        "Use when running tests.\n---\n"
    )
    (repo / ".claude" / "skills" / "no-meta" / "scripts").mkdir(parents=True)
    (repo / ".claude" / "skills" / "no-meta" / "SKILL.md").write_text("# no frontmatter\n")

    agents, _errors = _corpus.discover_agents(tmp_path)
    baseline = _corpus.synthesize_baseline(agents)
    # 1-of-1 repo carries each skill, so both are required.
    assert {"run-tests", "no-meta"} <= baseline.required_skills
    # Description is collected for the skill that has frontmatter and trimmed
    # to the first sentence (the trailing "Use when..." is dropped).
    assert baseline.skill_descriptions["run-tests"].startswith(
        "Run pytest with parallel execution and coverage."
    )
    assert "Use when" not in baseline.skill_descriptions["run-tests"]
    # Skills without a parseable description are absent from the dict, not
    # mapped to an empty string — render falls back to a bare bullet.
    assert "no-meta" not in baseline.skill_descriptions

    body = _corpus.render_perfect_patient(baseline)
    assert "- `run-tests` — Run pytest with parallel execution and coverage." in body
    assert "- `no-meta`\n" in body


def test_write_repo_report_writes_marked_file(tmp_path: Path) -> None:
    repo = tmp_path / "alpha"
    repo.mkdir()
    body = "# Steward suggestions\n\n" + f"{_corpus.REPORT_MARKER_PREFIX} on 2026-01-01.\n"
    path, status = _corpus.write_repo_report(repo, body)
    assert status == "written"
    assert path == repo / _corpus.REPORT_RELPATH
    assert path.read_text().startswith("# Steward suggestions")


def test_write_repo_report_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "alpha"
    repo.mkdir()
    body = "# Steward suggestions\n\n" + f"{_corpus.REPORT_MARKER_PREFIX} on 2026-01-01.\n"
    _corpus.write_repo_report(repo, body)
    path, status = _corpus.write_repo_report(repo, body)
    assert status == "written"
    assert path.read_text().count("# Steward suggestions") == 1


def test_write_repo_report_finds_marker_below_first_5_lines(tmp_path: Path) -> None:
    """The marker scan covers the entire file — extra header lines (editor
    banner, frontmatter, etc.) above the marker must NOT trigger the
    skipped-unmanaged path."""
    repo = tmp_path / "alpha"
    target_dir = repo / "docs" / "steward"
    target_dir.mkdir(parents=True)
    target = target_dir / "steward-suggestions.md"
    target.write_text(
        "# Steward suggestions\n\n"
        "<!-- editor banner line 1 -->\n"
        "<!-- editor banner line 2 -->\n"
        "<!-- editor banner line 3 -->\n"
        "<!-- editor banner line 4 -->\n"
        f"{_corpus.REPORT_MARKER_PREFIX} on 2026-01-01.\n"
    )
    body = "# Steward suggestions\n\n" + f"{_corpus.REPORT_MARKER_PREFIX} on 2026-01-02.\n"
    _path, status = _corpus.write_repo_report(repo, body)
    assert status == "written"


def test_write_repo_report_preserves_unmanaged_file(tmp_path: Path) -> None:
    repo = tmp_path / "alpha"
    target_dir = repo / "docs" / "steward"
    target_dir.mkdir(parents=True)
    target = target_dir / "steward-suggestions.md"
    target.write_text("# Hand-written notes\n\nDon't overwrite me.\n")

    body = "# Steward suggestions\n\n" + f"{_corpus.REPORT_MARKER_PREFIX} on 2026-01-01.\n"
    path, status = _corpus.write_repo_report(repo, body)
    assert status == "skipped-unmanaged"
    assert "Hand-written notes" in path.read_text()
