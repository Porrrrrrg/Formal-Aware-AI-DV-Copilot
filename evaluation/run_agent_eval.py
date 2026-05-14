#!/usr/bin/env python3
"""Evaluate JasperLoop diagnosis systems on labeled benchmark cases."""

from __future__ import annotations

import argparse
import collections
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.dv_triage_agent import diagnose as structured_diagnose  # noqa: E402
from copilot.baselines.heuristic_baseline import predict as heuristic_predict  # noqa: E402
from copilot.baselines.raw_log_llm import diagnose_from_raw_log  # noqa: E402
from evaluation.metrics import accuracy  # noqa: E402
from evaluation.output_quality import hallucinated_signals, rate, source_summary  # noqa: E402
from scripts.build_all_evidence_packets import iter_case_files, resolve_repo_path  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402

DEFAULT_SYSTEMS = ["structured"]
ALL_SYSTEMS = ["heuristic", "raw_log", "structured"]
ABLATIONS = [
    "no_assertion_manifest",
    "no_assumption_manifest",
    "no_jasper_cex",
    "no_coverage_context",
    "minimal_packet",
]


def packet_path_for(case: dict[str, object], packet_root: Path) -> Path:
    return packet_root / str(case["design_id"]) / str(case["case_id"]) / "evidence_packet.json"


def load_or_build_packet(case_path: Path, packet_root: Path, packet_source: str = "actual") -> dict[str, object]:
    case = json.loads(case_path.read_text())
    packet_path = packet_path_for(case, packet_root)
    if packet_source == "actual" and packet_path.exists():
        return json.loads(packet_path.read_text())
    return build_packet(case_path=case_path)


def predict(
    system: str,
    packet: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if system == "heuristic":
        return heuristic_predict(packet)
    if system == "raw_log":
        return diagnose_from_raw_log(packet, use_llm=use_llm, llm_command=llm_command)
    if system == "structured":
        return structured_diagnose(packet, use_llm=use_llm, llm_command=llm_command)
    if system.startswith("structured:"):
        _, ablation = system.split(":", 1)
        return structured_diagnose(apply_ablation(packet, ablation), use_llm=use_llm, llm_command=llm_command)
    raise ValueError(f"Unknown evaluation system: {system}")


def apply_ablation(packet: dict[str, object], ablation: str) -> dict[str, object]:
    ablated = copy.deepcopy(packet)
    if ablation == "no_assertion_manifest":
        ablated["assertion_intent"] = {}
        failing_property = ablated.get("failing_property")
        if isinstance(failing_property, dict):
            failing_property.pop("intent", None)
    elif ablation == "no_assumption_manifest":
        ablated["active_assumptions"] = []
        ablated["assumption_risks"] = []
    elif ablation == "no_jasper_cex":
        ablated["counterexample_summary"] = {}
        ablated["trace_summaries"] = []
    elif ablation == "no_coverage_context":
        ablated["coverage_context"] = {}
    elif ablation == "minimal_packet":
        ablated = {
            "case_id": packet.get("case_id"),
            "design_id": packet.get("design_id"),
            "variant": packet.get("variant"),
            "task_type": packet.get("task_type"),
            "failing_property": packet.get("failing_property", {}),
            "jasper_result": {
                "summary": packet.get("jasper_result", {}).get("summary", {})
                if isinstance(packet.get("jasper_result"), dict)
                else {}
            },
            "allowed_issue_types": packet.get("allowed_issue_types", []),
            "allowed_next_actions": packet.get("allowed_next_actions", []),
        }
    else:
        raise ValueError(f"Unknown ablation: {ablation}")
    ablated["ablation"] = ablation
    return ablated


def evaluate_system(
    system: str,
    case_paths: list[Path],
    packet_root: Path,
    packet_source: str = "actual",
    use_llm: bool = False,
    llm_command: str | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = []
    predictions = []
    for case_path in case_paths:
        case = json.loads(case_path.read_text())
        packet = load_or_build_packet(case_path, packet_root, packet_source)
        prediction = predict(system, packet, use_llm=use_llm, llm_command=llm_command)
        hallucinated = hallucinated_signals(prediction, packet)
        rows.append(
            {
                "system": system,
                "case_id": case.get("case_id"),
                "design_id": case.get("design_id"),
                "source": prediction.get("source", "unknown"),
                "llm_error": prediction.get("llm_error"),
                "gold_issue_type": case.get("expected_issue_type"),
                "predicted_issue_type": prediction.get("predicted_issue_type"),
                "gold_next_action": case.get("expected_next_action"),
                "predicted_next_action": prediction.get("recommended_next_action"),
                "hallucinated_suspect_signals": hallucinated,
                "has_hallucinated_signal": bool(hallucinated),
            }
        )
        predictions.append({"system": system, "case": case, "prediction": prediction})

    return summarize_rows(rows), predictions


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    summary = {
        "num_cases": len(rows),
        "cases_by_design": dict(sorted(collections.Counter(row["design_id"] for row in rows).items())),
        "issue_type_accuracy": accuracy(rows, "predicted_issue_type", "gold_issue_type"),
        "next_action_accuracy": accuracy(rows, "predicted_next_action", "gold_next_action"),
        "hallucinated_signal_rate": rate(rows, lambda row: bool(row.get("has_hallucinated_signal"))),
        "predicted_issue_distribution": dict(
            sorted(collections.Counter(row["predicted_issue_type"] for row in rows).items())
        ),
        "gold_issue_distribution": dict(
            sorted(collections.Counter(row["gold_issue_type"] for row in rows).items())
        ),
        "rows": rows,
    }
    summary.update(source_summary(rows))
    return summary


def compact_summary(summaries: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    compact = {}
    for system, summary in summaries.items():
        compact[system] = {key: value for key, value in summary.items() if key != "rows"}
    return compact


def resolve_systems(args: argparse.Namespace) -> list[str]:
    systems = list(ALL_SYSTEMS if args.all_systems else args.systems)
    systems.extend(f"structured:{ablation}" for ablation in args.ablations)
    seen = set()
    ordered = []
    for system in systems:
        if system not in seen:
            ordered.append(system)
            seen.add(system)
    return ordered


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
            Path("benchmarks/fifo_1r1w/cases"),
        ],
    )
    parser.add_argument("--packet-root", type=Path, default=Path("jasper/reports/case_packets"))
    parser.add_argument("--packet-source", choices=["actual", "minimal"], default="actual")
    parser.add_argument("--systems", nargs="+", choices=ALL_SYSTEMS, default=DEFAULT_SYSTEMS)
    parser.add_argument("--all-systems", action="store_true")
    parser.add_argument("--ablations", nargs="*", choices=ABLATIONS, default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    packet_root = resolve_repo_path(args.packet_root)
    case_paths = iter_case_files(args.cases)
    if args.limit is not None:
        case_paths = case_paths[: args.limit]
    systems = resolve_systems(args)

    summaries = {}
    all_predictions = []
    for system in systems:
        summary, predictions = evaluate_system(
            system,
            case_paths,
            packet_root,
            packet_source=args.packet_source,
            use_llm=args.llm,
            llm_command=args.llm_command,
        )
        summaries[system] = summary
        all_predictions.extend(predictions)

    payload = {
        "num_cases": len(case_paths),
        "systems": summaries,
        "predictions": all_predictions,
    }

    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"num_cases": len(case_paths), "systems": compact_summary(summaries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
