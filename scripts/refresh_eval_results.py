#!/usr/bin/env python3
"""Refresh scaffold evaluation JSON artifacts and markdown result tables."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evaluation" / "results"
DEFAULT_PACKET_ROOT = Path("jasper/reports/case_packets")
CASE_DIRS = [
    Path("benchmarks/arbiter_rr2/cases"),
    Path("benchmarks/rv_buffer/cases"),
    Path("benchmarks/apb_regblock/cases"),
    Path("benchmarks/fifo_1r1w/cases"),
]

ABLATIONS = [
    "no_assertion_manifest",
    "no_assumption_manifest",
    "no_jasper_cex",
    "no_coverage_context",
    "minimal_packet",
]

SYSTEM_LABELS = {
    "heuristic": "Heuristic baseline",
    "raw_log": "Raw-log fallback",
    "structured": "Structured fallback agent",
}

ABLATION_LABELS = {
    "structured": "Full structured packet",
    "structured:no_assertion_manifest": "No assertion manifest",
    "structured:no_assumption_manifest": "No assumption manifest",
    "structured:no_jasper_cex": "No JG CEX",
    "structured:no_coverage_context": "No coverage plan",
    "structured:minimal_packet": "Minimal packet",
}

ABLATION_NOTES = {
    "structured": "Deterministic triage scaffold.",
    "structured:no_assertion_manifest": "Removes assertion intent text from the packet.",
    "structured:no_assumption_manifest": "Removes active assumption and assumption-risk context.",
    "structured:no_jasper_cex": "Removes structured counterexample summaries; current scaffold still relies heavily on manifests.",
    "structured:no_coverage_context": "Removes coverage context, causing coverage cases to collapse into assertion-style diagnoses.",
    "structured:minimal_packet": "Keeps only IDs and Jasper status summary.",
}


def run_summary(cmd: list[str]) -> dict[str, object]:
    result = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def count_case_files() -> int:
    return sum(1 for case_dir in CASE_DIRS for _ in (ROOT / case_dir).glob("*.json"))


def count_actual_packets(packet_root: Path) -> int:
    return sum(1 for _ in packet_root.glob("*/*/evidence_packet.json"))


def packet_has_formal_evidence(packet_path: Path) -> bool:
    try:
        packet = json.loads(packet_path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    jasper_result = packet.get("jasper_result", {})
    if isinstance(jasper_result, dict):
        summary = jasper_result.get("summary", {})
        if isinstance(summary, dict) and summary.get("counts_by_status"):
            return True
        if jasper_result.get("source_report") or jasper_result.get("trace_files"):
            return True
    coverage_evidence = packet.get("coverage_evidence", {})
    return isinstance(coverage_evidence, dict) and bool(coverage_evidence.get("cover_status"))


def count_formal_packets(packet_root: Path) -> int:
    return sum(
        1
        for packet_path in packet_root.glob("*/*/evidence_packet.json")
        if packet_has_formal_evidence(packet_path)
    )


def ensure_actual_packets(packet_root: Path, allow_rebuild_packets: bool) -> None:
    expected = count_case_files()
    actual = count_actual_packets(packet_root)
    formal = count_formal_packets(packet_root)
    if actual >= expected and formal >= expected:
        return
    if actual >= expected:
        sys.stderr.write(
            "Warning: refreshing scaffold result tables with packets that do not all contain "
            f"formal report evidence ({formal}/{expected} formal packets). "
            "Do not cite this refresh as Moore/JasperGold performance.\n"
        )
        return
    if allow_rebuild_packets:
        return
    try:
        packet_root_display = str(packet_root.relative_to(ROOT))
    except ValueError:
        packet_root_display = str(packet_root)
    raise SystemExit(
        "Missing actual evidence packets: "
        f"found {actual} packets and {formal} with formal evidence, expected {expected} "
        f"under {packet_root_display}. "
        "Run this on moore after Jasper packet generation, or pass "
        "--allow-rebuild-packets for a local scaffold refresh."
    )


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return "TBD"
    return str(value)


def source_text(summary: dict[str, object]) -> str:
    counts = summary.get("source_counts", {})
    if not isinstance(counts, dict) or not counts:
        return "unknown"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def output_family_text(summary: dict[str, object]) -> str:
    counts = summary.get("output_family_counts", {})
    if not isinstance(counts, dict) or not counts:
        return "unknown"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def write_main_results(agent_payload: dict[str, object], coverage_payload: dict[str, object]) -> None:
    systems = agent_payload["systems"]
    coverage_systems = coverage_payload["systems"]
    lines = [
        "# Main Results",
        "",
        "| System | Issue Acc. | Action Acc. | Top-3 RCA | Evidence Quality |",
        "| --- | ---: | ---: | ---: | ---: |",
        "| Heuristic | TBD | TBD | TBD | TBD |",
        "| Raw-log LLM | TBD | TBD | TBD | TBD |",
        "| JasperLoop-DV | TBD | TBD | TBD | TBD |",
        "",
        "## Scaffold Sanity Check",
        "",
        "| System | Cases | Issue Acc. | Action Acc. | Hallucinated Signal | Notes |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for system in ["heuristic", "raw_log", "structured"]:
        summary = systems[system]
        note = {
            "heuristic": "Deterministic packet-metadata baseline; validates baseline plumbing, not final LLM performance.",
            "raw_log": "Deterministic raw JasperGold report/trace scaffold, without hosted LLM.",
            "structured": "Deterministic structured scaffold; validates packet/evaluation plumbing, not final LLM performance.",
        }[system]
        lines.append(
            "| "
            + " | ".join(
                [
                    SYSTEM_LABELS[system],
                    fmt(summary["num_cases"]),
                    fmt(summary["issue_type_accuracy"]),
                    fmt(summary["next_action_accuracy"]),
                    fmt(summary.get("hallucinated_signal_rate")),
                    note,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Source/fallback metrics for Codex-backed runs are tracked in `evaluation/results/output_quality_results.md`.",
            "",
            "## Coverage Closure Scaffold",
            "",
            "| System | Cases | Gap Type Acc. | Action Acc. | Wrong Test Suggestion Rate |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for system, label in [("raw_log", "Raw-log fallback"), ("structured", "JasperLoop-DV structured")]:
        summary = coverage_systems[system]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt(summary["num_cases"]),
                    fmt(summary["gap_type_accuracy"]),
                    fmt(summary["action_accuracy"]),
                    fmt(summary["wrong_test_suggestion_rate"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Detailed coverage closure results are tracked in `evaluation/results/coverage_closure_results.md`.",
            "",
        ]
    )
    (RESULTS / "main_results.md").write_text("\n".join(lines))


def write_coverage_results(coverage_payload: dict[str, object]) -> None:
    lines = [
        "# Coverage Closure Results",
        "",
        "| System | Cases | Gap Type Acc. | Action Acc. | Wrong Test Suggestion Rate | Reachable Sequence Rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for system, label in [("raw_log", "Raw-log fallback"), ("structured", "JasperLoop-DV structured")]:
        summary = coverage_payload["systems"][system]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt(summary["num_cases"]),
                    fmt(summary["gap_type_accuracy"]),
                    fmt(summary["action_accuracy"]),
                    fmt(summary["wrong_test_suggestion_rate"]),
                    fmt(summary["reachable_sequence_presence_rate"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "The coverage-only benchmark has 14 cases across arbiter, ready/valid buffer, APB-lite, and FIFO: 9 reachable coverage gaps and 5 invalid or unreachable coverage goals. The raw-log fallback intentionally lacks coverage-plan intent and therefore suggests directed tests for all goals, including illegal or invalid targets. The structured agent receives coverage-plan metadata and available reachability context, so it distinguishes reachable gaps from waiver/prove-unreachable cases in the scaffold evaluation.",
            "",
            "The coverage runner also reports `source_counts`, `llm_success_rate`, `fallback_rate`, and `llm_error_rate`, so Codex-backed coverage experiments can be separated from deterministic fallback behavior.",
            "",
        ]
    )
    (RESULTS / "coverage_closure_results.md").write_text("\n".join(lines))


def write_ablation_results(ablation_payload: dict[str, object]) -> None:
    lines = [
        "# Ablation Results",
        "",
        "| Variant | Issue Acc. | Action Acc. | Proven Final | Notes |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for system, label in ABLATION_LABELS.items():
        summary = ablation_payload["systems"][system]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt(summary["issue_type_accuracy"]),
                    fmt(summary["next_action_accuracy"]),
                    "N/A",
                    ABLATION_NOTES[system],
                ]
            )
            + " |"
        )
    lines.append("| No repair loop | TBD | TBD | TBD | Applies to SVA repair experiments, not current triage scaffold. |")
    lines.append("")
    (RESULTS / "ablation_results.md").write_text("\n".join(lines))


def write_output_quality_results(
    agent_payload: dict[str, object],
    coverage_payload: dict[str, object],
) -> None:
    lines = [
        "# Output Quality Results",
        "",
        "The evaluation runners track output provenance and hallucinated suspect signals. These metrics are intended for Codex-backed runs, where a failed LLM call can fall back to a deterministic path.",
        "",
        "## Triage, Actual Packets",
        "",
        "| System | Cases | Source | LLM Success | Fallback | LLM Error | Hallucinated Signal |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for system, label in [
        ("heuristic", "Heuristic"),
        ("raw_log", "Raw-log fallback"),
        ("structured", "Structured fallback"),
    ]:
        summary = agent_payload["systems"][system]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt(summary["num_cases"]),
                    source_text(summary),
                    fmt(summary["llm_success_rate"]),
                    fmt(summary["fallback_rate"]),
                    fmt(summary["llm_error_rate"]),
                    fmt(summary["hallucinated_signal_rate"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Coverage Closure, Actual Packets",
            "",
            "| System | Cases | Source | LLM Success | Fallback | LLM Error |",
            "| --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for system, label in [("raw_log", "Raw-log fallback"), ("structured", "Structured fallback")]:
        summary = coverage_payload["systems"][system]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt(summary["num_cases"]),
                    source_text(summary),
                    fmt(summary["llm_success_rate"]),
                    fmt(summary["fallback_rate"]),
                    fmt(summary["llm_error_rate"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Codex-backed experiments should report `source_counts`, `llm_success_rate`, `fallback_rate`, `llm_error_rate`, and `hallucinated_signal_rate` alongside accuracy. A healthy Codex run should have high `llm_success_rate`, low `fallback_rate`, and zero hallucinated suspect signals.",
            "",
            "## Output Families",
            "",
            "| Evaluation | Output Families | Caveat |",
            "| --- | --- | --- |",
            "| Triage | "
            + output_family_text(agent_payload["systems"]["structured"])
            + " | Deterministic fallback rows validate plumbing only and must not be cited as hosted LLM performance. |",
            "| Coverage | "
            + output_family_text(coverage_payload["systems"]["structured"])
            + " | Coverage fallback rows are local scaffold behavior unless `source_counts` records real LLM output. |",
            "",
        ]
    )
    (RESULTS / "output_quality_results.md").write_text("\n".join(lines))


def write_design2sva_results_if_present() -> None:
    result_paths = sorted(RESULTS.glob("design2sva_eval*.json"), key=design2sva_result_sort_key)
    if not result_paths:
        return
    lines = [
        "# Design2SVA Results",
        "",
        "These results are generated from the retrieval-assisted Design2SVA scaffold. Rows are separated by artifact and provenance so deterministic scaffold, replay, real LLM, and JasperGold-checked runs are not conflated.",
        "",
        "## Summary",
        "",
        "| Artifact | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | hallucinated_signal_rate | fallback_rate | valid_json_rate | avg_rounds | repair_success | Source | Formal | Root-cause candidates |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    provenance_lines = ["", "## Provenance", ""]
    for result_path in result_paths:
        payload = json.loads(result_path.read_text())
        summary = payload.get("summary", {})
        if not isinstance(summary, dict):
            continue
        mode = str(payload.get("mode", "unknown"))
        source_counts = summary.get("source_counts", {})
        failure_categories = summary.get("failure_categories", {})
        root_cause_candidates = summary.get("root_cause_candidates", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    result_path.name,
                    mode,
                    fmt(summary.get("num_cases")),
                    fmt(summary.get("k")),
                    fmt(summary.get("syntax@1")),
                    fmt(summary.get("syntax@k")),
                    fmt(summary.get("proven@1")),
                    fmt(summary.get("proven@k")),
                    fmt(summary.get("non_vacuous@k")),
                    fmt(summary.get("hallucinated_signal_rate")),
                    fmt(summary.get("fallback_rate")),
                    fmt(summary.get("valid_json_rate")),
                    fmt(summary.get("average_rounds")),
                    fmt(summary.get("repair_success_after_feedback")),
                    source_text({"source_counts": source_counts}),
                    str(summary.get("formal_metrics_status", "unknown")),
                    source_text({"source_counts": root_cause_candidates}),
                ]
            )
            + " |"
        )
        provenance_lines.extend(
            [
                f"### {result_path.name}",
                "",
                f"- Mode: `{mode}`",
                f"- Source counts: {source_text({'source_counts': source_counts})}",
                f"- Failure categories: {source_text({'source_counts': failure_categories})}",
                f"- Root-cause candidates: {source_text({'source_counts': root_cause_candidates})}",
                f"- Formal metrics status: `{summary.get('formal_metrics_status', 'unknown')}`",
                "",
            ]
        )
    lines.extend(
        provenance_lines
        + [
            "## Claim Boundary",
            "",
            "- Dry-run, replay, and deterministic scaffold rows do not measure hosted model quality.",
            "- Real LLM rows measure schema-constrained hosted-model behavior only when `source_counts` records `llm` outputs and fallback is low.",
            "- `proven@*` and `non_vacuous@k` are only meaningful when real JasperGold checks are enabled and available.",
            "- Exact/reference agreement on local fixtures is a scaffold signal, not functional equivalence or production signoff.",
            "",
        ]
    )
    (RESULTS / "design2sva_results.md").write_text("\n".join(lines))


def design2sva_result_sort_key(path: Path) -> tuple[int, str]:
    priority = {
        "design2sva_eval_local.json": 0,
        "design2sva_eval_replay_local.json": 1,
        "design2sva_eval_codex_subset.json": 2,
        "design2sva_eval_codex_jasper_subset.json": 3,
    }
    return (priority.get(path.name, 100), path.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--packet-source", choices=["actual", "minimal"], default="actual")
    parser.add_argument(
        "--allow-rebuild-packets",
        action="store_true",
        help="Allow evaluation runners to build missing packets from case metadata.",
    )
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    packet_root = args.packet_root if args.packet_root.is_absolute() else ROOT / args.packet_root
    if args.packet_source == "actual":
        ensure_actual_packets(packet_root, args.allow_rebuild_packets)
    agent_payload = run_summary(
        [
            sys.executable,
            "evaluation/run_agent_eval.py",
            "--all-systems",
            "--packet-source",
            args.packet_source,
            "--packet-root",
            str(packet_root),
        ]
    )
    ablation_payload = run_summary(
        [
            sys.executable,
            "evaluation/run_agent_eval.py",
            "--systems",
            "structured",
            "--ablations",
            *ABLATIONS,
            "--packet-source",
            args.packet_source,
            "--packet-root",
            str(packet_root),
        ]
    )
    coverage_payload = run_summary(
        [
            sys.executable,
            "evaluation/run_coverage_eval.py",
            "--all-systems",
            "--packet-source",
            args.packet_source,
            "--packet-root",
            str(packet_root),
        ]
    )

    write_main_results(agent_payload, coverage_payload)
    write_coverage_results(coverage_payload)
    write_ablation_results(ablation_payload)
    write_output_quality_results(agent_payload, coverage_payload)
    write_design2sva_results_if_present()
    print(f"Refreshed markdown results in {RESULTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
