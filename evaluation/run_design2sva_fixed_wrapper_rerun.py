#!/usr/bin/env python3
"""Stage 13 replay of committed Codex Design2SVA candidates.

This runner intentionally does not call any LLM path. It extracts the committed
candidate JSON from earlier Design2SVA result artifacts and sends those exact
candidate payloads through the current Design2SVA evaluator and Jasper wrapper.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.design2sva_agent import load_replay_records  # noqa: E402
from evaluation.run_design2sva_eval import (  # noqa: E402
    DEFAULT_NATIVE_ORACLE_PATH,
    load_cases,
    load_native_oracle_results,
    render_markdown,
    run_case,
    summarize,
)

DEFAULT_CASES = Path("benchmarks/design2sva_cases.json")
DEFAULT_ORIGINAL_SOURCE = Path(
    "evaluation/fixtures/design2sva_eval_codex_subset_fixture.json"
)
DEFAULT_ANTIVACUITY_SOURCE = DEFAULT_ORIGINAL_SOURCE
DEFAULT_ORIGINAL_OUT = Path(
    "evaluation/results/design2sva_eval_codex_fixed_wrapper_rerun.json"
)
DEFAULT_ANTIVACUITY_OUT = Path(
    "evaluation/results/design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json"
)
DEFAULT_REFERENCE_OUT = Path(
    "evaluation/results/design2sva_eval_reference_oracle_fixed_wrapper_sanity.json"
)
DEFAULT_EXPANDED_SOURCE = DEFAULT_ORIGINAL_SOURCE
DEFAULT_EXPANDED_LOCAL_OUT = Path(
    "evaluation/results/design2sva_codex_replay_expanded_local.json"
)
DEFAULT_EXPANDED_JASPER_OUT = Path(
    "evaluation/results/design2sva_codex_replay_expanded_jasper.json"
)
DEFAULT_JASPER_OUT_ROOT = Path("jasper/reports/design2sva_stage13_fixed_wrapper_rerun")


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_source_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    if not isinstance(summary, dict):
        return {}
    return {key: value for key, value in summary.items() if key != "rows"}


def ordered_case_ids(records: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for record in records:
        case_id = str(record.get("case_id") or "")
        if case_id and case_id not in seen:
            seen.add(case_id)
            ordered.append(case_id)
    return ordered


def select_cases(cases_path: Path, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases_by_id = {str(case["case_id"]): case for case in load_cases(cases_path)}
    selected = []
    for case_id in ordered_case_ids(records):
        if case_id not in cases_by_id:
            raise ValueError(f"Replay source references unknown case_id {case_id!r}")
        selected.append(cases_by_id[case_id])
    return selected


def replay_candidate_keys(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
    keys = set()
    for record in records:
        if not isinstance(record.get("response"), dict):
            continue
        case_id = str(record.get("case_id") or "")
        property_id = str(record.get("property_id") or "")
        if case_id and property_id:
            keys.add((case_id, property_id))
    return keys


def missing_replay_cases(
    cases: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> list[dict[str, str]]:
    available = replay_candidate_keys(records)
    missing = []
    for case in cases:
        key = (str(case["case_id"]), str(case["property_id"]))
        if key not in available:
            missing.append(
                {
                    "case_id": key[0],
                    "property_id": key[1],
                    "design_id": str(case["design_id"]),
                }
            )
    return missing


def require_no_missing_replay_cases(missing: list[dict[str, str]], source_result: Path) -> None:
    if not missing:
        return
    preview = ", ".join(
        f"{item['case_id']}:{item['property_id']}" for item in missing[:10]
    )
    suffix = "" if len(missing) <= 10 else f", ... ({len(missing)} total)"
    raise ValueError(
        "Replay source is missing candidates for expanded Design2SVA case(s): "
        f"{preview}{suffix}. Source: {source_result}. "
        "Provide a future expanded candidate JSONL/JSON artifact or rerun without "
        "--require-expanded-candidates to emit a partial coverage report."
    )


def infer_k(records: list[dict[str, Any]], source_summary: dict[str, Any]) -> int:
    if isinstance(source_summary.get("k"), int):
        return int(source_summary["k"])
    counts: dict[str, int] = {}
    for record in records:
        if int(record.get("round", 0)) != 0:
            continue
        case_id = str(record.get("case_id") or "")
        counts[case_id] = counts.get(case_id, 0) + 1
    return max(counts.values(), default=1)


def infer_max_repair_rounds(records: list[dict[str, Any]]) -> int:
    rounds = []
    for record in records:
        try:
            rounds.append(int(record.get("round", 0)))
        except (TypeError, ValueError):
            rounds.append(0)
    return max(rounds, default=0)


def stage13_payload(
    *,
    mode: str,
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    dry_run: bool,
    source_result: Path | None = None,
    source_summary: dict[str, Any] | None = None,
    native_oracle_results: Path | None = None,
    reference_limit: int | None = None,
    replay_coverage: dict[str, Any] | None = None,
    result_artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    public_summary = {key: value for key, value in summary.items() if key != "rows"}
    payload: dict[str, Any] = {
        "schema_version": "v1",
        "stage": "stage13_fixed_wrapper_rerun",
        "mode": mode,
        "formal_check_mode": "jasper_dry_run" if dry_run else "jasper",
        "llm_prompts_sent": False,
        "summary": public_summary,
        "results": compact_results(results),
        "claim_boundary": {
            "supported": (
                "The repaired wrapper and replay path can fairly rerun prior "
                "committed Codex Design2SVA candidates without sending new prompts."
            ),
            "unsupported_unless_measured": (
                "Broad Design2SVA success and production signoff remain unsupported."
            ),
        },
    }
    if source_result is not None:
        payload["source_result"] = str(source_result)
    if source_summary is not None:
        payload["source_result_summary"] = source_summary
    if native_oracle_results is not None:
        payload["native_oracle_results"] = str(native_oracle_results)
    if reference_limit is not None:
        payload["reference_limit"] = reference_limit
    if replay_coverage is not None:
        payload["replay_coverage"] = replay_coverage
    if result_artifact_paths is not None:
        payload["result_artifact_paths"] = result_artifact_paths
    return payload


def compact_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for result in results:
        paths = []
        for path in result.get("candidate_paths", []):
            if not isinstance(path, dict):
                continue
            rounds = [
                {
                    "candidate": compact_candidate(round_record.get("candidate", {})),
                    "metrics": compact_metrics(round_record.get("metrics", {})),
                }
                for round_record in path.get("rounds", [])
                if isinstance(round_record, dict)
            ]
            paths.append(
                {
                    "candidate_index": path.get("candidate_index"),
                    "rounds": rounds,
                    "final_metrics": compact_metrics(path.get("final_metrics", {})),
                }
            )
        compacted.append(
            {
                "case_id": result.get("case_id"),
                "design_id": result.get("design_id"),
                "property_id": result.get("property_id"),
                "candidate_paths": paths,
                "harness_reachability_audit": compact_harness_audit(
                    result.get("harness_reachability_audit", {})
                ),
            }
        )
    return compacted


def compact_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    keys = [
        "property_id",
        "sva",
        "helper_code",
        "referenced_signals",
        "intent_summary",
        "source",
        "failure_category",
        "feedback",
    ]
    compact = {key: candidate.get(key) for key in keys if key in candidate}
    if isinstance(candidate.get("repair_metadata"), dict):
        compact["repair_metadata"] = {
            key: candidate["repair_metadata"].get(key)
            for key in ["round", "previous_failure_category", "changed_by_repair"]
            if key in candidate["repair_metadata"]
        }
    return compact


def compact_metrics(metrics: Any) -> dict[str, Any]:
    if not isinstance(metrics, dict):
        return {}
    keys = [
        "case_id",
        "design_id",
        "property_id",
        "candidate_index",
        "round",
        "valid_json",
        "validation_error",
        "syntax_ok",
        "exact_match",
        "has_hallucinated_signal",
        "hallucinated_identifiers",
        "reset_clock_mismatch",
        "unsupported_helper_code_issue",
        "source",
        "antecedent_reachable",
        "cover_reachable",
        "syntax_status",
        "proof_status",
        "vacuity_status",
        "report_dir",
        "failure_category",
        "root_cause_candidate",
        "root_cause_detail",
        "wrapper_parity_pass",
    ]
    compact = {key: metrics.get(key) for key in keys if key in metrics}
    compact["proof_metadata"] = compact_proof_metadata(metrics.get("proof_metadata", {}))
    compact["antecedent_metadata"] = compact_antecedent_metadata(
        metrics.get("antecedent_metadata", {})
    )
    compact["clock_reset_metadata"] = metrics.get("clock_reset_metadata", {})
    return compact


def compact_proof_metadata(proof: Any) -> dict[str, Any]:
    if not isinstance(proof, dict):
        return {}
    compact = {
        key: proof.get(key)
        for key in [
            "backend",
            "status",
            "syntax_status",
            "proof_status",
            "vacuity_status",
            "report_dir",
        ]
        if key in proof
    }
    artifact_paths = proof.get("artifact_paths", {})
    if isinstance(artifact_paths, dict):
        compact["artifact_paths"] = {
            key: artifact_paths.get(key)
            for key in [
                "report_dir",
                "generated_properties",
                "generated_harness",
                "candidate_json",
                "properties_report",
                "cover_report",
                "vacuity_report",
                "log",
                "embedding_audit_json",
                "embedding_audit_markdown",
            ]
            if artifact_paths.get(key)
        }
    return compact


def compact_antecedent_metadata(antecedent: Any) -> dict[str, Any]:
    if not isinstance(antecedent, dict):
        return {}
    keys = [
        "extraction_status",
        "reason",
        "antecedent",
        "antecedent_kind",
        "trigger_kind",
        "trigger_status",
        "requires_antecedent_cover",
        "cover_property_id",
        "cover_sva",
        "cover_status",
        "antecedent_reachability",
    ]
    return {key: antecedent.get(key) for key in keys if key in antecedent}


def compact_harness_audit(audit: Any) -> dict[str, Any]:
    if not isinstance(audit, dict):
        return {}
    return {
        key: audit.get(key)
        for key in [
            "case_id",
            "design_id",
            "property_id",
            "reference_available",
            "reference_reset_clock_mismatch",
            "reference_syntax_ok",
            "reference_antecedent_reachable",
            "reference_proven",
            "reference_non_vacuous",
            "harness_reachability_status",
            "cover_property_id",
            "cover_status",
        ]
        if key in audit
    }


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    out = resolve_repo_path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_candidate_source(
    *,
    source_result: Path,
    out: Path,
    cases_path: Path,
    native_oracle_results_path: Path | None,
    jasper_out_root: Path,
    dry_run: bool,
    context_budget: int,
    markdown: Path | None = None,
) -> dict[str, Any]:
    source = resolve_repo_path(source_result)
    replay_records = load_replay_records(source)
    if not replay_records:
        raise ValueError(f"No replayable candidates found in {source_result}")
    source_summary = load_source_summary(source_result)
    k = infer_k(replay_records, source_summary)
    max_repair_rounds = infer_max_repair_rounds(replay_records)
    cases = select_cases(cases_path, replay_records)
    native_oracle = {} if dry_run else load_native_oracle_results(native_oracle_results_path)
    results = [
        run_case(
            case=case,
            k=k,
            max_repair_rounds=max_repair_rounds,
            reference_oracle=False,
            use_llm=False,
            llm_command=None,
            replay_records=replay_records,
            jasper_check=True,
            jasper_dry_run=dry_run,
            jasper_replay_records=None,
            jasper_out_root=resolve_repo_path(jasper_out_root),
            context_budget=context_budget,
            native_oracle=native_oracle.get(str(case["case_id"])),
            run_harness_diagnostics=False,
        )
        for case in cases
    ]
    summary = summarize(
        results,
        k=k,
        jasper_check=True,
        jasper_dry_run=dry_run,
        jasper_replay=False,
    )
    payload = stage13_payload(
        mode="committed_codex_candidate_replay",
        summary=summary,
        results=results,
        dry_run=dry_run,
        source_result=source_result,
        source_summary=source_summary,
        native_oracle_results=native_oracle_results_path,
    )
    write_payload(out, payload)
    if markdown is not None:
        markdown_path = resolve_repo_path(markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(
            render_markdown(summary, mode="stage13_committed_codex_candidate_replay"),
            encoding="utf-8",
        )
    return payload


def run_expanded_candidate_source(
    *,
    source_result: Path,
    out: Path,
    cases_path: Path,
    native_oracle_results_path: Path | None,
    jasper_out_root: Path,
    dry_run: bool,
    context_budget: int,
    require_expanded_candidates: bool,
    markdown: Path | None = None,
) -> dict[str, Any]:
    source = resolve_repo_path(source_result)
    replay_records = load_replay_records(source)
    if not replay_records:
        raise ValueError(f"No replayable candidates found in {source_result}")

    all_cases = load_cases(cases_path)
    missing = missing_replay_cases(all_cases, replay_records)
    require_no_missing_replay_cases(missing, source_result) if require_expanded_candidates else None
    missing_keys = {(item["case_id"], item["property_id"]) for item in missing}
    cases = [
        case
        for case in all_cases
        if (str(case["case_id"]), str(case["property_id"])) not in missing_keys
    ]
    if not cases:
        raise ValueError(
            f"Replay source {source_result} has no candidates for the expanded case set."
        )

    source_summary = load_source_summary(source_result)
    k = infer_k(replay_records, source_summary)
    max_repair_rounds = infer_max_repair_rounds(replay_records)
    native_oracle = {} if dry_run else load_native_oracle_results(native_oracle_results_path)
    results = [
        run_case(
            case=case,
            k=k,
            max_repair_rounds=max_repair_rounds,
            reference_oracle=False,
            use_llm=False,
            llm_command=None,
            replay_records=replay_records,
            jasper_check=True,
            jasper_dry_run=dry_run,
            jasper_replay_records=None,
            jasper_out_root=resolve_repo_path(jasper_out_root),
            context_budget=context_budget,
            native_oracle=native_oracle.get(str(case["case_id"])),
            run_harness_diagnostics=False,
        )
        for case in cases
    ]
    summary = summarize(
        results,
        k=k,
        jasper_check=True,
        jasper_dry_run=dry_run,
        jasper_replay=False,
    )
    replay_coverage = {
        "expanded_case_count": len(all_cases),
        "evaluated_case_count": len(cases),
        "missing_case_count": len(missing),
        "missing_candidates": missing,
        "strict_candidates_required": require_expanded_candidates,
        "fallback_used_for_missing_cases": False,
    }
    payload = stage13_payload(
        mode="committed_codex_expanded_replay",
        summary=summary,
        results=results,
        dry_run=dry_run,
        source_result=source_result,
        source_summary=source_summary,
        native_oracle_results=native_oracle_results_path,
        replay_coverage=replay_coverage,
        result_artifact_paths={
            "local": str(DEFAULT_EXPANDED_LOCAL_OUT),
            "jasper": str(DEFAULT_EXPANDED_JASPER_OUT),
        },
    )
    payload["stage"] = "stage14_expanded_codex_replay"
    write_payload(out, payload)
    if markdown is not None:
        markdown_path = resolve_repo_path(markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(
            render_markdown(summary, mode="stage14_committed_codex_expanded_replay"),
            encoding="utf-8",
        )
    return payload


def run_reference_sanity(
    *,
    out: Path,
    cases_path: Path,
    native_oracle_results_path: Path | None,
    jasper_out_root: Path,
    dry_run: bool,
    context_budget: int,
    reference_limit: int | None,
    markdown: Path | None = None,
) -> dict[str, Any]:
    cases = load_cases(cases_path)
    if reference_limit is not None:
        cases = cases[:reference_limit]
    native_oracle = load_native_oracle_results(native_oracle_results_path)
    results = [
        run_case(
            case=case,
            k=1,
            max_repair_rounds=0,
            reference_oracle=True,
            use_llm=False,
            llm_command=None,
            replay_records=None,
            jasper_check=True,
            jasper_dry_run=dry_run,
            jasper_replay_records=None,
            jasper_out_root=resolve_repo_path(jasper_out_root),
            context_budget=context_budget,
            native_oracle=native_oracle.get(str(case["case_id"])),
            run_harness_diagnostics=False,
        )
        for case in cases
    ]
    summary = summarize(
        results,
        k=1,
        jasper_check=True,
        jasper_dry_run=dry_run,
        jasper_replay=False,
    )
    payload = stage13_payload(
        mode="reference_oracle_fixed_wrapper_sanity",
        summary=summary,
        results=results,
        dry_run=dry_run,
        native_oracle_results=native_oracle_results_path,
        reference_limit=reference_limit,
    )
    write_payload(out, payload)
    if markdown is not None:
        markdown_path = resolve_repo_path(markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(
            render_markdown(summary, mode="stage13_reference_oracle_fixed_wrapper_sanity"),
            encoding="utf-8",
        )
    return payload


def print_summary(name: str, payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    print(
        json.dumps(
            {
                "name": name,
                "formal_metrics_status": summary.get("formal_metrics_status"),
                "proven@k": summary.get("proven@k"),
                "proven_non_vacuous@k": summary.get("proven_non_vacuous@k"),
                "root_cause_detail_counts": summary.get("root_cause_detail_counts"),
            },
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--original-source", type=Path, default=DEFAULT_ORIGINAL_SOURCE)
    parser.add_argument("--antivacuity-source", type=Path, default=DEFAULT_ANTIVACUITY_SOURCE)
    parser.add_argument("--expanded-source", type=Path, default=DEFAULT_EXPANDED_SOURCE)
    parser.add_argument("--original-out", type=Path, default=DEFAULT_ORIGINAL_OUT)
    parser.add_argument("--antivacuity-out", type=Path, default=DEFAULT_ANTIVACUITY_OUT)
    parser.add_argument("--reference-out", type=Path, default=DEFAULT_REFERENCE_OUT)
    parser.add_argument("--expanded-local-out", type=Path, default=DEFAULT_EXPANDED_LOCAL_OUT)
    parser.add_argument("--expanded-jasper-out", type=Path, default=DEFAULT_EXPANDED_JASPER_OUT)
    parser.add_argument(
        "--native-oracle-results",
        nargs="?",
        const=DEFAULT_NATIVE_ORACLE_PATH,
        type=Path,
        default=DEFAULT_NATIVE_ORACLE_PATH,
    )
    parser.add_argument("--jasper-out-root", type=Path, default=DEFAULT_JASPER_OUT_ROOT)
    parser.add_argument("--context-budget", type=int, default=24)
    parser.add_argument("--reference-limit", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--only",
        choices=("all", "original", "antivacuity", "reference", "expanded-local", "expanded-jasper"),
        default="all",
    )
    parser.add_argument(
        "--require-expanded-candidates",
        action="store_true",
        help=(
            "Fail expanded replay if the candidate artifact does not cover every "
            "expanded Design2SVA case. Without this flag, missing cases are reported "
            "separately and are not replaced by fallback candidates."
        ),
    )
    args = parser.parse_args(argv)

    if args.only in {"all", "original"}:
        payload = run_candidate_source(
            source_result=args.original_source,
            out=args.original_out,
            cases_path=args.cases,
            native_oracle_results_path=args.native_oracle_results,
            jasper_out_root=args.jasper_out_root / "codex_original",
            dry_run=args.dry_run,
            context_budget=args.context_budget,
        )
        print_summary("original", payload)

    if args.only in {"all", "antivacuity"}:
        payload = run_candidate_source(
            source_result=args.antivacuity_source,
            out=args.antivacuity_out,
            cases_path=args.cases,
            native_oracle_results_path=args.native_oracle_results,
            jasper_out_root=args.jasper_out_root / "codex_antivacuity",
            dry_run=args.dry_run,
            context_budget=args.context_budget,
        )
        print_summary("antivacuity", payload)

    if args.only in {"all", "reference"}:
        payload = run_reference_sanity(
            out=args.reference_out,
            cases_path=args.cases,
            native_oracle_results_path=args.native_oracle_results,
            jasper_out_root=args.jasper_out_root / "reference_oracle",
            dry_run=args.dry_run,
            context_budget=args.context_budget,
            reference_limit=args.reference_limit,
        )
        print_summary("reference", payload)

    if args.only == "expanded-local":
        payload = run_expanded_candidate_source(
            source_result=args.expanded_source,
            out=args.expanded_local_out,
            cases_path=args.cases,
            native_oracle_results_path=args.native_oracle_results,
            jasper_out_root=args.jasper_out_root / "codex_expanded_local",
            dry_run=True,
            context_budget=args.context_budget,
            require_expanded_candidates=args.require_expanded_candidates,
        )
        print_summary("expanded-local", payload)

    if args.only == "expanded-jasper":
        payload = run_expanded_candidate_source(
            source_result=args.expanded_source,
            out=args.expanded_jasper_out,
            cases_path=args.cases,
            native_oracle_results_path=args.native_oracle_results,
            jasper_out_root=args.jasper_out_root / "codex_expanded_jasper",
            dry_run=args.dry_run,
            context_budget=args.context_budget,
            require_expanded_candidates=args.require_expanded_candidates,
        )
        print_summary("expanded-jasper", payload)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
