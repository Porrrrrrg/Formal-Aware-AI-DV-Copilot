#!/usr/bin/env python3
"""Evaluate SVA generation systems on local property-intent cases."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.sva_generation_agent import generate as generate_structured  # noqa: E402
from copilot.baselines.direct_sva_llm import generate_direct  # noqa: E402
from copilot.sva_library import hallucinated_identifiers, normalize_sva, syntax_scaffold_ok  # noqa: E402
from evaluation.metrics import accuracy  # noqa: E402
from tools.check_generated_sva import check_generated_sva  # noqa: E402

ALL_SYSTEMS = ["direct", "structured"]


def load_cases(path: Path) -> list[dict[str, object]]:
    data = json.loads(resolve_repo_path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return [case for case in data if isinstance(case, dict)]


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def predict(
    system: str,
    case: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if system == "direct":
        return generate_direct(case, use_llm=use_llm, llm_command=llm_command)
    if system == "structured":
        return generate_structured(case, use_llm=use_llm, llm_command=llm_command)
    raise ValueError(f"Unknown SVA generation system: {system}")


def evaluate_system(
    system: str,
    cases: list[dict[str, object]],
    use_llm: bool = False,
    llm_command: str | None = None,
    jasper_check: bool = False,
    jasper_dry_run: bool = False,
    jasper_out_root: Path | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows = []
    predictions = []
    for case in cases:
        prediction = predict(system, case, use_llm=use_llm, llm_command=llm_command)
        row = evaluate_prediction(system, case, prediction)
        if jasper_check or jasper_dry_run:
            jasper_result = check_generated_sva(
                case=case,
                prediction=prediction,
                system=system,
                out_root=jasper_out_root,
                dry_run=jasper_dry_run,
            )
            row.update(
                {
                    "jasper_syntax_pass": jasper_result.get("syntax_pass"),
                    "jasper_proof_status": jasper_result.get("proof_status"),
                    "jasper_vacuity_status": jasper_result.get("vacuity_status"),
                    "jasper_report_dir": jasper_result.get("report_dir"),
                }
            )
        rows.append(row)
        predictions.append({"system": system, "case": sanitized_case(case), "prediction": prediction, "metrics": row})
    return summarize_rows(rows), predictions


def evaluate_prediction(
    system: str,
    case: dict[str, object],
    prediction: dict[str, object],
) -> dict[str, object]:
    sva = str(prediction.get("sva", ""))
    reference = str(case.get("reference_sva", ""))
    allowed = list(case.get("signals", [])) if isinstance(case.get("signals"), list) else []
    allowed.append(str(case.get("property_id", "")))
    hallucinated = hallucinated_identifiers(sva, allowed)
    return {
        "system": system,
        "case_id": case.get("case_id"),
        "design_id": case.get("design_id"),
        "property_id": case.get("property_id"),
        "syntax_ok": syntax_scaffold_ok(sva),
        "exact_match": normalize_sva(sva) == normalize_sva(reference),
        "has_hallucinated_signal": bool(hallucinated),
        "hallucinated_identifiers": hallucinated,
    }


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "num_cases": 0,
            "cases_by_design": {},
            "syntax_scaffold_rate": 0.0,
            "exact_match_rate": 0.0,
            "hallucinated_signal_rate": 0.0,
            "rows": [],
        }
    exact_rows = [
        {**row, "pred": row["exact_match"], "gold": True}
        for row in rows
    ]
    syntax_rows = [
        {**row, "pred": row["syntax_ok"], "gold": True}
        for row in rows
    ]
    hallucination_rows = [
        {**row, "pred": row["has_hallucinated_signal"], "gold": False}
        for row in rows
    ]
    hallucinated = sum(1 for row in rows if row["has_hallucinated_signal"])
    summary = {
        "num_cases": len(rows),
        "cases_by_design": dict(sorted(collections.Counter(row["design_id"] for row in rows).items())),
        "syntax_scaffold_rate": accuracy(syntax_rows, "pred", "gold"),
        "exact_match_rate": accuracy(exact_rows, "pred", "gold"),
        "hallucinated_signal_rate": hallucinated / len(rows),
        "no_hallucinated_signal_rate": accuracy(hallucination_rows, "pred", "gold"),
        "rows": rows,
    }
    jasper_rows = [row for row in rows if row.get("jasper_syntax_pass") is not None]
    if jasper_rows:
        proven = sum(1 for row in jasper_rows if row.get("jasper_proof_status") == "proven")
        vacuous = sum(1 for row in jasper_rows if row.get("jasper_vacuity_status") == "vacuous")
        summary.update(
            {
                "jasper_checked_cases": len(jasper_rows),
                "jasper_syntax_pass_rate": (
                    sum(1 for row in jasper_rows if row.get("jasper_syntax_pass")) / len(jasper_rows)
                    if jasper_rows
                    else 0.0
                ),
                "jasper_proven_rate": proven / len(jasper_rows) if jasper_rows else 0.0,
                "jasper_vacuous_rate": vacuous / len(jasper_rows) if jasper_rows else 0.0,
            }
        )
    elif any("jasper_syntax_pass" in row for row in rows):
        summary["jasper_dry_run_cases"] = len(rows)
    return summary


def sanitized_case(case: dict[str, object]) -> dict[str, object]:
    clone = dict(case)
    clone.pop("reference_sva", None)
    return clone


def compact_summary(summaries: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    return {
        system: {key: value for key, value in summary.items() if key != "rows"}
        for system, summary in summaries.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("benchmarks/sva_generation_cases.json"))
    parser.add_argument("--systems", nargs="+", choices=ALL_SYSTEMS, default=ALL_SYSTEMS)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--jasper-dry-run", action="store_true")
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/sva_generation"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    summaries = {}
    all_predictions = []
    for system in args.systems:
        summary, predictions = evaluate_system(
            system,
            cases,
            use_llm=args.llm,
            llm_command=args.llm_command,
            jasper_check=args.jasper_check,
            jasper_dry_run=args.jasper_dry_run,
            jasper_out_root=resolve_repo_path(args.jasper_out_root),
        )
        summaries[system] = summary
        all_predictions.extend(predictions)

    payload = {
        "num_cases": len(cases),
        "systems": summaries,
        "predictions": all_predictions,
    }
    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"num_cases": len(cases), "systems": compact_summary(summaries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
