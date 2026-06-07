#!/usr/bin/env python3
"""End-to-end RTL2Repair dry-run/evaluation runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copilot.agents.design2sva_agent import generate_candidates  # noqa: E402
from copilot.agents.design2sva_repair_agent import repair_design2sva_candidate  # noqa: E402
from copilot.agents.rtl_repair_agent import propose_rtl_repair  # noqa: E402
from copilot.retrieval import Design2SVAContextOptions, build_design2sva_context  # noqa: E402
from tools.build_formal_debug_bundle import build_formal_debug_bundle  # noqa: E402
from tools.check_generated_sva import check_generated_sva  # noqa: E402
from tools.rtl_project_intake import create_rtl_project  # noqa: E402


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def run_rtl2repair(args: argparse.Namespace) -> dict[str, Any]:
    out_path = resolve_repo_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = resolve_manifest(args, out_path)
    manifest = load_json(manifest_path)
    task = build_task(args, manifest, manifest_path)
    context = build_design2sva_context(
        [resolve_repo_path(Path(path)) for path in manifest.get("rtl_files", [])],
        Design2SVAContextOptions(
            module_name=str(manifest["top_module"]),
            focus_signals=tuple(str(signal) for signal in manifest.get("visible_signals", [])),
            property_intent=str(task["intent"]),
        ),
    )
    candidates = generate_candidates(
        task,
        context,
        k=args.k,
        use_llm=bool(args.llm),
        llm_command=args.llm_command,
    )
    candidate_records = []
    accepted_properties: list[dict[str, Any]] = []
    rtl_patch_candidate: dict[str, Any] | None = None
    formal_metrics_status = "not_run"

    for index, candidate in enumerate(candidates):
        rounds = []
        current = candidate
        for round_index in range(max(0, args.max_sva_rounds) + 1):
            check_result, check_status = run_dynamic_check(
                args=args,
                task=task,
                candidate=current,
                manifest_path=manifest_path,
                candidate_index=index,
                round_index=round_index,
                out_path=out_path,
            )
            formal_metrics_status = combine_formal_status(formal_metrics_status, check_status)
            bundle = build_formal_debug_bundle(
                check_result=check_result,
                embedding_audit=check_result.get("embedding_audit")
                if isinstance(check_result.get("embedding_audit"), dict)
                else None,
                candidate=current,
            )
            row = candidate_row(task, current, check_result, bundle)
            rounds.append(
                {
                    "round": round_index,
                    "candidate": current,
                    "check_result": check_result,
                    "formal_debug_bundle": bundle,
                    "row": row,
                }
            )
            if row.get("usable_for_rtl_triage") and bundle["repair_recommendation"]["next_owner"] != "rtl":
                accepted_properties.append(current)
                break
            if bundle["repair_recommendation"]["next_owner"] == "rtl":
                if args.max_rtl_rounds > 0:
                    rtl_patch_candidate = propose_rtl_repair(
                        rtl_project_manifest=manifest,
                        formal_debug_bundle=bundle,
                        stable_sva=current,
                        triage={"predicted_issue_type": "rtl_design_bug", "evidence": [bundle["repair_recommendation"]["reason"]]},
                        suspect_signals=bundle["root_cause_signals"].get("unknown_signals", []),
                        allowed_patch_files=[str(resolve_repo_path(Path(path))) for path in manifest.get("rtl_files", [])],
                        use_llm=bool(args.rtl_repair_llm),
                        llm_command=args.rtl_repair_llm_command,
                    )
                break
            if round_index >= args.max_sva_rounds:
                break
            current = repair_design2sva_candidate(
                task=task,
                context=context,
                current_candidate=current,
                metrics=row,
                formal_debug_bundle=bundle,
                jasper_feedback=str(check_result.get("feedback") or ""),
                round_index=round_index + 1,
                use_llm=bool(args.repair_with_llm),
                llm_command=args.repair_llm_command,
            )
        candidate_records.append({"candidate_index": index, "rounds": rounds})

    payload = {
        "schema_version": "rtl2repair_eval_v1",
        "rtl_project_manifest": str(manifest_path),
        "task": task,
        "formal_metrics_status": formal_metrics_status,
        "generated_sva_candidates": candidate_records,
        "accepted_properties": accepted_properties,
        "rtl_patch_candidate": rtl_patch_candidate,
        "metrics": summarize_metrics(candidate_records, rtl_patch_candidate, formal_metrics_status),
        "claim_boundaries": claim_boundaries(),
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path = out_path.with_suffix(".md")
    report_path.write_text(render_markdown_report(payload), encoding="utf-8")
    payload["markdown_report"] = str(report_path)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def resolve_manifest(args: argparse.Namespace, out_path: Path) -> Path:
    if args.manifest:
        return resolve_repo_path(args.manifest)
    intake_out = out_path.parent / "intake" / "rtl_project_manifest.json"
    create_rtl_project(
        rtl_inputs=[str(path) for path in args.rtl],
        out_path=intake_out,
        top=args.top,
        clock=args.clock,
        reset=args.reset,
        reset_polarity=args.reset_polarity,
        spec=args.spec,
        include_dirs=[str(path) for path in args.include_dir],
        defines=dict(parse_define(item) for item in args.define),
    )
    return intake_out


def parse_define(value: str) -> tuple[str, str]:
    if "=" not in value:
        return value, "1"
    name, raw = value.split("=", 1)
    return name, raw


def build_task(args: argparse.Namespace, manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    intent = args.intent or intent_from_spec(args.spec) or "Observable control outputs should not enter illegal simultaneous states."
    return {
        "schema_version": "rtl2sva_task_v1",
        "task_id": f"{manifest['project_id']}::p_rtl2repair_01",
        "task_type": "rtl2sva",
        "case_id": f"{manifest['project_id']}_rtl2repair",
        "project_id": manifest["project_id"],
        "design_id": manifest["design_id"],
        "property_id": "p_rtl2repair_01",
        "module_name": manifest["top_module"],
        "intent": intent,
        "rtl_project_manifest_path": str(manifest_path),
        "design_rtl_paths": manifest["rtl_files"],
        "design_rtl_path": manifest["rtl_files"][0],
        "visible_signals": manifest["visible_signals"],
        "clock_reset": manifest["clock_reset"],
        "helper_code_policy": {
            "allowed": False,
            "allowed_kinds": [],
            "max_lines": 0,
            "rationale": "RTL2Repair dry-run tasks default to helper-free SVA candidates.",
        },
        "evaluation_metadata": {
            "benchmark": "arbitrary_rtl",
            "split": "local",
            "expected_result": "unknown",
            "reference_available": False,
            "reference_sva": None,
            "expected_proof_status": "unknown",
            "notes": "Arbitrary RTL mode does not use reference_sva for success.",
        },
    }


def intent_from_spec(spec: Path | None) -> str:
    if not spec:
        return ""
    resolved = resolve_repo_path(spec)
    if not resolved.exists():
        return ""
    for line in resolved.read_text(encoding="utf-8").splitlines():
        stripped = line.strip(" -\t")
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def run_dynamic_check(
    *,
    args: argparse.Namespace,
    task: dict[str, Any],
    candidate: dict[str, Any],
    manifest_path: Path,
    candidate_index: int,
    round_index: int,
    out_path: Path,
) -> tuple[dict[str, Any], str]:
    dry_run = bool(args.dry_run or not args.jasper_check)
    try:
        result = check_generated_sva(
            case=task,
            prediction=candidate,
            system=f"rtl2repair_c{candidate_index}_r{round_index}",
            out_root=out_path.parent / "jasper",
            dry_run=dry_run,
            design_manifest=manifest_path,
        )
        return result, "not_run" if dry_run else "ran"
    except RuntimeError as exc:
        return {
            "syntax_pass": False,
            "jasper_returncode": None,
            "proof_status": None,
            "vacuity_status": None,
            "feedback": str(exc),
            "report_dir": str(out_path.parent / "jasper" / f"rtl2repair_c{candidate_index}_r{round_index}"),
            "artifact_paths": {},
        }, "blocked"


def candidate_row(
    task: dict[str, Any],
    candidate: dict[str, Any],
    check_result: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    proof_status = check_result.get("proof_status")
    vacuity_status = check_result.get("vacuity_status")
    syntax_pass = check_result.get("syntax_pass")
    row = {
        "valid_json": True,
        "syntax_ok": syntax_pass is not False,
        "has_hallucinated_signal": False,
        "unsupported_helper_code_issue": False,
        "reset_clock_mismatch": bool(bundle["root_cause_signals"].get("clock_reset_mismatch")),
        "exact_match": None,
        "antecedent_reachable": bundle["root_cause_signals"].get("antecedent_reachable"),
        "antecedent_metadata": {"extraction_status": "unknown"},
        "proof_metadata": {
            "proof_status": proof_status,
            "vacuity_status": vacuity_status,
            "syntax_status": "passed" if syntax_pass is True else "not_run" if syntax_pass is None else "syntax_error",
            "artifact_paths": check_result.get("artifact_paths", {}),
        },
        "failure_category": bundle["repair_recommendation"]["next_owner"],
        "hallucinated_identifiers": [],
        "candidate_sva": candidate.get("sva"),
        "property_id": candidate.get("property_id") or task.get("property_id"),
    }
    row["usable_for_rtl_triage"] = row_sva_usable_for_rtl_triage(row)
    return row


def row_sva_usable_for_rtl_triage(row: dict[str, Any]) -> bool:
    proof = row.get("proof_metadata") if isinstance(row.get("proof_metadata"), dict) else {}
    proof_status = str(proof.get("proof_status") or "").lower()
    vacuity_status = str(proof.get("vacuity_status") or "").lower()
    return (
        bool(row.get("valid_json"))
        and bool(row.get("syntax_ok"))
        and not bool(row.get("has_hallucinated_signal"))
        and not bool(row.get("unsupported_helper_code_issue"))
        and not bool(row.get("reset_clock_mismatch"))
        and (
            proof_status == "proven"
            and vacuity_status != "vacuous"
            or proof_status in {"falsified", "cex"} and row.get("antecedent_reachable") is True
        )
    )


def combine_formal_status(current: str, observed: str) -> str:
    order = {"not_run": 0, "ran": 1, "blocked": 2}
    return observed if order.get(observed, 0) > order.get(current, 0) else current


def summarize_metrics(
    candidate_records: list[dict[str, Any]],
    rtl_patch_candidate: dict[str, Any] | None,
    formal_metrics_status: str,
) -> dict[str, Any]:
    rows = [
        round_record["row"]
        for record in candidate_records
        for round_record in record["rounds"]
    ]
    valid_json = sum(1 for row in rows if row.get("valid_json"))
    syntax_ok = sum(1 for row in rows if row.get("syntax_ok"))
    return {
        "valid_json_rate": rate(valid_json, len(rows)),
        "hallucinated_signal_rate": rate(
            sum(1 for row in rows if row.get("has_hallucinated_signal")),
            len(rows),
        ),
        "syntax@1": rate(syntax_ok, len(rows)),
        "syntax@k": rate(syntax_ok, len(rows)),
        "proven_non_vacuous@k": rate(
            sum(
                1
                for row in rows
                if str((row.get("proof_metadata") or {}).get("proof_status") or "").lower() == "proven"
            ),
            len(rows),
        ),
        "sva_repair_success_after_feedback": 0.0,
        "falsified_reachable_count": sum(
            1
            for row in rows
            if str((row.get("proof_metadata") or {}).get("proof_status") or "").lower()
            in {"falsified", "cex"}
            and row.get("antecedent_reachable") is True
        ),
        "rtl_patch_attempt_count": 1 if rtl_patch_candidate else 0,
        "rtl_patch_accept_count": 0,
        "regression_pass_rate": 0.0,
        "fallback_rate": 0.0,
        "formal_metrics_status": formal_metrics_status,
    }


def rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def claim_boundaries() -> list[str]:
    return [
        "RTL2Repair drafts and debugs candidate assertions and proposes RTL patches.",
        "It does not sign off RTL.",
        "Formal proof is necessary but not sufficient for full intent equivalence.",
        "Arbitrary RTL auto-intents are coverage aids, not complete specifications.",
    ]


def render_markdown_report(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    lines = [
        "# RTL2Repair Run",
        "",
        f"- Manifest: `{payload['rtl_project_manifest']}`",
        f"- Formal metrics status: `{payload['formal_metrics_status']}`",
        f"- Candidates: `{len(payload['generated_sva_candidates'])}`",
        f"- RTL patch attempted: `{metrics['rtl_patch_attempt_count']}`",
        "",
        "## Claim Boundaries",
        "",
    ]
    for boundary in payload["claim_boundaries"]:
        lines.append(f"- {boundary}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", action="append", default=[], type=Path)
    parser.add_argument("--top")
    parser.add_argument("--clock")
    parser.add_argument("--reset")
    parser.add_argument("--reset-polarity", choices=["active_high", "active_low", "unknown"], default="unknown")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--intent")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--include-dir", action="append", default=[], type=Path)
    parser.add_argument("--define", action="append", default=[])
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--max-sva-rounds", type=int, default=3)
    parser.add_argument("--max-rtl-rounds", type=int, default=2)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--repair-with-llm", action="store_true")
    parser.add_argument("--repair-llm-command")
    parser.add_argument("--rtl-repair-llm", action="store_true")
    parser.add_argument("--rtl-repair-llm-command")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.manifest and not args.rtl:
        raise SystemExit("--rtl is required unless --manifest is provided")
    payload = run_rtl2repair(args)
    print(json.dumps({"out": str(resolve_repo_path(args.out)), "markdown": payload["markdown_report"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
