#!/usr/bin/env python3
"""Re-check saved SVA repair evaluator outputs with JasperGold."""

from __future__ import annotations

import argparse
import collections
import json
import os
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.check_generated_sva import check_generated_sva  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_cases(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    cases: dict[str, dict[str, Any]] = {}
    for row in data:
        if isinstance(row, dict) and row.get("case_id"):
            cases[str(row["case_id"])] = row
    return cases


def final_candidate(result: dict[str, Any]) -> dict[str, Any]:
    rounds = result.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise ValueError(f"{result.get('case_id')} has no repair rounds")
    final_round = rounds[-1]
    if not isinstance(final_round, dict):
        raise ValueError(f"{result.get('case_id')} final round is not an object")
    sva = final_round.get("sva")
    if not isinstance(sva, str) or not sva.strip():
        raise ValueError(f"{result.get('case_id')} final round has no SVA")
    return {
        "property_id": result.get("property_id") or "generated_property",
        "sva": sva,
        "source": "local_qwen_full",
        "source_run_id": "v1.1.2-local-qwen-full-benchmark",
    }


def recheck_results(
    source: Path,
    cases_path: Path,
    out_root: Path,
    system: str,
) -> dict[str, Any]:
    payload = load_json(source)
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError(f"{source} must contain a top-level results array")
    cases = load_cases(cases_path)
    rows = []
    for index, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            raise ValueError(f"{source}: result {index} is not an object")
        case_id = str(result.get("case_id") or "")
        if case_id not in cases:
            raise ValueError(f"{source}: unknown case_id {case_id!r}")
        prediction = final_candidate(result)
        check = check_generated_sva(
            case=cases[case_id],
            prediction=prediction,
            system=system,
            out_root=resolve_repo_path(out_root),
            dry_run=False,
        )
        rows.append(build_row(result, prediction, check))
    return build_payload(source, cases_path, out_root, rows)


def build_row(result: dict[str, Any], prediction: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    exact_match = result.get("final_exact_match")
    scaffold_success = result.get("scaffold_success")
    hallucinated = result.get("hallucinated_signals")
    if not isinstance(hallucinated, list):
        hallucinated = []
    syntax_pass = check.get("syntax_pass")
    proof_status = check.get("proof_status")
    vacuity_status = check.get("vacuity_status")
    return {
        "case_id": result.get("case_id"),
        "design_id": result.get("design_id"),
        "property_id": result.get("property_id"),
        "bug_type": result.get("bug_type"),
        "qwen_final_exact_match": exact_match,
        "qwen_scaffold_success": scaffold_success,
        "qwen_hallucinated_signals": hallucinated,
        "jasper_syntax_pass": syntax_pass,
        "jasper_proof_status": proof_status,
        "jasper_vacuity_status": vacuity_status,
        "jasper_returncode": check.get("jasper_returncode"),
        "jasper_report_dir": repo_relative(check.get("report_dir")),
        "properties_report": repo_relative(check.get("properties_report")),
        "vacuity_report": repo_relative(check.get("vacuity_report")),
        "candidate_sva": prediction["sva"],
        "exact_match_but_jasper_failed": exact_match is True
        and not jasper_formal_passed(syntax_pass, proof_status, vacuity_status),
        "proof_passed_but_exact_match_failed": proof_status == "proven" and exact_match is not True,
        "hallucinated_signal_syntax_failure": bool(hallucinated) and syntax_pass is False,
    }


def jasper_formal_passed(syntax_pass: object, proof_status: object, vacuity_status: object) -> bool:
    return syntax_pass is True and proof_status == "proven" and vacuity_status != "vacuous"


def repo_relative(value: object) -> str | None:
    if value is None:
        return None
    path = Path(str(value))
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(value)


def build_payload(source: Path, cases_path: Path, out_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    syntax_pass_count = count_value(rows, "jasper_syntax_pass", True)
    proof_counts = collections.Counter(str(row.get("jasper_proof_status") or "not_reported") for row in rows)
    vacuity_counts = collections.Counter(str(row.get("jasper_vacuity_status") or "not_reported") for row in rows)
    return {
        "run": {
            "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "host": platform.node(),
            "jasper_bin": os.environ.get("JASPER_BIN") or "jg",
            "jasper_bin_resolved": shutil.which(os.environ.get("JASPER_BIN") or "jg"),
            "source_checkpoint": "v1.1.2-local-qwen-full-benchmark",
            "source_artifact": source.as_posix(),
            "cases": cases_path.as_posix(),
            "out_root": out_root.as_posix(),
        },
        "summary": {
            "num_candidates": len(rows),
            "syntax_pass_count": syntax_pass_count,
            "syntax_pass_rate": syntax_pass_count / len(rows) if rows else 0.0,
            "proof_status_counts": dict(sorted(proof_counts.items())),
            "proven_count": proof_counts.get("proven", 0),
            "falsified_count": proof_counts.get("cex", 0) + proof_counts.get("falsified", 0),
            "undetermined_count": proof_counts.get("undetermined", 0),
            "vacuity_status_counts": dict(sorted(vacuity_counts.items())),
            "vacuous_count": vacuity_counts.get("vacuous", 0),
            "not_flagged_vacuous_count": len(rows) - vacuity_counts.get("vacuous", 0),
            "exact_match_but_jasper_failed_count": sum(
                1 for row in rows if row["exact_match_but_jasper_failed"]
            ),
            "proof_passed_but_exact_match_failed_count": sum(
                1 for row in rows if row["proof_passed_but_exact_match_failed"]
            ),
            "hallucinated_signal_syntax_failure_count": sum(
                1 for row in rows if row["hallucinated_signal_syntax_failure"]
            ),
        },
        "rows": rows,
    }


def count_value(rows: list[dict[str, Any]], key: str, value: object) -> int:
    return sum(1 for row in rows if row.get(key) == value)


def write_markdown(payload: dict[str, Any], out: Path) -> None:
    summary = payload["summary"]
    run = payload["run"]
    rows = payload["rows"]
    lines = [
        "# Local Qwen JasperGold Re-check Results",
        "",
        f"Date: {run['created_utc']}",
        "",
        f"Host: `{run['host']}`",
        "",
        f"JasperGold executable: `{run['jasper_bin']}`",
        "",
        f"Resolved executable: `{run['jasper_bin_resolved']}`",
        "",
        "Source checkpoint: `v1.1.2-local-qwen-full-benchmark`",
        "",
        f"Raw Qwen artifact: `{run['source_artifact']}`",
        "",
        "This is a JasperGold-backed re-check of saved local Qwen SVA repair outputs. It is not Codex CLI performance, not official FVEval performance, and not production signoff.",
        "",
        "Proof outcomes are scoped to the generated harnesses, assumptions, properties, and JasperGold environment used for this run. A proof pass does not establish full semantic intent equivalence.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Candidates rechecked | {summary['num_candidates']} |",
        f"| Syntax pass rate | {summary['syntax_pass_rate']:.3f} |",
        f"| Proven count | {summary['proven_count']} |",
        f"| Falsified count | {summary['falsified_count']} |",
        f"| Undetermined count | {summary['undetermined_count']} |",
        f"| Vacuous count | {summary['vacuous_count']} |",
        f"| Not flagged vacuous count | {summary['not_flagged_vacuous_count']} |",
        f"| Exact-match success but JasperGold failed | {summary['exact_match_but_jasper_failed_count']} |",
        f"| Proof passed but exact match failed | {summary['proof_passed_but_exact_match_failed_count']} |",
        f"| Hallucinated signal caused syntax failure | {summary['hallucinated_signal_syntax_failure_count']} |",
        "",
        "Proof status counts:",
        "",
        "```json",
        json.dumps(summary["proof_status_counts"], indent=2),
        "```",
        "",
        "Vacuity status counts:",
        "",
        "```json",
        json.dumps(summary["vacuity_status_counts"], indent=2),
        "```",
        "",
    ]
    add_case_table(
        lines,
        "Exact-Match Success But JasperGold Failed",
        [row for row in rows if row["exact_match_but_jasper_failed"]],
    )
    add_case_table(
        lines,
        "Proof Passed But Exact Match Failed",
        [row for row in rows if row["proof_passed_but_exact_match_failed"]],
    )
    add_case_table(
        lines,
        "Hallucinated Signal Syntax Failures",
        [row for row in rows if row["hallucinated_signal_syntax_failure"]],
    )
    add_case_table(lines, "All Rechecked Candidates", rows)
    out_path = resolve_repo_path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def add_case_table(lines: list[str], title: str, rows: list[dict[str, Any]]) -> None:
    lines.extend([f"## {title}", ""])
    if not rows:
        lines.extend(["None.", ""])
        return
    lines.extend(
        [
            "| Case | Design | Qwen exact | Syntax | Proof | Vacuity | Report |",
            "| --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| `{case}` | `{design}` | {exact} | {syntax} | `{proof}` | `{vacuity}` | `{report}` |".format(
                case=row.get("case_id"),
                design=row.get("design_id"),
                exact=str(row.get("qwen_final_exact_match")).lower(),
                syntax=str(row.get("jasper_syntax_pass")).lower(),
                proof=display_status(row.get("jasper_proof_status")),
                vacuity=display_status(row.get("jasper_vacuity_status")),
                report=row.get("jasper_report_dir"),
            )
        )
    lines.append("")


def display_status(value: object) -> str:
    if value is None:
        return "not_reported"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=Path("benchmarks/sva_repair_cases.json"))
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/qwen_jasper_recheck"))
    parser.add_argument("--system", default="local_qwen_sva_repair_full")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    payload = recheck_results(
        source=args.input,
        cases_path=args.cases,
        out_root=args.jasper_out_root,
        system=args.system,
    )
    out_json = resolve_repo_path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.out_md)
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
