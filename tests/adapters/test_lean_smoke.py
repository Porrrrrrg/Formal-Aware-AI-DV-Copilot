from __future__ import annotations

from dataclasses import is_dataclass
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from app.core.artifacts import make_attempt_id, make_candidate_id, make_problem_id, make_run_id
from app.core.protocols import VerifierAdapter
from app.models.core import (
    Candidate,
    ErrorKind,
    Language,
    ProblemSpec,
    ToolName,
    VerifierOutcome,
    VerificationStatus,
    load_core_schema,
)
from adapters.lean import LeanAdapter

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = make_run_id(
    "0123456789abcdef",
    now=datetime(2026, 5, 10, 16, 0, 0, tzinfo=timezone.utc),
    nonce="adpt03",
)


def make_problem(content: str) -> ProblemSpec:
    return ProblemSpec(
        problem_id=make_problem_id(ToolName.LEAN, content),
        tool=ToolName.LEAN,
        language=Language.LEAN,
        statement=content,
        metadata={"benchmark": "lean_smt_smoke"},
    )


def make_candidate(problem: ProblemSpec, content: str, attempt_number: int) -> Candidate:
    attempt_id = make_attempt_id(attempt_number)
    return Candidate(
        candidate_id=make_candidate_id(attempt_id, "fixture", content),
        run_id=RUN_ID,
        problem_id=problem.problem_id,
        attempt_id=attempt_id,
        producer="fixture",
        content=content,
    )


def assert_artifact_refs(outcome: VerifierOutcome, artifact_root: Path) -> None:
    assert isinstance(outcome, VerifierOutcome)
    assert not is_dataclass(outcome)
    payload = outcome.model_dump(mode="json")
    assert "manifest_ref" not in payload
    assert "raw_status" not in payload
    assert payload["stdout_ref"]
    assert payload["stderr_ref"]
    assert payload["artifact_refs"]
    assert payload["stdout_ref"] in payload["artifact_refs"]
    assert payload["stderr_ref"] in payload["artifact_refs"]
    assert (artifact_root / payload["stdout_ref"]).is_file()
    assert (artifact_root / payload["stderr_ref"]).is_file()
    jsonschema.Draft202012Validator(load_core_schema()).evolve(
        schema={"$ref": "#/$defs/VerifierOutcome"}
    ).validate(payload)


def assert_diagnostic_shape(outcome: VerifierOutcome) -> None:
    for diagnostic in outcome.model_dump(mode="json")["diagnostics"]:
        assert {"level", "message", "line", "column"}.issubset(diagnostic)
        assert diagnostic["level"] in {"info", "warning", "error"}
        assert isinstance(diagnostic["message"], str)


def test_lean_adapter_implements_verifier_protocol() -> None:
    content = "#check True"
    problem = make_problem(content)
    adapter = LeanAdapter()

    assert isinstance(adapter, VerifierAdapter)
    assert adapter.probe().tool == ToolName.LEAN
    assert adapter.supports(problem)


def test_lean_smoke_compiles_or_blocks_with_structured_diagnostics(tmp_path: Path) -> None:
    content = (ROOT / "benchmarks/lean_smt_smoke/lean/true.lean").read_text(encoding="utf-8")
    artifact_root = tmp_path / "artifacts"
    problem = make_problem(content)
    outcome = LeanAdapter(artifact_root=artifact_root).verify(
        problem,
        make_candidate(problem, content, 1),
    )

    assert outcome.tool == ToolName.LEAN
    assert outcome.status in {
        VerificationStatus.PASSED,
        VerificationStatus.FAILED,
        VerificationStatus.BLOCKED,
        VerificationStatus.TIMEOUT,
        VerificationStatus.ERROR,
    }
    assert_artifact_refs(outcome, artifact_root)
    assert_diagnostic_shape(outcome)
    if outcome.status == VerificationStatus.BLOCKED:
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
    artifact_root = tmp_path / "artifacts"
    problem = make_problem(content)
    outcome = LeanAdapter(artifact_root=artifact_root).verify(
        problem,
        make_candidate(problem, content, 2),
    )

    assert_artifact_refs(outcome, artifact_root)
    assert_diagnostic_shape(outcome)
    if outcome.status != VerificationStatus.BLOCKED:
        assert outcome.status == VerificationStatus.FAILED
        assert outcome.diagnostics


def test_lean_missing_tool_returns_schema_valid_blocked_outcome(tmp_path: Path) -> None:
    content = "#check True"
    artifact_root = tmp_path / "artifacts"
    problem = make_problem(content)
    outcome = LeanAdapter(
        artifact_root=artifact_root,
        lean_executable="lean-definitely-missing-for-protocol-test",
        use_lake=False,
    ).verify(problem, make_candidate(problem, content, 3))

    assert outcome.status == VerificationStatus.BLOCKED
    assert outcome.error is not None
    assert outcome.error.kind == ErrorKind.TOOL_NOT_FOUND
    assert_artifact_refs(outcome, artifact_root)
    assert_diagnostic_shape(outcome)
