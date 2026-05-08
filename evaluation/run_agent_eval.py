#!/usr/bin/env python3
"""Evaluate JasperLoop agents on labeled benchmark cases."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.dv_triage_agent import diagnose  # noqa: E402
from evaluation.metrics import accuracy  # noqa: E402
from scripts.build_all_evidence_packets import iter_case_files, resolve_repo_path  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402


def packet_path_for(case: dict[str, object], packet_root: Path) -> Path:
    return packet_root / str(case["design_id"]) / str(case["case_id"]) / "evidence_packet.json"


def load_or_build_packet(case_path: Path, packet_root: Path) -> dict[str, object]:
    case = json.loads(case_path.read_text())
    packet_path = packet_path_for(case, packet_root)
    if packet_path.exists():
        return json.loads(packet_path.read_text())
    return build_packet(case_path=case_path)


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
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    packet_root = resolve_repo_path(args.packet_root)
    rows = []
    predictions = []
    for case_path in iter_case_files(args.cases):
        case = json.loads(case_path.read_text())
        packet = load_or_build_packet(case_path, packet_root)
        prediction = diagnose(packet, use_llm=args.llm, llm_command=args.llm_command)
        rows.append(
            {
                "case_id": case.get("case_id"),
                "design_id": case.get("design_id"),
                "gold_issue_type": case.get("expected_issue_type"),
                "predicted_issue_type": prediction.get("predicted_issue_type"),
                "gold_next_action": case.get("expected_next_action"),
                "predicted_next_action": prediction.get("recommended_next_action"),
            }
        )
        predictions.append({"case": case, "prediction": prediction})

    summary = {
        "num_cases": len(rows),
        "cases_by_design": dict(sorted(collections.Counter(row["design_id"] for row in rows).items())),
        "issue_type_accuracy": accuracy(rows, "predicted_issue_type", "gold_issue_type"),
        "next_action_accuracy": accuracy(rows, "predicted_next_action", "gold_next_action"),
        "predicted_issue_distribution": dict(
            sorted(collections.Counter(row["predicted_issue_type"] for row in rows).items())
        ),
        "gold_issue_distribution": dict(
            sorted(collections.Counter(row["gold_issue_type"] for row in rows).items())
        ),
        "rows": rows,
    }

    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"summary": summary, "predictions": predictions}, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
