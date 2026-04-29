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


def test_write_prescription_report_writes_to_target(tmp_path: Path) -> None:
    target = tmp_path / "out" / "steward-suggestions.md"
    body = "# Steward suggestions\n\n" + f"{_corpus.REPORT_MARKER_PREFIX} on 2026-01-01.\n"
    path = _corpus.write_prescription_report(target, body)
    assert path == target
    assert target.is_file()
    assert target.read_text().startswith("# Steward suggestions")


def test_write_prescription_report_creates_parent_dirs(tmp_path: Path) -> None:
    """The prescription dir tree may not yet exist on first run."""
    target = tmp_path / "deeply" / "nested" / "dir" / "report.md"
    body = "# x\n"
    _corpus.write_prescription_report(target, body)
    assert target.is_file()


def test_write_prescription_report_overwrites_without_complaint(tmp_path: Path) -> None:
    """No 'preserve unmanaged hand-edits' branch — prescriptions are scratch."""
    target = tmp_path / "report.md"
    target.write_text("# stale content\n")
    body = "# fresh content\n"
    _corpus.write_prescription_report(target, body)
    assert target.read_text() == "# fresh content\n"


def test_write_prescription_report_appends_trailing_newline(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    _corpus.write_prescription_report(target, "no-newline")
    assert target.read_text() == "no-newline\n"
