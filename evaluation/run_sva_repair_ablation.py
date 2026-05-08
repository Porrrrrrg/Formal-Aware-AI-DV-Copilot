#!/usr/bin/env python3
"""Run SVA repair-loop ablations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.run_sva_repair_eval import load_cases, resolve_repo_path, run_repair_case, summarize  # noqa: E402

VARIANTS = {
    "no_repair_loop": {
        "label": "Round-0 only / no repair loop",
        "max_rounds": 0,
        "feedback_mode": "none",
    },
    "repair_loop_no_feedback": {
        "label": "Repair loop, no feedback",
        "max_rounds": None,
        "feedback_mode": "none",
    },
    "repair_loop_scaffold_feedback": {
        "label": "Repair loop, scaffold feedback",
        "max_rounds": None,
        "feedback_mode": "scaffold",
    },
    "repair_loop_jasper_feedback": {
        "label": "Repair loop, JasperGold feedback",
        "max_rounds": None,
        "feedback_mode": "jasper",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("benchmarks/sva_repair_cases.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--jasper-dry-run", action="store_true")
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/sva_repair_ablation"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]

    systems: dict[str, dict[str, object]] = {}
    all_results: list[dict[str, object]] = []
    for variant in args.variants:
        config = VARIANTS[variant]
        variant_rounds = int(config["max_rounds"] if config["max_rounds"] is not None else args.max_rounds)
        results = [
            run_repair_case(
                case=case,
                max_rounds=variant_rounds,
                use_llm=args.llm,
                llm_command=args.llm_command,
                jasper_check=args.jasper_check,
                jasper_dry_run=args.jasper_dry_run,
                jasper_out_root=resolve_repo_path(args.jasper_out_root) / variant,
                feedback_mode=str(config["feedback_mode"]),
            )
            for case in cases
        ]
        summary = summarize(results)
        summary["label"] = config["label"]
        summary["variant"] = variant
        systems[variant] = summary
        all_results.extend({"variant": variant, **result} for result in results)

    payload = {
        "num_cases": len(cases),
        "systems": systems,
        "results": all_results,
    }
    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"num_cases": len(cases), "systems": compact_summary(systems)}, indent=2))
    return 0


def compact_summary(systems: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    return {
        system: {key: value for key, value in summary.items() if key != "rows"}
        for system, summary in systems.items()
    }


if __name__ == "__main__":
    raise SystemExit(main())
