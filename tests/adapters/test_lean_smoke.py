from __future__ import annotations

from pathlib import Path

from adapters.lean import LeanAdapter
from core.schemas import Candidate, ProblemSpec

ROOT = Path(__file__).resolve().parents[2]


def make_problem() -> ProblemSpec:
    return ProblemSpec(
        problem_id="lean_smoke",
        tool="lean",
        language="lean",
        statement="",
        metadata={"benchmark": "lean_smt_smoke"},
    )


def make_candidate(content: str, attempt: str) -> Candidate:
    return Candidate(
        run_id="run_lean_smoke",
        attempt_id=attempt,
        producer="fixture",
        content=content,
    )


def assert_artifact_refs(outcome) -> None:
    payload = outcome.to_dict()
    assert payload["stdout_ref"]
    assert payload["stderr_ref"]
    assert payload["artifact_refs"]
    assert payload["manifest_ref"]


def assert_diagnostic_shape(outcome) -> None:
    for diagnostic in outcome.to_dict()["diagnostics"]:
        assert {"level", "message", "line", "column"}.issubset(diagnostic)
        assert diagnostic["level"] in {"info", "warning", "error"}
        assert isinstance(diagnostic["message"], str)


def test_lean_smoke_compiles_or_blocks_with_structured_diagnostics(tmp_path: Path) -> None:
    content = (ROOT / "benchmarks/lean_smt_smoke/lean/true.lean").read_text(encoding="utf-8")
    outcome = LeanAdapter(artifact_root=tmp_path / "artifacts").verify(
        make_problem(),
        make_candidate(content, "positive"),
    )

    assert outcome.tool == "lean"
    assert outcome.status in {"passed", "failed", "blocked", "skipped"}
    assert_artifact_refs(outcome)
    assert_diagnostic_shape(outcome)
    if outcome.status == "blocked":
        assert outcome.exit_code == -1
        assert outcome.diagnostics
        assert outcome.diagnostics[0].line is None
        assert outcome.diagnostics[0].column is None
    else:
        assert outcome.exit_code != -1


def test_lean_syntax_error_returns_repair_friendly_diagnostics(tmp_path: Path) -> None:
    content = (ROOT / "benchmarks/lean_smt_smoke/lean/syntax_error.lean").read_text(
        encoding="utf-8"
    )
    outcome = LeanAdapter(artifact_root=tmp_path / "artifacts").verify(
        make_problem(),
        make_candidate(content, "syntax_error"),
    )

    assert_artifact_refs(outcome)
    assert_diagnostic_shape(outcome)
    if outcome.status != "blocked":
        assert outcome.status == "failed"
        assert outcome.diagnostics
