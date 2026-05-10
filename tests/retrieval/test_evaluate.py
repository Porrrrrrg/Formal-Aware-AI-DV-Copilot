from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.models.core import load_core_schema
from app.retrieval.benchmark_registry import build_local_dv_registry
from app.retrieval.evaluate import evaluate_retrieval, write_report
from app.retrieval.vector_index import VectorRetriever


def test_evaluator_reports_metrics_and_failure_taxonomy(tmp_path: Path) -> None:
    registry = build_local_dv_registry()
    payload = evaluate_retrieval(registry, split="test", top_k=5)
    metrics = payload["metrics"]
    assert metrics["correctness"]["query_success_rate"] > 0
    assert set(metrics["failure_buckets"]) == {
        "syntax_error",
        "missing_premise",
        "timeout",
        "solver_fail",
        "schema_drift",
    }
    report_dir = write_report(
        benchmark="local_dv",
        run_id="run_pytest",
        split="test",
        top_k=5,
        registry=registry,
        payload=payload,
        vector_status=VectorRetriever().status().as_dict(),
        out_root=tmp_path,
    )
    assert (report_dir / "summary.md").exists()
    assert (report_dir / "failures.json").exists()
    assert (report_dir / "verifier_outcome.json").exists()

    failures = json.loads((report_dir / "failures.json").read_text(encoding="utf-8"))
    assert failures["canonical_schema"] == "schemas/v1/core.schema.json"
    assert failures["verifier_outcome_ref"] == "verifier_outcome.json"
    assert "schema_drift" in failures["taxonomy"]
    assert "schema_drift" in failures["failure_buckets"]

    outcome = json.loads((report_dir / "verifier_outcome.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(load_core_schema()).evolve(
        schema={"$ref": "#/$defs/VerifierOutcome"}
    ).validate(outcome)
