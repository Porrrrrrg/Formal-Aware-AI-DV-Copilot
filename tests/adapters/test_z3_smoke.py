from __future__ import annotations

from pathlib import Path

from adapters.smt.z3 import Z3Adapter
from core.schemas import Candidate, ProblemSpec

ROOT = Path(__file__).resolve().parents[2]


def make_problem(expected: str | None = None) -> ProblemSpec:
    return ProblemSpec(
        problem_id="z3_smoke",
        tool="z3",
        language="smt2",
        statement="",
        metadata={"expect": expected} if expected else {},
    )


def make_candidate(content: str, attempt: str) -> Candidate:
    return Candidate(
        run_id="run_z3_smoke",
        attempt_id=attempt,
        producer="fixture",
        content=content,
    )


def assert_common_shape(outcome) -> None:
    payload = outcome.to_dict()
    assert payload["stdout_ref"]
    assert payload["stderr_ref"]
    assert payload["artifact_refs"]
    assert payload["manifest_ref"]
    for diagnostic in payload["diagnostics"]:
        assert {"level", "message", "line", "column"}.issubset(diagnostic)


def test_z3_sat_smoke_runs_or_blocks(tmp_path: Path) -> None:
    content = (ROOT / "benchmarks/lean_smt_smoke/smt/sat.smt2").read_text(encoding="utf-8")
    outcome = Z3Adapter(artifact_root=tmp_path / "artifacts").verify(
        make_problem("sat"),
        make_candidate(content, "sat"),
    )

    assert outcome.tool == "z3"
    assert outcome.status in {"passed", "failed", "blocked", "skipped"}
    assert_common_shape(outcome)
    if outcome.status == "blocked":
        assert outcome.exit_code == -1
        assert outcome.diagnostics
    else:
        assert outcome.raw_status == "sat"
        assert outcome.ok


def test_z3_syntax_error_returns_structured_diagnostics(tmp_path: Path) -> None:
    content = (ROOT / "benchmarks/lean_smt_smoke/smt/syntax_error.smt2").read_text(
        encoding="utf-8"
    )
    outcome = Z3Adapter(artifact_root=tmp_path / "artifacts").verify(
        make_problem(),
        make_candidate(content, "syntax_error"),
    )

    assert_common_shape(outcome)
    if outcome.status != "blocked":
        assert outcome.status == "failed"
        assert outcome.diagnostics
