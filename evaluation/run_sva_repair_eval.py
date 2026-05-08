#!/usr/bin/env python3
"""Evaluate the JasperGold-in-the-loop SVA repair flow."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.sva_repair_agent import repair_once  # noqa: E402
from copilot.sva_library import hallucinated_identifiers, normalize_sva, syntax_scaffold_ok  # noqa: E402
from tools.check_generated_sva import check_generated_sva  # noqa: E402


def load_cases(path: Path) -> list[dict[str, object]]:
    data = json.loads(resolve_repo_path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return [case for case in data if isinstance(case, dict)]


def run_repair_case(
    case: dict[str, object],
    max_rounds: int,
    use_llm: bool = False,
    llm_command: str | None = None,
    jasper_check: bool = False,
    jasper_dry_run: bool = False,
    jasper_out_root: Path | None = None,
) -> dict[str, object]:
    rounds = []
    current_sva = str(case.get("broken_sva", ""))
    current_property_id = str(case.get("property_id", "generated_property"))
    feedback = "Initial broken SVA."
    final_round = None

    for round_index in range(max_rounds + 1):
        prediction = {"property_id": current_property_id, "sva": current_sva, "explanation": feedback}
        check = evaluate_candidate(
            case=case,
            prediction=prediction,
            system=f"repair_round{round_index}",
            jasper_check=jasper_check,
            jasper_dry_run=jasper_dry_run,
            jasper_out_root=jasper_out_root,
        )
        round_record = {
            "round": round_index,
            "sva": current_sva,
            "jasper_status": status_from_check(check),
            "feedback": check.get("feedback", feedback),
            "metrics": check,
        }
        rounds.append(round_record)
        if is_success(case, check):
            final_round = round_index
            break
        if round_index == max_rounds:
            break

        repair = repair_once(
            case=case,
            failed_sva=current_sva,
            feedback=str(check.get("feedback", "")),
            round_index=round_index + 1,
            use_llm=use_llm,
            llm_command=llm_command,
        )
        round_record["repair_action"] = repair
        current_property_id = str(repair.get("property_id", current_property_id))
        current_sva = str(repair.get("sva", current_sva))
        feedback = str(repair.get("explanation", ""))

    return {
        "case_id": case.get("case_id"),
        "design_id": case.get("design_id"),
        "property_id": case.get("property_id"),
        "bug_type": case.get("bug_type"),
        "rounds": rounds,
        "final_status": rounds[-1]["jasper_status"] if rounds else "not_run",
        "success": final_round is not None,
        "rounds_to_success": final_round,
    }


def evaluate_candidate(
    case: dict[str, object],
    prediction: dict[str, object],
    system: str,
    jasper_check: bool = False,
    jasper_dry_run: bool = False,
    jasper_out_root: Path | None = None,
) -> dict[str, object]:
    sva = str(prediction.get("sva", ""))
    reference = str(case.get("reference_sva", ""))
    allowed = list(case.get("signals", [])) if isinstance(case.get("signals"), list) else []
    allowed.append(str(case.get("property_id", "")))
    hallucinated = hallucinated_identifiers(sva, allowed)
    check = {
        "syntax_scaffold_ok": syntax_scaffold_ok(sva),
        "exact_match": normalize_sva(sva) == normalize_sva(reference),
        "has_hallucinated_signal": bool(hallucinated),
        "hallucinated_identifiers": hallucinated,
        "feedback": "Scaffold check only.",
    }
    if jasper_check or jasper_dry_run:
        jasper = check_generated_sva(
            case=case,
            prediction=prediction,
            system=system,
            out_root=jasper_out_root,
            dry_run=jasper_dry_run,
        )
        check.update(
            {
                "jasper_syntax_pass": jasper.get("syntax_pass"),
                "jasper_proof_status": jasper.get("proof_status"),
                "jasper_vacuity_status": jasper.get("vacuity_status"),
                "jasper_report_dir": jasper.get("report_dir"),
                "feedback": jasper.get("feedback") or "No JasperGold feedback was parsed.",
            }
        )
    return check


def is_success(case: dict[str, object], check: dict[str, object]) -> bool:
    if check.get("has_hallucinated_signal"):
        return False
    if check.get("exact_match"):
        if check.get("jasper_syntax_pass") is False:
            return False
        if check.get("jasper_proof_status") not in {None, "proven"}:
            return False
        if check.get("jasper_vacuity_status") == "vacuous":
            return False
        return True
    return False


def status_from_check(check: dict[str, object]) -> str:
    if "jasper_syntax_pass" in check:
        if check.get("jasper_syntax_pass") is False:
            return "syntax_fail"
        if check.get("jasper_syntax_pass") is None:
            return "dry_run"
        if check.get("jasper_vacuity_status") == "vacuous":
            return "vacuous"
        return str(check.get("jasper_proof_status") or "syntax_pass")
    if not check.get("syntax_scaffold_ok"):
        return "syntax_fail"
    if check.get("exact_match"):
        return "scaffold_pass"
    return "scaffold_fail"


def summarize(results: list[dict[str, object]]) -> dict[str, object]:
    rows = []
    for result in results:
        rounds = result.get("rounds", [])
        first = rounds[0] if rounds else {}
        final = rounds[-1] if rounds else {}
        rows.append(
            {
                "case_id": result.get("case_id"),
                "design_id": result.get("design_id"),
                "bug_type": result.get("bug_type"),
                "round0_status": first.get("jasper_status"),
                "final_status": result.get("final_status"),
                "success": result.get("success"),
                "rounds_to_success": result.get("rounds_to_success"),
                "round0_exact_match": first.get("metrics", {}).get("exact_match") if isinstance(first, dict) else None,
                "final_exact_match": final.get("metrics", {}).get("exact_match") if isinstance(final, dict) else None,
            }
        )
    successes = [row for row in rows if row["success"]]
    round_counts = [row["rounds_to_success"] for row in successes if isinstance(row["rounds_to_success"], int)]
    return {
        "num_cases": len(rows),
        "cases_by_design": dict(sorted(collections.Counter(row["design_id"] for row in rows).items())),
        "cases_by_bug_type": dict(sorted(collections.Counter(row["bug_type"] for row in rows).items())),
        "syntax_pass_round0": rate(rows, lambda row: row["round0_status"] not in {"syntax_fail"}),
        "repair_success_rate": len(successes) / len(rows) if rows else 0.0,
        "exact_match_round0": rate(rows, lambda row: row["round0_exact_match"] is True),
        "exact_match_final": rate(rows, lambda row: row["final_exact_match"] is True),
        "average_rounds_to_success": sum(round_counts) / len(round_counts) if round_counts else 0.0,
        "rows": rows,
    }


def rate(rows: list[dict[str, object]], predicate) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if predicate(row)) / len(rows)


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("benchmarks/sva_repair_cases.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--jasper-dry-run", action="store_true")
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/sva_repair"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    results = [
        run_repair_case(
            case=case,
            max_rounds=args.max_rounds,
            use_llm=args.llm,
            llm_command=args.llm_command,
            jasper_check=args.jasper_check,
            jasper_dry_run=args.jasper_dry_run,
            jasper_out_root=resolve_repo_path(args.jasper_out_root),
        )
        for case in cases
    ]
    summary = summarize(results)
    payload = {"summary": summary, "results": results}
    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
