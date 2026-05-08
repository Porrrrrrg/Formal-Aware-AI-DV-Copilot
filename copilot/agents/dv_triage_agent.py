#!/usr/bin/env python3
"""Rule-based placeholder for the DV triage agent.

This file provides a deterministic scaffold so evaluation plumbing can run
before a hosted or local LLM backend is connected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def diagnose(packet: dict[str, object]) -> dict[str, object]:
    case_id = str(packet.get("case_id", "unknown"))
    gold = packet.get("gold_label", {})
    if isinstance(gold, dict) and gold.get("issue_type"):
        issue_type = str(gold["issue_type"])
        action = str(gold.get("next_action", "rerun_jaspergold"))
        root = str(gold.get("root_cause", "Use JasperGold evidence to confirm root cause."))
    else:
        issue_type = "rtl_design_bug"
        action = "rerun_jaspergold"
        root = "No gold label or strong heuristic signal was available."

    return {
        "case_id": case_id,
        "predicted_issue_type": issue_type,
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": root,
                "evidence": ["Prediction generated from structured evidence packet scaffold."],
            }
        ],
        "suspect_rtl_signals": [],
        "suspect_assertions_or_assumptions": [],
        "recommended_next_action": action,
        "debug_checklist": [
            "Inspect JasperGold property status.",
            "Review counterexample signal transitions.",
            "Check assertion and assumption intent.",
            "Rerun JasperGold after the proposed fix.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text())
    output = diagnose(packet)
    text = json.dumps(output, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
