"""Retrieval benchmark evaluator."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.artifacts import (
    make_attempt_id,
    make_candidate_id,
    make_outcome_id,
    make_problem_id,
    make_run_id as make_core_run_id,
    short_hash,
)
from app.models.core import (
    CORE_SCHEMA_ID,
    RUN_ID_PATTERN,
    Candidate,
    Diagnostic,
    DiagnosticLevel,
    ErrorKind,
    ErrorRecord,
    Language,
    ProblemSpec,
    ToolName,
    VerificationStatus,
    VerifierOutcome,
)
from app.retrieval.benchmark_registry import (
    contamination_evidence,
    load_json,
    load_registry,
    repo_relative,
    resolve_repo_path,
)
from app.retrieval.symbol_index import SymbolIndex, timed_search
from app.retrieval.vector_index import VectorRetriever

FAILURE_BUCKETS = [
    "syntax_error",
    "missing_premise",
    "timeout",
    "solver_fail",
    ErrorKind.SCHEMA_DRIFT.value,
]
_RUN_ID_RE = re.compile(RUN_ID_PATTERN)
ZERO_GIT_SHA = "0" * 12


def make_run_id(prefix: str = "run") -> str:
    now = datetime.now(timezone.utc)
    nonce = None if prefix == "run" else short_hash(f"{prefix}:{now.isoformat()}", 6)
    return make_core_run_id(current_git_sha(), now=now, nonce=nonce)


def current_git_sha() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return ZERO_GIT_SHA
    sha = completed.stdout.strip().lower()
    if re.fullmatch(r"[a-f0-9]{7,64}", sha):
        return sha
    return ZERO_GIT_SHA


def ensure_canonical_run_id(run_id: str) -> str:
    if _RUN_ID_RE.fullmatch(run_id):
        return run_id
    return make_core_run_id(current_git_sha(), nonce=short_hash(run_id, 6))


def item_query(item: dict[str, Any]) -> str:
    case = load_json(item["case_path"])
    parts: list[str] = []
    for field in item.get("query_fields", []):
        value = case.get(field)
        if isinstance(value, list):
            parts.extend(str(part) for part in value)
        elif value is not None:
            parts.append(str(value))
    return "\n".join(parts)


def select_items(registry: dict[str, Any], split: str) -> list[dict[str, Any]]:
    items = list(registry.get("items", []))
    if split == "all":
        return items
    return [item for item in items if item.get("split") == split]


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percent / 100.0) * (len(ordered) - 1))))
    return ordered[index]


def reciprocal_rank(hits: list[dict[str, Any]], gold_doc_ids: set[str]) -> float:
    for idx, hit in enumerate(hits, start=1):
        if hit["doc_id"] in gold_doc_ids:
            return 1.0 / idx
    return 0.0


def classify_failure(
    matched: set[str],
    gold_doc_ids: set[str],
    elapsed_ms: float,
    timeout_ms: float,
    schema_error: str | None = None,
) -> str | None:
    if schema_error:
        return ErrorKind.SCHEMA_DRIFT.value
    if elapsed_ms > timeout_ms:
        return "timeout"
    if gold_doc_ids and not matched:
        return "missing_premise"
    return None


def evaluate_retrieval(
    registry: dict[str, Any],
    split: str = "test",
    top_k: int = 5,
    timeout_ms: float = 1000.0,
) -> dict[str, Any]:
    index = SymbolIndex.from_registry(registry)
    rows = []
    failures = []
    for item in select_items(registry, split):
        schema_error = None
        try:
            query = item_query(item)
            gold_doc_ids = set(str(doc_id) for doc_id in item.get("gold_context_doc_ids", []))
        except (KeyError, TypeError, FileNotFoundError, json.JSONDecodeError) as exc:
            query = ""
            gold_doc_ids = set()
            schema_error = str(exc)
        hits, elapsed_ms = timed_search(
            index,
            query=query,
            top_k=top_k,
            design_id=str(item.get("design_id")) if item.get("design_id") else None,
        )
        hit_dicts = [hit.as_dict() for hit in hits]
        hit_doc_ids = {str(hit["doc_id"]) for hit in hit_dicts}
        matched = hit_doc_ids & gold_doc_ids
        recall = len(matched) / len(gold_doc_ids) if gold_doc_ids else 0.0
        bucket = classify_failure(matched, gold_doc_ids, elapsed_ms, timeout_ms, schema_error)
        row = {
            "item_id": item.get("item_id"),
            "case_id": item.get("case_id"),
            "design_id": item.get("design_id"),
            "split": item.get("split"),
            "top_k": top_k,
            "latency_ms": round(elapsed_ms, 3),
            "gold_doc_count": len(gold_doc_ids),
            "matched_doc_count": len(matched),
            "recall_at_k": round(recall, 6),
            "mrr": round(reciprocal_rank(hit_dicts, gold_doc_ids), 6),
            "matched_doc_ids": sorted(matched),
            "top_hits": hit_dicts,
            "failure_bucket": bucket,
            "schema_error": schema_error,
        }
        rows.append(row)
        if bucket:
            failures.append(
                {
                    "item_id": row["item_id"],
                    "case_id": row["case_id"],
                    "design_id": row["design_id"],
                    "bucket": bucket,
                    "missing_gold_doc_ids": sorted(gold_doc_ids - matched),
                    "top_hit_doc_ids": [hit["doc_id"] for hit in hit_dicts],
                    "schema_error": schema_error,
                    "latency_ms": row["latency_ms"],
                }
            )

    latencies = [float(row["latency_ms"]) for row in rows]
    bucket_counts = {bucket: 0 for bucket in FAILURE_BUCKETS}
    for failure in failures:
        bucket_counts[str(failure["bucket"])] += 1
    correctness = {
        "query_success_rate": (
            sum(1 for row in rows if row["matched_doc_count"] > 0) / len(rows) if rows else 0.0
        ),
        "mean_recall_at_k": statistics.fmean(row["recall_at_k"] for row in rows) if rows else 0.0,
        "mean_mrr": statistics.fmean(row["mrr"] for row in rows) if rows else 0.0,
    }
    total_indexed_bytes = sum(int(doc.get("bytes", 0)) for doc in index.documents.values())
    return {
        "rows": rows,
        "failures": failures,
        "metrics": {
            "correctness": {key: round(value, 6) for key, value in correctness.items()},
            "latency": {
                "avg_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
                "p50_ms": round(percentile(latencies, 50), 3),
                "p95_ms": round(percentile(latencies, 95), 3),
                "timeout_ms": timeout_ms,
            },
            "cost": {
                "external_calls": 0,
                "llm_tokens": 0,
                "estimated_usd": 0.0,
                "indexed_documents": index.document_count,
                "indexed_bytes": total_indexed_bytes,
            },
            "failure_buckets": bucket_counts,
        },
        "index": index,
    }


def summary_markdown(
    benchmark: str,
    run_id: str,
    split: str,
    top_k: int,
    registry: dict[str, Any],
    payload: dict[str, Any],
    vector_status: dict[str, str],
) -> str:
    metrics = payload["metrics"]
    contamination = registry.get("contamination_evidence") or contamination_evidence(
        registry.get("items", []),
        registry.get("documents", []),
    )
    lines = [
        f"# Retrieval Benchmark Summary: {benchmark}",
        "",
        f"- Run ID: `{run_id}`",
        f"- Split: `{split}`",
        f"- Top-k: `{top_k}`",
        f"- Cases: `{len(payload['rows'])}`",
        f"- Vector backend: `{vector_status['status']}` ({vector_status['reason']})",
        "",
        "## Correctness",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in metrics["correctness"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Latency",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    for key, value in metrics["latency"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Cost",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    for key, value in metrics["cost"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Failure Buckets",
            "",
            "| Bucket | Count |",
            "|---|---:|",
        ]
    )
    for bucket, count in metrics["failure_buckets"].items():
        lines.append(f"| `{bucket}` | {count} |")
    lines.extend(
        [
            "",
            "## Contamination Evidence",
            "",
            f"- Official splits modified: `{contamination['official_splits_modified']}`",
            f"- Split policy: `{contamination['split_policy']}`",
            f"- Indexed answer-bearing case files: `{contamination['indexed_case_or_answer_files']}`",
            f"- Test answer fields indexed: `{contamination['test_answer_fields_indexed']}`",
            f"- Training cache policy: {contamination['training_cache_policy']}",
            "",
            "## Notes",
            "",
            "- Retrieval path evaluated: sparse symbolic index.",
            "- A canonical `VerifierOutcome` is written for CI gating; no JasperGold solver",
            "  invocation is performed by the retrieval evaluator.",
            "- Vector retrieval is available only when Qdrant and query-vector configuration are supplied.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(
    benchmark: str,
    run_id: str,
    split: str,
    top_k: int,
    registry: dict[str, Any],
    payload: dict[str, Any],
    vector_status: dict[str, str],
    out_root: Path,
) -> Path:
    run_id = ensure_canonical_run_id(run_id)
    report_dir = resolve_repo_path(out_root) / benchmark / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    problem, candidate, outcome = benchmark_core_artifacts(
        benchmark=benchmark,
        run_id=run_id,
        split=split,
        top_k=top_k,
        payload=payload,
        vector_status=vector_status,
    )
    failures_payload = {
        "schema_version": "v1",
        "canonical_schema": CORE_SCHEMA_ID,
        "run_id": run_id,
        "benchmark": benchmark,
        "split": split,
        "problem_spec_ref": "problem_spec.json",
        "candidate_ref": "candidate.json",
        "verifier_outcome_ref": "verifier_outcome.json",
        "taxonomy": FAILURE_BUCKETS,
        "failure_buckets": payload["metrics"]["failure_buckets"],
        "failures": payload["failures"],
    }
    (report_dir / "failures.json").write_text(json.dumps(failures_payload, indent=2) + "\n")
    metrics_payload = {
        "run_id": run_id,
        "benchmark": benchmark,
        "split": split,
        "metrics": payload["metrics"],
        "rows": payload["rows"],
        "vector_backend": vector_status,
    }
    (report_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2) + "\n")
    (report_dir / "summary.md").write_text(
        summary_markdown(benchmark, run_id, split, top_k, registry, payload, vector_status)
    )
    (report_dir / "problem_spec.json").write_text(
        json.dumps(problem.model_dump(mode="json"), indent=2) + "\n"
    )
    (report_dir / "candidate.json").write_text(
        json.dumps(candidate.model_dump(mode="json"), indent=2) + "\n"
    )
    (report_dir / "verifier_outcome.json").write_text(
        json.dumps(outcome.model_dump(mode="json"), indent=2) + "\n"
    )
    return report_dir


def benchmark_core_artifacts(
    *,
    benchmark: str,
    run_id: str,
    split: str,
    top_k: int,
    payload: dict[str, Any],
    vector_status: dict[str, str],
) -> tuple[ProblemSpec, Candidate, VerifierOutcome]:
    statement = json.dumps(
        {
            "benchmark": benchmark,
            "kind": "retrieval_benchmark",
            "split": split,
            "top_k": top_k,
        },
        sort_keys=True,
    )
    problem_id = make_problem_id(ToolName.Z3, statement)
    attempt_id = make_attempt_id(0)
    candidate_content = json.dumps(
        {
            "case_count": len(payload["rows"]),
            "failure_buckets": payload["metrics"]["failure_buckets"],
            "metrics": payload["metrics"],
            "vector_backend": vector_status,
        },
        sort_keys=True,
    )
    candidate_id = make_candidate_id(attempt_id, "retrieval_benchmark", candidate_content)
    problem = ProblemSpec(
        problem_id=problem_id,
        tool=ToolName.Z3,
        language=Language.SMT2,
        statement=statement,
        metadata={
            "benchmark": benchmark,
            "benchmark_kind": "retrieval",
            "verifier_invoked": False,
        },
    )
    candidate = Candidate(
        candidate_id=candidate_id,
        run_id=run_id,
        problem_id=problem_id,
        attempt_id=attempt_id,
        producer="retrieval_benchmark",
        content=candidate_content,
        content_type="application/json",
        metadata={"split": split, "top_k": top_k},
    )
    failure_buckets = payload["metrics"]["failure_buckets"]
    schema_drift_count = int(failure_buckets.get("schema_drift", 0))
    ok = schema_drift_count == 0
    diagnostics = [
        Diagnostic(
            level=DiagnosticLevel.WARNING,
            message=f"{bucket}: {count}",
            code=bucket,
        )
        for bucket, count in failure_buckets.items()
        if count
    ]
    error = None
    if schema_drift_count:
        message = "Retrieval benchmark report contains schema_drift failures."
        diagnostics.append(
            Diagnostic(level=DiagnosticLevel.ERROR, message=message, code=ErrorKind.SCHEMA_DRIFT.value)
        )
        error = ErrorRecord(kind=ErrorKind.SCHEMA_DRIFT, message=message)
    outcome_payload = json.dumps(
        {
            "candidate_id": candidate_id,
            "failure_buckets": failure_buckets,
            "ok": ok,
            "run_id": run_id,
        },
        sort_keys=True,
    )
    return (
        problem,
        candidate,
        VerifierOutcome(
            outcome_id=make_outcome_id(attempt_id, ToolName.Z3, outcome_payload),
            run_id=run_id,
            problem_id=problem_id,
            candidate_id=candidate_id,
            attempt_id=attempt_id,
            ok=ok,
            status=VerificationStatus.PASSED if ok else VerificationStatus.FAILED,
            tool=ToolName.Z3,
            exit_code=0 if ok else 1,
            stdout_ref="metrics.json",
            stderr_ref="failures.json",
            diagnostics=diagnostics,
            artifact_refs=[
                "metrics.json",
                "failures.json",
                "summary.md",
                "problem_spec.json",
                "candidate.json",
            ],
            error=error,
            metadata={
                "benchmark": benchmark,
                "benchmark_kind": "retrieval",
                "failure_buckets": failure_buckets,
                "split": split,
                "top_k": top_k,
                "verifier_invoked": False,
                "vector_backend": vector_status,
            },
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="local_dv")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--split", choices=["train", "dev", "test", "all"], default="test")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout-ms", type=float, default=1000.0)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out-root", type=Path, default=Path("reports/eval"))
    parser.add_argument("--write-index", action="store_true")
    args = parser.parse_args()

    run_id = args.run_id or make_run_id()
    registry = load_registry(args.benchmark, args.registry)
    payload = evaluate_retrieval(
        registry=registry,
        split=args.split,
        top_k=args.top_k,
        timeout_ms=args.timeout_ms,
    )
    vector_status = VectorRetriever().status().as_dict()
    report_dir = write_report(
        benchmark=args.benchmark,
        run_id=run_id,
        split=args.split,
        top_k=args.top_k,
        registry=registry,
        payload=payload,
        vector_status=vector_status,
        out_root=args.out_root,
    )
    if args.write_index:
        index_path = report_dir / "symbol_index.json"
        payload["index"].save(index_path)
    print(
        json.dumps(
            {
                "benchmark": args.benchmark,
                "run_id": run_id,
                "report_dir": repo_relative(report_dir),
                "metrics": payload["metrics"],
                "vector_backend": vector_status,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
