#!/usr/bin/env python3
"""Run or plan the RTL2Repair real-LLM patch subset evaluation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "artifacts" / "rtl2repair" / "llm_patch_subset" / "summary.json"
REQUIRED_CASE_KEYS = {
    "case_id",
    "design_id",
    "rtl_path",
    "top",
    "clock",
    "reset",
    "reset_polarity",
    "intent",
    "stable_sva",
    "regression_candidates",
    "expected_bug_type",
    "claim_boundary",
}
METRIC_KEYS = [
    "valid_json_rate",
    "non_empty_diff_rate",
    "patch_safety_pass_rate",
    "scratch_apply_rate",
    "target_closure_rate",
    "regression_pass_rate",
    "accepted_patch_rate",
    "fallback_rate",
]


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = resolve_repo_path(path)
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{resolved} must contain a JSON object.")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{resolved} must contain a non-empty cases array.")
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"{resolved}: cases[{index}] must be an object.")
        missing = sorted(REQUIRED_CASE_KEYS - set(case))
        if missing:
            raise ValueError(f"{resolved}: cases[{index}] missing required keys: {', '.join(missing)}")
        stable_sva = case.get("stable_sva")
        if not isinstance(stable_sva, dict) or not stable_sva.get("property_id") or not stable_sva.get("sva"):
            raise ValueError(f"{resolved}: cases[{index}].stable_sva must include property_id and sva.")
    return data


def build_eval_command(
    *,
    case: dict[str, Any],
    case_out: Path,
    provider_path: Path,
    llm_command: str | None,
    jasper_check: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(ROOT / "evaluation" / "run_rtl2repair_eval.py"),
        "--rtl",
        str(resolve_repo_path(Path(str(case["rtl_path"])))),
        "--top",
        str(case["top"]),
        "--clock",
        str(case["clock"]),
        "--reset",
        str(case["reset"]),
        "--reset-polarity",
        str(case["reset_polarity"]),
        "--intent",
        str(case["intent"]),
        "--k",
        "1",
        "--max-sva-rounds",
        "0",
        "--max-rtl-rounds",
        "1",
        "--llm",
        "--llm-command",
        f"{shell_quote(sys.executable)} {shell_quote(str(provider_path))}",
        "--regression-candidates",
        str(resolve_repo_path(Path(str(case["regression_candidates"])))),
        "--out",
        str(case_out),
    ]
    if llm_command:
        cmd.extend(["--rtl-repair-llm", "--rtl-repair-llm-command", llm_command])
    if jasper_check:
        cmd.append("--jasper-check")
    else:
        cmd.append("--dry-run")
    return cmd


def shell_quote(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def write_stable_sva_provider(case: dict[str, Any], provider_path: Path) -> None:
    provider_path.parent.mkdir(parents=True, exist_ok=True)
    stable = dict(case["stable_sva"])
    candidate = {
        "property_id": str(stable["property_id"]),
        "sva": str(stable["sva"]),
        "helper_code": str(stable.get("helper_code") or ""),
        "referenced_signals": [str(item) for item in stable.get("referenced_signals", [])],
        "intent_summary": str(stable.get("intent_summary") or case["intent"]),
        "source": "llm",
        "repair_metadata": {
            "round": 0,
            "failure_category": "not_run",
            "feedback": "",
            "changed_by_repair": False,
        },
        "proof_metadata": {
            "backend": "jaspergold",
            "status": "not_run",
            "syntax_status": "not_run",
            "proof_status": None,
            "vacuity_status": None,
            "report_dir": None,
        },
    }
    payload = json.dumps(candidate, sort_keys=True)
    provider_path.write_text(f"#!/usr/bin/env python3\nprint({payload!r})\n", encoding="utf-8")


def summarize_case_result(case: dict[str, Any], result_path: Path) -> dict[str, Any]:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    recheck = payload.get("patch_recheck") if isinstance(payload.get("patch_recheck"), dict) else {}
    patch_candidate = payload.get("rtl_patch_candidate") if isinstance(payload.get("rtl_patch_candidate"), dict) else {}
    recheck_metrics = recheck.get("metrics") if isinstance(recheck.get("metrics"), dict) else {}
    non_empty_diff = bool(str(patch_candidate.get("unified_diff") or "").strip())
    scratch_apply = bool(recheck.get("apply_manifest"))
    fallback = bool(
        not patch_candidate
        or not non_empty_diff
        or any("LLM repair failed:" in str(note) for note in patch_candidate.get("risk_notes", []))
    )
    return {
        "case_id": case["case_id"],
        "status": "completed",
        "result_json": str(result_path),
        "metrics": {
            "valid_json_rate": float((payload.get("metrics") or {}).get("valid_json_rate", 0.0)),
            "non_empty_diff_rate": 1.0 if non_empty_diff else 0.0,
            "patch_safety_pass_rate": 1.0 if scratch_apply else 0.0,
            "scratch_apply_rate": 1.0 if scratch_apply else 0.0,
            "target_closure_rate": 1.0 if recheck_metrics.get("target_pass") else 0.0,
            "regression_pass_rate": float(recheck_metrics.get("regression_pass_rate", 0.0)),
            "accepted_patch_rate": 1.0 if recheck.get("accepted") else 0.0,
            "fallback_rate": 1.0 if fallback else 0.0,
        },
        "patch_recheck_status": recheck.get("status"),
        "patch_accepted": bool(recheck.get("accepted")),
        "claim_boundary": case["claim_boundary"],
    }


def aggregate_metrics(case_results: list[dict[str, Any]]) -> dict[str, float]:
    completed = [case for case in case_results if isinstance(case.get("metrics"), dict)]
    if not completed:
        return {key: 0.0 for key in METRIC_KEYS}
    return {
        key: sum(float(case["metrics"].get(key, 0.0)) for case in completed) / len(completed)
        for key in METRIC_KEYS
    }


def render_curated_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# RTL2Repair Real LLM Patch Subset",
        "",
        "This curated summary separates real LLM RTL patch proposal behavior from deterministic SVA generation.",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    for key, value in summary["aggregate_metrics"].items():
        lines.append(f"| `{key}` | `{value:.3f}` |")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Status | Patch accepted | Patch recheck | Boundary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for case in summary["cases"]:
        lines.append(
            "| `{case_id}` | `{status}` | `{accepted}` | `{recheck}` | {boundary} |".format(
                case_id=case["case_id"],
                status=case["status"],
                accepted=case.get("patch_accepted", "n/a"),
                recheck=case.get("patch_recheck_status", "n/a"),
                boundary=str(case.get("claim_boundary") or ""),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Stable target SVAs are deterministic/manual for Phase A.",
            "- JasperGold remains the formal oracle.",
            "- LLM outputs are patch candidates only.",
            "- Do not cite this as arbitrary RTL auto-repair or production signoff.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_subset(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    out_path = resolve_repo_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    llm_command = args.llm_command or os.environ.get("JASPERLOOP_LLM_CMD")
    if not args.dry_run:
        if not llm_command:
            raise SystemExit("Real LLM patch subset runs require --llm-command or JASPERLOOP_LLM_CMD.")
        if not args.acknowledge_external_send:
            raise SystemExit(
                "Real LLM patch subset runs require --acknowledge-external-send before sending prompts."
            )

    case_results: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        case_out = out_path.parent / str(case["case_id"]) / "rtl2repair_eval.json"
        provider_path = out_path.parent / "stable_sva_providers" / f"{case['case_id']}_provider.py"
        command = build_eval_command(
            case=case,
            case_out=case_out,
            provider_path=provider_path,
            llm_command=llm_command if not args.dry_run else None,
            jasper_check=bool(args.jasper_check),
        )
        if args.dry_run:
            case_results.append(
                {
                    "case_id": case["case_id"],
                    "status": "planned",
                    "command": command,
                    "stable_sva_source": "deterministic_provider",
                    "patch_source": "real_llm_required_for_execution",
                    "claim_boundary": case["claim_boundary"],
                }
            )
            continue
        write_stable_sva_provider(case, provider_path)
        completed = subprocess.run(command, cwd=ROOT, check=False)
        case_summary = summarize_case_result(case, case_out) if case_out.exists() else {
            "case_id": case["case_id"],
            "status": "failed",
            "returncode": completed.returncode,
            "metrics": {key: 0.0 for key in METRIC_KEYS},
            "claim_boundary": case["claim_boundary"],
        }
        case_summary["returncode"] = completed.returncode
        case_summary["command"] = command
        case_results.append(case_summary)

    summary = {
        "schema_version": "rtl2repair_llm_patch_subset_summary_v1",
        "manifest": str(manifest_path),
        "dry_run": bool(args.dry_run),
        "jasper_check": bool(args.jasper_check),
        "external_send_acknowledged": bool(args.acknowledge_external_send),
        "cases": case_results,
        "aggregate_metrics": aggregate_metrics(case_results),
        "boundary": manifest.get("claim_boundary", ""),
    }
    out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.curated_out:
        curated_path = resolve_repo_path(args.curated_out)
        curated_path.parent.mkdir(parents=True, exist_ok=True)
        curated_path.write_text(render_curated_markdown(summary), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--llm-command")
    parser.add_argument("--acknowledge-external-send", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    parser.add_argument("--curated-out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_subset(args)
    print(json.dumps({"out": str(resolve_repo_path(args.out)), "cases": len(summary["cases"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
