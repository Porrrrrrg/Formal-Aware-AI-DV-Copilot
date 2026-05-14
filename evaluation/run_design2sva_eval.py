#!/usr/bin/env python3
"""Evaluate retrieval-assisted Design2SVA on local fixture tasks."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.design2sva_agent import (  # noqa: E402
    DEFAULT_REPLAY_PATH,
    generate_candidates,
    load_replay_records,
    normalize_candidate,
    structured_candidate,
    validate_candidate,
)
from copilot.backends.jasper_backend import JasperBackend  # noqa: E402
from copilot.retrieval import Design2SVAContextOptions, build_design2sva_context  # noqa: E402
from copilot.sva_library import hallucinated_identifiers, normalize_sva, syntax_scaffold_ok  # noqa: E402

DEFAULT_CASES = Path("benchmarks/design2sva_cases.json")
DEFAULT_OUT = Path("evaluation/results/design2sva_eval_local.json")
DEFAULT_MARKDOWN = Path("evaluation/results/design2sva_results.md")
TASK_SCHEMA = ROOT / "copilot" / "schemas" / "design2sva_task.schema.json"

FAILURE_CATEGORIES = {
    "passed",
    "syntax_error",
    "unknown_signal",
    "reset_clock_mismatch",
    "overstrong_assertion",
    "weak_vacuous_assertion",
    "temporal_mismatch",
    "unsupported_helper_code_issue",
    "invalid_json",
    "backend_blocked",
    "not_run",
}


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    schema = json.loads(TASK_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    cases = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"{path} contains a non-object case entry")
        validator.validate(item)
        cases.append(item)
    return cases


def build_context(case: dict[str, Any], context_budget: int) -> dict[str, Any]:
    rtl_path = resolve_repo_path(Path(str(case["design_rtl_path"])))
    return build_design2sva_context(
        [rtl_path],
        Design2SVAContextOptions(
            module_name=str(case.get("module_name") or case["design_id"]),
            focus_signals=tuple(str(signal) for signal in case.get("visible_signals", [])),
            property_intent=str(case.get("intent", "")),
            visible_signal_budget=context_budget,
        ),
    )


def run_case(
    case: dict[str, Any],
    k: int,
    max_repair_rounds: int,
    use_llm: bool,
    llm_command: str | None,
    replay_records: list[dict[str, Any]] | None,
    jasper_check: bool,
    jasper_dry_run: bool,
    jasper_out_root: Path,
    context_budget: int,
) -> dict[str, Any]:
    context = build_context(case, context_budget=context_budget)
    initial_candidates = generate_candidates(
        case,
        context,
        k=k,
        use_llm=use_llm,
        llm_command=llm_command,
        replay_records=replay_records,
    )
    candidate_paths = []
    for candidate_index, candidate in enumerate(initial_candidates):
        rounds = []
        current = candidate
        for round_index in range(max_repair_rounds + 1):
            evaluated = evaluate_candidate(
                case=case,
                context=context,
                candidate=current,
                candidate_index=candidate_index,
                round_index=round_index,
                jasper_check=jasper_check,
                jasper_dry_run=jasper_dry_run,
                jasper_out_root=jasper_out_root,
            )
            rounds.append(evaluated)
            if row_success(evaluated["metrics"], formal_mode=jasper_check and not jasper_dry_run):
                break
            if round_index == max_repair_rounds:
                break
            current = repair_candidate(case, context, current, evaluated["metrics"], round_index + 1)
        candidate_paths.append(
            {
                "candidate_index": candidate_index,
                "rounds": rounds,
                "final_metrics": rounds[-1]["metrics"],
            }
        )

    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "context": context,
        "candidate_paths": candidate_paths,
    }


def evaluate_candidate(
    case: dict[str, Any],
    context: dict[str, Any],
    candidate: dict[str, Any],
    candidate_index: int,
    round_index: int,
    jasper_check: bool,
    jasper_dry_run: bool,
    jasper_out_root: Path,
) -> dict[str, Any]:
    validation_error = ""
    valid_json = True
    try:
        validate_candidate(candidate)
    except ValidationError as exc:
        valid_json = False
        validation_error = exc.message

    sva = str(candidate.get("sva", ""))
    allowed = sorted(allowed_identifiers(case, context))
    hallucinated = hallucinated_identifiers(sva, allowed + [str(case["property_id"])])
    helper_issue = helper_code_disallowed(case, str(candidate.get("helper_code", "")))
    reset_clock_issue = reset_clock_mismatch(case, sva)
    reference = reference_sva(case)
    exact_match = normalize_sva(sva) == normalize_sva(reference) if reference else None
    backend_result = None
    proof_metadata = {
        "backend": "jaspergold",
        "status": "not_run",
        "syntax_status": "not_run",
        "proof_status": None,
        "vacuity_status": None,
        "report_dir": None,
    }
    if jasper_check:
        backend_result = JasperBackend().check_generated_sva(
            case=legacy_case_shape(case),
            prediction=candidate,
            system=f"design2sva_c{candidate_index}_r{round_index}",
            out_root=jasper_out_root,
            dry_run=jasper_dry_run,
        )
        proof_metadata = {
            "backend": backend_result.backend,
            "status": backend_result.status.value,
            "syntax_status": backend_result.syntax_result.status.value,
            "proof_status": backend_result.to_legacy_check_dict().get("proof_status"),
            "vacuity_status": backend_result.to_legacy_check_dict().get("vacuity_status"),
            "report_dir": backend_result.report_dir,
        }

    metrics = {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "candidate_index": candidate_index,
        "round": round_index,
        "valid_json": valid_json,
        "validation_error": validation_error,
        "syntax_ok": syntax_scaffold_ok(sva),
        "exact_match": exact_match,
        "has_hallucinated_signal": bool(hallucinated),
        "hallucinated_identifiers": hallucinated,
        "reset_clock_mismatch": reset_clock_issue,
        "unsupported_helper_code_issue": helper_issue,
        "source": candidate.get("source", "unknown"),
        "proof_metadata": proof_metadata,
    }
    metrics["failure_category"] = classify_failure(metrics)
    candidate = dict(candidate)
    candidate["repair_metadata"] = {
        "round": round_index,
        "failure_category": metrics["failure_category"],
        "feedback": failure_feedback(metrics),
        "changed_by_repair": round_index > 0,
    }
    candidate["proof_metadata"] = proof_metadata
    if valid_json:
        validate_candidate(candidate)
    return {"candidate": candidate, "metrics": metrics}


def repair_candidate(
    case: dict[str, Any],
    context: dict[str, Any],
    candidate: dict[str, Any],
    metrics: dict[str, Any],
    round_index: int,
) -> dict[str, Any]:
    repaired = structured_candidate(case)
    repaired["source"] = "repair"
    repaired["failure_category"] = metrics["failure_category"]
    repaired["feedback"] = failure_feedback(metrics)
    repaired["changed_by_repair"] = normalize_sva(str(candidate.get("sva", ""))) != normalize_sva(
        str(repaired.get("sva", ""))
    )
    return normalize_candidate(case, context, repaired, source="repair", round_index=round_index)


def classify_failure(metrics: dict[str, Any]) -> str:
    if not metrics["valid_json"]:
        return "invalid_json"
    if metrics["unsupported_helper_code_issue"]:
        return "unsupported_helper_code_issue"
    if metrics["has_hallucinated_signal"]:
        return "unknown_signal"
    if not metrics["syntax_ok"]:
        return "syntax_error"
    proof = metrics.get("proof_metadata", {})
    if proof.get("status") == "blocked":
        return "backend_blocked"
    if proof.get("syntax_status") == "syntax_error":
        return "syntax_error"
    if metrics["reset_clock_mismatch"]:
        return "reset_clock_mismatch"
    if proof.get("vacuity_status") == "vacuous" or proof.get("status") == "vacuous":
        return "weak_vacuous_assertion"
    if proof.get("proof_status") == "falsified":
        return "overstrong_assertion"
    if proof.get("proof_status") in {"undetermined", "unknown"}:
        return "temporal_mismatch"
    if metrics["exact_match"] is False:
        return "temporal_mismatch"
    if proof.get("status") == "dry_run":
        return "not_run"
    return "passed"


def failure_feedback(metrics: dict[str, Any]) -> str:
    category = str(metrics.get("failure_category", "not_run"))
    if category == "unknown_signal":
        return "Candidate references unknown signals: " + ", ".join(metrics["hallucinated_identifiers"])
    if category == "unsupported_helper_code_issue":
        return "Candidate uses helper code when the task policy disallows helper code."
    if category == "reset_clock_mismatch":
        return "Candidate clock/reset event does not match the task clock/reset contract."
    if category == "syntax_error":
        return "Candidate failed local or Jasper SVA syntax checks."
    if category == "weak_vacuous_assertion":
        return "Candidate appears weak or vacuous under available feedback."
    if category == "overstrong_assertion":
        return "Candidate was falsified; it may be overstrong for the design and harness."
    if category == "temporal_mismatch":
        return "Candidate syntax is valid but temporal behavior does not match available reference feedback."
    return "No repair feedback was required."


def summarize(results: list[dict[str, Any]], k: int, jasper_check: bool, jasper_dry_run: bool) -> dict[str, Any]:
    first_round_rows = []
    all_initial_rows = []
    all_rows = []
    repair_rows = []
    for result in results:
        for path in result["candidate_paths"]:
            rounds = path["rounds"]
            if not rounds:
                continue
            all_initial_rows.append(rounds[0]["metrics"])
            all_rows.extend(round_record["metrics"] for round_record in rounds)
            if path["candidate_index"] == 0:
                first_round_rows.append(rounds[0]["metrics"])
            repair_rows.extend(round_record["metrics"] for round_record in rounds[1:])

    formal_mode = jasper_check and not jasper_dry_run
    first_by_case = group_initial_by_case(all_initial_rows)
    syntax_at_1 = rate(first_round_rows, lambda row: row["syntax_ok"])
    syntax_at_k = rate(
        list(first_by_case.values()),
        lambda rows: any(row["syntax_ok"] for row in rows[:k]),
    )
    proven_at_1 = rate(first_round_rows, formal_success) if formal_mode else 0.0
    proven_at_k = (
        rate(list(first_by_case.values()), lambda rows: any(formal_success(row) for row in rows[:k]))
        if formal_mode
        else 0.0
    )
    non_vacuous_at_k = (
        rate(
            list(first_by_case.values()),
            lambda rows: any(
                row["proof_metadata"].get("vacuity_status") != "vacuous" and formal_success(row)
                for row in rows[:k]
            ),
        )
        if formal_mode
        else 0.0
    )
    successes_after_feedback = [
        row_success(row, formal_mode=formal_mode) for row in repair_rows if int(row["round"]) > 0
    ]
    return {
        "num_cases": len(results),
        "k": k,
        "cases_by_design": dict(
            sorted(collections.Counter(result["design_id"] for result in results).items())
        ),
        "syntax@1": syntax_at_1,
        "syntax@k": syntax_at_k,
        "proven@1": proven_at_1,
        "proven@k": proven_at_k,
        "non_vacuous@k": non_vacuous_at_k,
        "formal_metrics_status": "measured" if formal_mode else "not_run",
        "hallucinated_signal_rate": rate(all_initial_rows, lambda row: row["has_hallucinated_signal"]),
        "fallback_rate": rate(all_initial_rows, lambda row: row["source"] == "structured_fallback"),
        "valid_json_rate": rate(all_initial_rows, lambda row: row["valid_json"]),
        "average_rounds": (
            sum(int(path["final_metrics"]["round"]) for result in results for path in result["candidate_paths"])
            / max(1, sum(len(result["candidate_paths"]) for result in results))
        ),
        "repair_success_after_feedback": (
            sum(1 for success in successes_after_feedback if success) / len(successes_after_feedback)
            if successes_after_feedback
            else 0.0
        ),
        "source_counts": dict(sorted(collections.Counter(row["source"] for row in all_initial_rows).items())),
        "failure_categories": dict(
            sorted(collections.Counter(row["failure_category"] for row in all_rows).items())
        ),
        "rows": all_rows,
    }


def render_markdown(summary: dict[str, Any], mode: str) -> str:
    return f"""# Design2SVA Results

## Summary

Mode: `{mode}`

| Metric | Value |
| --- | ---: |
| Cases | {summary["num_cases"]} |
| k | {summary["k"]} |
| syntax@1 | {summary["syntax@1"]:.3f} |
| syntax@k | {summary["syntax@k"]:.3f} |
| proven@1 | {summary["proven@1"]:.3f} |
| proven@k | {summary["proven@k"]:.3f} |
| non_vacuous@k | {summary["non_vacuous@k"]:.3f} |
| Hallucinated signal rate | {summary["hallucinated_signal_rate"]:.3f} |
| Fallback rate | {summary["fallback_rate"]:.3f} |
| Valid JSON rate | {summary["valid_json_rate"]:.3f} |
| Average rounds | {summary["average_rounds"]:.3f} |
| Repair success after feedback | {summary["repair_success_after_feedback"]:.3f} |

Formal metrics status: `{summary["formal_metrics_status"]}`.

## Boundaries

- Dry-run and replay rows validate local infrastructure and JSON contracts; they are not production signoff.
- `proven@*` and `non_vacuous@k` remain `0.000` with status `not_run` unless real JasperGold checks are explicitly enabled and available.
- Exact/reference agreement is a local scaffold signal for these fixtures, not a semantic equivalence result.
"""


def group_initial_by_case(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        grouped[str(row["case_id"])].append(row)
    return grouped


def rate(rows: list[Any], predicate) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if predicate(row)) / len(rows)


def formal_success(row: dict[str, Any]) -> bool:
    proof = row.get("proof_metadata", {})
    return proof.get("proof_status") == "proven" and proof.get("vacuity_status") != "vacuous"


def row_success(row: dict[str, Any], formal_mode: bool) -> bool:
    if row["failure_category"] in FAILURE_CATEGORIES - {"passed", "not_run"}:
        return False
    if formal_mode:
        return formal_success(row)
    return (
        row["valid_json"]
        and row["syntax_ok"]
        and not row["has_hallucinated_signal"]
        and not row["reset_clock_mismatch"]
        and not row["unsupported_helper_code_issue"]
        and row["exact_match"] is not False
    )


def allowed_identifiers(case: dict[str, Any], context: dict[str, Any]) -> set[str]:
    allowed = {str(signal) for signal in case.get("visible_signals", [])}
    allowed.update(str(signal) for signal in context.get("visible_signals", []))
    allowed.add(str(case["property_id"]))
    return allowed


def helper_code_disallowed(case: dict[str, Any], helper_code: str) -> bool:
    policy = case.get("helper_code_policy", {})
    allowed = bool(policy.get("allowed")) if isinstance(policy, dict) else False
    return bool(helper_code.strip()) and not allowed


def reset_clock_mismatch(case: dict[str, Any], sva: str) -> bool:
    clock_reset = case.get("clock_reset", {})
    if not isinstance(clock_reset, dict):
        return False
    clock = str(clock_reset.get("clock") or "")
    reset = str(clock_reset.get("reset") or "")
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    if clock and f"@(posedge {clock})" not in sva:
        return True
    if "disable iff" not in sva or not reset:
        return False
    expected = f"disable iff (!{reset})" if polarity == "active_low" else f"disable iff ({reset})"
    return expected not in sva


def reference_sva(case: dict[str, Any]) -> str:
    metadata = case.get("evaluation_metadata", {})
    if isinstance(metadata, dict):
        return str(metadata.get("reference_sva") or "")
    return ""


def legacy_case_shape(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "clock": case["clock_reset"]["clock"],
        "reset": case["clock_reset"].get("reset"),
        "signals": list(case.get("visible_signals", [])),
        "intent": case["intent"],
        "reference_sva": reference_sva(case),
    }


def run_mode(args: argparse.Namespace) -> str:
    if args.llm:
        return "real_llm"
    if args.replay:
        return "replay"
    return "deterministic_scaffold"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--max-repair-rounds", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replay", nargs="?", const=DEFAULT_REPLAY_PATH, type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/design2sva"))
    parser.add_argument("--context-budget", type=int, default=24)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    replay_records = load_replay_records(resolve_repo_path(args.replay)) if args.replay else None
    jasper_dry_run = bool(args.dry_run)
    results = [
        run_case(
            case=case,
            k=args.k,
            max_repair_rounds=args.max_repair_rounds,
            use_llm=args.llm,
            llm_command=args.llm_command,
            replay_records=replay_records,
            jasper_check=args.jasper_check,
            jasper_dry_run=jasper_dry_run,
            jasper_out_root=resolve_repo_path(args.jasper_out_root),
            context_budget=args.context_budget,
        )
        for case in cases
    ]
    summary = summarize(results, k=args.k, jasper_check=args.jasper_check, jasper_dry_run=jasper_dry_run)
    payload = {"summary": summary, "mode": run_mode(args), "results": results}
    if args.out:
        out_path = resolve_repo_path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        markdown_path = resolve_repo_path(args.markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(summary, run_mode(args)), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
