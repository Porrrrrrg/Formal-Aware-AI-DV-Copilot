from __future__ import annotations

from pathlib import Path

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

