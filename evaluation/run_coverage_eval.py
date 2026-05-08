#!/usr/bin/env python3
"""Evaluate coverage-closure recommendations on coverage cases."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.coverage_closure_agent import recommend as structured_recommend  # noqa: E402
from copilot.baselines.raw_log_llm import diagnose_from_raw_log  # noqa: E402
from copilot.json_utils import coerce_string_list  # noqa: E402
from evaluation.metrics import accuracy  # noqa: E402
from scripts.build_all_evidence_packets import iter_case_files, resolve_repo_path  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402

SYSTEMS = ["raw_log", "structured"]


def packet_path_for(case: dict[str, object], packet_root: Path) -> Path:
    return packet_root / str(case["design_id"]) / str(case["case_id"]) / "evidence_packet.json"


def load_or_build_packet(case_path: Path, packet_root: Path) -> dict[str, object]:
    case = json.loads(case_path.read_text())
    packet_path = packet_path_for(case, packet_root)
    if packet_path.exists():
        packet = json.loads(packet_path.read_text())
        if "coverage_evidence" in packet and "vacuity_context" in packet:
            return packet
    return build_packet(case_path=case_path)


def predict(
    system: str,
    packet: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if system == "structured":
        return structured_recommend(packet, use_llm=use_llm, llm_command=llm_command)
    if system == "raw_log":
        diagnosis = diagnose_from_raw_log(packet, use_llm=use_llm, llm_command=llm_command)
        return coverage_from_diagnosis(packet, diagnosis)
    raise ValueError(f"Unknown coverage system: {system}")


def coverage_from_diagnosis(
    packet: dict[str, object],
    diagnosis: dict[str, object],
) -> dict[str, object]:
    issue = str(diagnosis.get("predicted_issue_type", ""))
    if issue == "unreachable_or_invalid_coverage_goal":
        gap_type = "unreachable_or_invalid_coverage_goal"
        action = "prove_unreachable_or_waive_coverage_goal"
    else:
        gap_type = "reachable_coverage_gap"
        action = "add_directed_test_or_sequence"
    coverage = packet.get("coverage_context", {})
    if not isinstance(coverage, dict):
        coverage = {}
    return {
        "case_id": diagnosis.get("case_id", packet.get("case_id", "unknown")),
        "coverage_gap_type": gap_type,
        "recommended_next_action": action,
        "directed_sequence": coverage.get("suggested_sequence", []),
        "evidence": [
            "Mapped from raw-log diagnosis output.",
            *[
                str(item)
                for root in diagnosis.get("root_cause_ranked", [])
                if isinstance(root, dict)
                for item in coerce_string_list(root.get("evidence"))[:2]
            ],
        ],
    }


def evaluate_system(
    system: str,
    case_paths: list[Path],
    packet_root: Path,
    use_llm: bool = False,
    llm_command: str | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = []
    predictions = []
    for case_path in case_paths:
        case = json.loads(case_path.read_text())
        if case.get("task_type") != "coverage_closure":
            continue
        packet = load_or_build_packet(case_path, packet_root)
        prediction = predict(system, packet, use_llm=use_llm, llm_command=llm_command)
        rows.append(
            {
                "system": system,
                "case_id": case.get("case_id"),
                "design_id": case.get("design_id"),
                "coverage_goal": case.get("property_id"),
                "gold_gap_type": case.get("expected_issue_type"),
                "predicted_gap_type": prediction.get("coverage_gap_type"),
                "gold_next_action": case.get("expected_next_action"),
                "predicted_next_action": prediction.get("recommended_next_action"),
                "directed_sequence_len": len(prediction.get("directed_sequence", []))
                if isinstance(prediction.get("directed_sequence"), list)
                else 0,
            }
        )
        predictions.append({"system": system, "case": case, "prediction": prediction})
    return summarize_rows(rows), predictions


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    invalid_rows = [
        row for row in rows if row.get("gold_gap_type") == "unreachable_or_invalid_coverage_goal"
    ]
    wrong_test_suggestions = [
        row
        for row in invalid_rows
        if row.get("predicted_next_action") == "add_directed_test_or_sequence"
    ]
    reachable_rows = [row for row in rows if row.get("gold_gap_type") == "reachable_coverage_gap"]
    sequence_rows = [
        row
        for row in reachable_rows
        if isinstance(row.get("directed_sequence_len"), int) and row["directed_sequence_len"] > 0
    ]
    return {
        "num_cases": len(rows),
        "cases_by_design": dict(sorted(collections.Counter(row["design_id"] for row in rows).items())),
        "gap_type_accuracy": accuracy(rows, "predicted_gap_type", "gold_gap_type"),
        "action_accuracy": accuracy(rows, "predicted_next_action", "gold_next_action"),
        "wrong_test_suggestion_rate": len(wrong_test_suggestions) / len(invalid_rows)
        if invalid_rows
        else 0.0,
        "reachable_sequence_presence_rate": len(sequence_rows) / len(reachable_rows)
        if reachable_rows
        else 0.0,
        "predicted_gap_distribution": dict(
            sorted(collections.Counter(row["predicted_gap_type"] for row in rows).items())
        ),
        "gold_gap_distribution": dict(
            sorted(collections.Counter(row["gold_gap_type"] for row in rows).items())
        ),
        "rows": rows,
    }


def compact_summary(summaries: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    return {
        system: {key: value for key, value in summary.items() if key != "rows"}
        for system, summary in summaries.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        nargs="+",
        type=Path,
        default=[
            Path("benchmarks/arbiter_rr2/cases"),
            Path("benchmarks/rv_buffer/cases"),
            Path("benchmarks/apb_regblock/cases"),
        ],
    )
    parser.add_argument("--packet-root", type=Path, default=Path("jasper/reports/case_packets"))
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=["structured"])
    parser.add_argument("--all-systems", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    case_paths = iter_case_files(args.cases)
    if args.limit is not None:
        case_paths = case_paths[: args.limit]
    packet_root = resolve_repo_path(args.packet_root)
    systems = SYSTEMS if args.all_systems else args.systems
    summaries = {}
    all_predictions = []
    for system in systems:
        summary, predictions = evaluate_system(
            system,
            case_paths,
            packet_root,
            use_llm=args.llm,
            llm_command=args.llm_command,
        )
        summaries[system] = summary
        all_predictions.extend(predictions)

    payload = {
        "num_cases": max((summary["num_cases"] for summary in summaries.values()), default=0),
        "systems": summaries,
        "predictions": all_predictions,
    }
    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"systems": compact_summary(summaries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
