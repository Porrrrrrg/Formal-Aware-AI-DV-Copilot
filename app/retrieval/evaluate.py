"""Retrieval benchmark evaluator."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.retrieval.benchmark_registry import (
    contamination_evidence,
    load_json,
    load_registry,
    repo_relative,
    resolve_repo_path,
)
from app.retrieval.symbol_index import SymbolIndex, timed_search
from app.retrieval.vector_index import VectorRetriever

FAILURE_BUCKETS = ["syntax_error", "missing_premise", "timeout", "solver_fail", "schema_drift"]


def make_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


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
        return "schema_drift"
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
            "- Verifier outcome aggregation is marked `unspecified` for this retrieval run; no JasperGold",
            "  solver invocation is performed by the retrieval evaluator.",
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
    report_dir = resolve_repo_path(out_root) / benchmark / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    failures_payload = {
        "run_id": run_id,
        "benchmark": benchmark,
        "split": split,
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
    return report_dir


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
