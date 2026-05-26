#!/usr/bin/env python3
"""Refresh the final curated evaluation result table."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evaluation" / "results"
DEFAULT_RESULTS = ROOT / "evaluation" / "results"
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

AMBIENT_LLM_ENV_KEYS = ("JASPERLOOP_LLM_CMD",)

DESIGN2SVA_SECTIONS = [
    (
        "Infrastructure Sanity",
        "Local scaffold rows used to validate parsing, schema, and replay plumbing before citing model or JasperGold behavior.",
        [
            "design2sva_eval_local.json",
            "design2sva_eval_replay_local.json",
        ],
    ),
    (
        "Reference/Native Oracle",
        "Reference and native-oracle controls are kept separate from generated-candidate rows so oracle/tooling checks do not overwrite LLM measurements.",
        [
            "design2sva_eval_reference_oracle_local.json",
            "design2sva_eval_reference_oracle_jasper.json",
            "design2sva_eval_reference_oracle_parity_local.json",
            "design2sva_eval_reference_oracle_parity_jasper.json",
            "design2sva_eval_reference_oracle_rootcause_jasper.json",
            "design2sva_native_reference_oracle_jasper.json",
        ],
    ),
    (
        "Expanded oracle validation",
        (
            "Stage 15 expanded native and wrapper reference-oracle controls are rendered "
            "separately from generated-candidate rows. Dry-run, replay, and real "
            "JasperGold outputs must not be collapsed into one result."
        ),
        [
            "design2sva_native_oracle_expanded_local.json",
            "design2sva_native_oracle_expanded_jasper.json",
            "design2sva_reference_oracle_expanded_local.json",
            "design2sva_reference_oracle_expanded_jasper.json",
        ],
    ),
    (
        "Expanded real Codex Design2SVA benchmark",
        (
            "Stage 16 expanded benchmark rows keep the measured reference-oracle gate, "
            "the real Codex LLM-only generation artifact, and the JasperGold-measured "
            "replay of those exact candidates separate from the older Stage 13 "
            "three-case fixed-wrapper reruns."
        ),
        [
            "design2sva_reference_oracle_expanded_jasper.json",
            "design2sva_eval_codex_expanded_subset.json",
            "design2sva_eval_codex_expanded_jasper.json",
        ],
    ),
    (
        "Real LLM Subset",
        "Hosted-model subset rows are separated by whether JasperGold was run, so schema success is not conflated with measured proof quality.",
        [
            "design2sva_eval_codex_subset.json",
            "design2sva_eval_codex_jasper_subset.json",
        ],
    ),
    (
        "JasperGold Fixed-Wrapper Rerun",
        "Fixed-wrapper rows replay committed candidates through the corrected wrapper and report JasperGold-measured outcomes.",
        [
            "design2sva_eval_reference_oracle_fixed_wrapper_sanity.json",
            "design2sva_eval_codex_fixed_wrapper_rerun.json",
            "design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json",
        ],
    ),
    (
        "Expanded Fixtures",
        "Expanded anti-vacuity fixture rows are isolated from the original subset to avoid replacing earlier measurements.",
        [
            "design2sva_eval_anti_vacuity_replay.json",
            "design2sva_eval_anti_vacuity_jasper_subset.json",
            "design2sva_eval_antivacuity_codex_new_subset.json",
            "design2sva_eval_antivacuity_codex_new_jasper_subset.json",
            "design2sva_codex_replay_expanded_local.json",
            "design2sva_codex_replay_expanded_jasper.json",
        ],
    ),
]

DESIGN2SVA_ROW_LABEL_OVERRIDES = {
    "design2sva_reference_oracle_expanded_jasper.json": "expanded reference oracle",
    "design2sva_eval_codex_expanded_subset.json": "expanded real Codex LLM-only",
    "design2sva_eval_codex_expanded_jasper.json": (
        "expanded real Codex JasperGold-measured"
    ),
    "design2sva_ablation_summary.json": "Stage 17 ablation ledger",
}

DESIGN2SVA_ABLATION_PLAN = [
    (
        "No retrieval examples",
        "planned",
        "Isolate how much retrieval context affects valid JSON, syntax, and candidate diversity.",
    ),
    (
        "No JasperGold feedback repair",
        "planned",
        "Disable feedback-guided repair and compare repair_success_after_feedback plus non_vacuous@k.",
    ),
    (
        "No fixed wrapper",
        "planned control",
        "Compare against fixed-wrapper reruns to separate wrapper integration defects from generated SVA quality.",
    ),
    (
        "Reference/native oracle controls",
        "measured controls above",
        "Use oracle rows to bound harness, wrapper, and native-reference failures before attributing errors to the LLM.",
    ),
]


def local_eval_env(*, allow_ambient_llm: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    if not allow_ambient_llm:
        for key in AMBIENT_LLM_ENV_KEYS:
            env.pop(key, None)
    return env


def run_summary(cmd: list[str], *, allow_ambient_llm: bool = False) -> dict[str, object]:
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=local_eval_env(allow_ambient_llm=allow_ambient_llm),
    )
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
            "Do not cite this refresh as JasperGold-backed performance.\n"
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
        "Run this in a configured JasperGold environment after packet generation, or pass "
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


def write_final_results() -> None:
    lines = [
        "# Final Results",
        "",
        "This is the canonical curated result table for the cleaned JasperLoop-DV repository. Raw local Qwen outputs, JasperGold logs, traces, waves, and run artifacts remain local/untracked.",
        "",
        "| Task | Backend | Cases | JSON validity | Fallback | Hallucinated signal | Task metric | Formal status | Boundary |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
        "| SVA repair | Local Qwen/Qwen3-14B-AWQ via `JASPERLOOP_LLM_CMD` | 23 | 1.000 | 0.000 | 0.043 | Exact/repair success 0.913 | Local LLM output mechanics only | Not Codex CLI; not formal proof by itself |",
        "| SVA repair re-check | JasperGold on saved local Qwen final candidates | 23 | n/a | n/a | n/a | 22/23 syntax pass; 22 proven | 0 falsified, 0 undetermined, 0 vacuous | Scoped to project harnesses/properties; not full intent equivalence |",
        "| Failure triage | Local Qwen/Qwen3-14B-AWQ after evidence-cue improvements | 53 | 1.000 | 0.000 | 0.000 | Issue/action accuracy 1.000/1.000 | Not a formal re-check task | Not JasperGold-backed triage validation |",
        "| Coverage closure | Local Qwen/Qwen3-14B-AWQ | 14 | 1.000 | 0.000 | n/a | Gap/action accuracy 1.000/1.000 | Local LLM output mechanics only | Coverage plans still require project-specific review |",
        "",
        "## Interpretation",
        "",
        "- The final triage score reflects a full 53-case local Qwen rerun after the assumption/vacuity and stimulus-vs-coverage evidence improvements.",
        "- The JasperGold-backed result applies only to the saved local Qwen SVA repair final candidates.",
        "- The coverage and triage rows are not JasperGold-backed formal validation.",
        "- These results are not Codex CLI performance, not official FVEval performance, and not production DV signoff.",
        "",
    ]
    (RESULTS / "final_results.md").write_text("\n".join(lines), encoding="utf-8")


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
            "Source/fallback metrics are summarized in `evaluation/results/final_results.md`.",
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
            "Coverage closure results are summarized in `evaluation/results/final_results.md`.",
            "",
        ]
    )
    path = legacy_markdown_path("main_results.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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
    path = legacy_markdown_path("coverage_closure_results.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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
    path = legacy_markdown_path("ablation_results.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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
    path = legacy_markdown_path("output_quality_results.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def fmt_design2sva(value: object) -> str:
    if value is None:
        return "N/A"
    return fmt(value)


def counts_text(counts: object) -> str:
    if not isinstance(counts, dict) or not counts:
        return "unknown"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def design2sva_result_paths() -> list[Path]:
    paths = {path.name: path for path in RESULTS.glob("design2sva*.json")}
    return sorted(paths.values(), key=design2sva_result_sort_key)


def legacy_markdown_path(filename: str) -> Path:
    if RESULTS.resolve() == DEFAULT_RESULTS.resolve():
        return ROOT / "artifacts" / "legacy_results" / filename
    return RESULTS / filename


def design2sva_markdown_path() -> Path:
    return legacy_markdown_path("design2sva_results.md")


def design2sva_source_text(payload: dict[str, object], summary: dict[str, object]) -> str:
    source_counts = summary.get("source_counts")
    if isinstance(source_counts, dict) and source_counts:
        return counts_text(source_counts)
    if payload.get("mode") in {
        "native_reference_oracle",
        "design2sva_native_oracle_expanded",
    }:
        return f"native_reference_oracle={fmt_design2sva(summary.get('num_cases'))}"
    return "unknown"


def design2sva_row_type(payload: dict[str, object], summary: dict[str, object]) -> str:
    mode = str(payload.get("mode", "unknown"))
    source_counts = summary.get("source_counts")
    source_keys = set(source_counts) if isinstance(source_counts, dict) else set()
    if mode == "deterministic_scaffold" or "structured_fallback" in source_keys:
        return "deterministic"
    if mode in {"native_reference_oracle", "design2sva_native_oracle_expanded"}:
        return "native oracle"
    if mode.startswith("reference_oracle") or mode == "design2sva_reference_oracle_expanded":
        return "reference oracle"
    if mode == "real_llm":
        return "real LLM"
    if mode == "committed_codex_candidate_replay":
        return "replay of committed LLM candidates"
    if "replay" in mode or "replay" in source_keys:
        return "replay"
    return mode


def design2sva_formal_text(payload: dict[str, object], summary: dict[str, object]) -> str:
    output_mode = payload.get("output_mode")
    if output_mode:
        return str(output_mode)
    formal_mode = payload.get("formal_check_mode")
    if formal_mode:
        if formal_mode == "jasper":
            return "JasperGold-measured"
        if formal_mode == "replay":
            return "replayed"
        return str(formal_mode)
    status = summary.get("formal_metrics_status")
    if status == "measured":
        return "JasperGold-measured"
    if status:
        return str(status)
    if payload.get("mode") == "native_reference_oracle":
        return "native dry-run" if summary.get("dry_run") else "native JasperGold-measured"
    return "unknown"


def design2sva_signal_text(summary: dict[str, object]) -> str:
    signals = []
    signal_keys = [
        ("failures", "failure_categories"),
        ("root causes", "root_cause_candidate_counts"),
        ("root causes", "root_cause_candidates"),
        ("root details", "root_cause_detail_counts"),
        ("backend", "backend_status_counts"),
        ("harness", "harness_reachability_status_counts"),
        ("native failures", "native_failures_by_design"),
        ("native proof", "native_proof_status_counts"),
        ("native vacuity", "native_vacuity_status_counts"),
    ]
    seen_labels = set()
    for label, key in signal_keys:
        counts = summary.get(key)
        if label in seen_labels or not isinstance(counts, dict) or not counts:
            continue
        signals.append(f"{label}: {counts_text(counts)}")
        seen_labels.add(label)
    if not signals:
        return "none"
    return "; ".join(signals)


def design2sva_table_header() -> list[str]:
    return [
        "| Artifact | Row type | Mode | Cases | k | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | valid_json | fallback | Source | Formal check | Signal |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]


def summary_first(summary: dict[str, object], *keys: str) -> object:
    for key in keys:
        if key in summary:
            return summary.get(key)
    return None


def design2sva_row(result_path: Path, payload: dict[str, object], summary: dict[str, object]) -> str:
    mode = str(payload.get("mode", "unknown"))
    row_type = DESIGN2SVA_ROW_LABEL_OVERRIDES.get(
        result_path.name,
        design2sva_row_type(payload, summary),
    )
    return (
        "| "
        + " | ".join(
            [
                result_path.name,
                row_type,
                mode,
                fmt_design2sva(summary.get("num_cases")),
                fmt_design2sva(summary.get("k")),
                fmt_design2sva(summary.get("syntax@1")),
                fmt_design2sva(summary.get("syntax@k")),
                fmt_design2sva(
                    summary_first(
                        summary,
                        "proven@1",
                        "reference_proven@1",
                        "native_reference_proven_rate",
                    )
                ),
                fmt_design2sva(
                    summary_first(
                        summary,
                        "proven@k",
                        "reference_proven@1",
                        "native_reference_proven_rate",
                    )
                ),
                fmt_design2sva(
                    summary_first(
                        summary,
                        "non_vacuous@k",
                        "reference_non_vacuous@1",
                        "native_reference_non_vacuous_rate",
                    )
                ),
                fmt_design2sva(summary.get("valid_json_rate")),
                fmt_design2sva(summary.get("fallback_rate")),
                design2sva_source_text(payload, summary),
                design2sva_formal_text(payload, summary),
                design2sva_signal_text(summary),
            ]
        )
        + " |"
    )


def append_design2sva_section(
    lines: list[str],
    title: str,
    description: str,
    artifact_names: list[str],
    records: dict[str, tuple[Path, dict[str, object], dict[str, object]]],
) -> set[str]:
    lines.extend(["", f"## {title}", "", description, ""])
    lines.extend(design2sva_table_header())
    written = set()
    for artifact_name in artifact_names:
        record = records.get(artifact_name)
        if not record:
            continue
        result_path, payload, summary = record
        lines.append(design2sva_row(result_path, payload, summary))
        written.add(artifact_name)
    if not written:
        lines.append("| No artifact present | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | none |")
    return written


def write_design2sva_results_if_present() -> None:
    result_paths = design2sva_result_paths()
    if not result_paths:
        return
    records: dict[str, tuple[Path, dict[str, object], dict[str, object]]] = {}
    for result_path in result_paths:
        payload = json.loads(result_path.read_text())
        summary = payload.get("summary", {})
        if not isinstance(summary, dict):
            continue
        records[result_path.name] = (result_path, payload, summary)
    lines = [
        "# Design2SVA Results",
        "",
        "These results are generated from the retrieval-assisted Design2SVA scaffold. Rows are separated by artifact, provenance, and formal-check status so deterministic, replay, real LLM, and JasperGold-measured outcomes are not conflated.",
        "",
        "## Canonical Result Links",
        "",
        "- Final curated result table: [evaluation/results/final_results.md](final_results.md)",
        "- Final research summary: [docs/reports/final_research_summary.md](../../docs/reports/final_research_summary.md)",
        "- Experiment history: [docs/reports/experiment_history.md](../../docs/reports/experiment_history.md)",
    ]
    written: set[str] = set()
    for title, description, artifact_names in DESIGN2SVA_SECTIONS:
        written.update(
            append_design2sva_section(lines, title, description, artifact_names, records)
        )
    ablation_artifacts = [
        name
        for name in sorted(records, key=lambda name: design2sva_result_sort_key(Path(name)))
        if "ablation" in name
    ]
    lines.extend(
        [
            "",
            "## Stage 17 Ablation Summary",
            "",
            "Design2SVA ablation artifacts are rendered here when present. Stage 17 rows are built from existing committed artifacts only; placeholder rows reserve non-overlapping reporting slots for explicitly gated follow-up runs.",
            "",
        ]
    )
    if ablation_artifacts:
        lines.extend(design2sva_table_header())
        for artifact_name in ablation_artifacts:
            result_path, payload, summary = records[artifact_name]
            lines.append(design2sva_row(result_path, payload, summary))
            written.add(artifact_name)
        lines.append("")
    lines.extend(
        [
            "| Variant | Status | Isolation target |",
            "| --- | --- | --- |",
        ]
    )
    for variant, status, isolation_target in DESIGN2SVA_ABLATION_PLAN:
        lines.append(f"| {variant} | {status} | {isolation_target} |")
    unwritten = [
        name
        for name in sorted(records, key=lambda name: design2sva_result_sort_key(Path(name)))
        if name not in written and "ablation" not in name
    ]
    if unwritten:
        lines.extend(
            [
                "",
                "## Additional Artifacts",
                "",
                "These Design2SVA artifacts did not match a named reporting section and are listed to avoid silent omission.",
                "",
            ]
        )
        lines.extend(design2sva_table_header())
        for artifact_name in unwritten:
            result_path, payload, summary = records[artifact_name]
            lines.append(design2sva_row(result_path, payload, summary))
    lines.extend(
        [
            "",
            "## Claim Boundaries",
            "",
            "- Dry-run, replay, and deterministic scaffold rows do not measure hosted model quality.",
            "- Real LLM rows measure schema-constrained hosted-model behavior only when `source_counts` records `llm` outputs and fallback is low.",
            "- JasperGold-measured rows are the only rows where `proven@*` and `non_vacuous@k` should be cited as formal outcomes.",
            "- Reference and native-oracle rows are infrastructure controls; exact/reference agreement on fixtures is not production signoff.",
            "- Fixed-wrapper reruns isolate wrapper correctness from candidate generation quality.",
            "- If expanded references prove non-vacuously with high native/wrapper parity, the expanded fixtures are valid for LLM evaluation.",
            "- If expanded references fail, do not run the expanded LLM benchmark yet; repair the fixture, harness, or wrapper first.",
            "",
        ]
    )
    markdown_path = design2sva_markdown_path()
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def design2sva_result_sort_key(path: Path) -> tuple[int, str]:
    priority = {
        "design2sva_eval_local.json": 0,
        "design2sva_eval_replay_local.json": 1,
        "design2sva_eval_reference_oracle_local.json": 10,
        "design2sva_eval_reference_oracle_jasper.json": 11,
        "design2sva_eval_reference_oracle_parity_local.json": 12,
        "design2sva_eval_reference_oracle_parity_jasper.json": 13,
        "design2sva_eval_reference_oracle_rootcause_jasper.json": 14,
        "design2sva_native_reference_oracle_jasper.json": 15,
        "design2sva_native_oracle_expanded_local.json": 16,
        "design2sva_native_oracle_expanded_jasper.json": 17,
        "design2sva_reference_oracle_expanded_local.json": 18,
        "design2sva_reference_oracle_expanded_jasper.json": 19,
        "design2sva_eval_codex_subset.json": 20,
        "design2sva_eval_codex_jasper_subset.json": 21,
        "design2sva_eval_codex_expanded_subset.json": 22,
        "design2sva_eval_codex_expanded_jasper.json": 23,
        "design2sva_eval_reference_oracle_fixed_wrapper_sanity.json": 30,
        "design2sva_eval_codex_fixed_wrapper_rerun.json": 31,
        "design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json": 32,
        "design2sva_eval_anti_vacuity_replay.json": 40,
        "design2sva_eval_anti_vacuity_jasper_subset.json": 41,
        "design2sva_eval_antivacuity_codex_new_subset.json": 42,
        "design2sva_eval_antivacuity_codex_new_jasper_subset.json": 43,
        "design2sva_codex_replay_expanded_local.json": 44,
        "design2sva_codex_replay_expanded_jasper.json": 45,
        "design2sva_ablation_summary.json": 50,
        "design2sva_ablation_replay_local.json": 51,
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
    parser.add_argument(
        "--allow-ambient-llm",
        action="store_true",
        help=(
            "Preserve ambient LLM configuration such as JASPERLOOP_LLM_CMD for "
            "downstream eval runners. Default refreshes scrub it and stay local."
        ),
    )
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    packet_root = args.packet_root if args.packet_root.is_absolute() else ROOT / args.packet_root
    if args.packet_source == "actual":
        ensure_actual_packets(packet_root, args.allow_rebuild_packets)
    write_final_results()
    print(f"Refreshed {Path('evaluation/results/final_results.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
