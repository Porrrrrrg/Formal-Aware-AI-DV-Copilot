#!/usr/bin/env python3
"""Run Stage 4A SVA repair ablations.

The runner intentionally separates local scaffold metrics from live JasperGold
proof metrics. Unless ``--jasper-check`` is used on Moore, generated candidates
are reported as needing a Moore handoff for final proof/vacuity validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.run_sva_repair_eval import load_cases, resolve_repo_path, run_repair_case, summarize  # noqa: E402

VARIANTS: dict[str, dict[str, object]] = {
    "baseline_prompt": {
        "label": "baseline prompt",
        "description": "Baseline prompt, single repair attempt, no tool-feedback emphasis.",
        "prompt_version": "baseline",
        "feedback_mode": "none",
        "max_rounds": 1,
    },
    "cex_aware_prompt": {
        "label": "cex-aware prompt",
        "description": "Counterexample-aware prompt context with scaffold/Jasper feedback channel.",
        "prompt_version": "cex_aware",
        "feedback_mode": "jasper",
        "max_rounds": 1,
    },
    "signal_whitelist_only": {
        "label": "signal whitelist only",
        "description": "Prompt variant isolating allowed-signal whitelist pressure.",
        "prompt_version": "signal_whitelist",
        "feedback_mode": "none",
        "max_rounds": 1,
    },
    "temporal_hint_only": {
        "label": "temporal hint only",
        "description": "Prompt variant emphasizing clock/reset and implication timing.",
        "prompt_version": "temporal_hint",
        "feedback_mode": "none",
        "max_rounds": 1,
    },
    "one_round_repair": {
        "label": "one-round repair",
        "description": "Baseline prompt with one repair attempt after local scaffold feedback.",
        "prompt_version": "baseline",
        "feedback_mode": "scaffold",
        "max_rounds": 1,
    },
    "multi_round_repair": {
        "label": "multi-round repair",
        "description": "Baseline prompt with up to three repair attempts after scaffold feedback.",
        "prompt_version": "baseline",
        "feedback_mode": "scaffold",
        "max_rounds": 3,
    },
    "self_check_before_final": {
        "label": "self-check before final answer",
        "description": "Prompt variant requiring an internal identifier/syntax/intent self-check.",
        "prompt_version": "self_check",
        "feedback_mode": "scaffold",
        "max_rounds": 1,
    },
}

EXTERNAL_SEND_WARNING = """\
This command will send SVA repair benchmark content to the configured LLM backend.
Rerun with --acknowledge-external-send if you approve that data export.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("benchmarks/sva_repair_cases.json"))
    parser.add_argument("--case-set", choices=["stage3d_repair", "all"], default="stage3d_repair")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--codex-adapter", action="store_true")
    parser.add_argument("--codex-model")
    parser.add_argument("--codex-timeout", type=int, default=600)
    parser.add_argument("--acknowledge-external-send", action="store_true")
    parser.add_argument("--jasper-check", action="store_true")
    parser.add_argument("--jasper-dry-run", action="store_true")
    parser.add_argument("--jasper-out-root", type=Path, default=Path("jasper/reports/sva_repair_ablation"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--error-cases-out", type=Path)
    parser.add_argument("--candidate-artifact-out", type=Path)
    parser.add_argument(
        "--stage3-final-proof-manifest",
        type=Path,
        default=Path("reports/jasper/codex_repair_final_proof_manifest_20260511T053413Z.json"),
    )
    args = parser.parse_args()

    if args.llm and not args.acknowledge_external_send:
        sys.stderr.write(EXTERNAL_SEND_WARNING)
        return 2

    created_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    git_sha = git_rev_parse("HEAD")
    final_proof = load_final_proof(args.stage3_final_proof_manifest)
    cases = load_cases(args.cases)
    cases = filter_cases(cases, args.case_set, final_proof)
    if args.limit is not None:
        cases = cases[: args.limit]

    llm_command = args.llm_command
    if args.codex_adapter:
        llm_command = build_codex_adapter_command(args.codex_timeout, args.codex_model)
    systems: dict[str, dict[str, object]] = {}
    all_results: list[dict[str, object]] = []

    for variant in args.variants:
        config = VARIANTS[variant]
        results = [
            run_repair_case(
                case=case,
                max_rounds=int(config["max_rounds"]),
                use_llm=args.llm,
                llm_command=llm_command,
                jasper_check=args.jasper_check,
                jasper_dry_run=args.jasper_dry_run,
                jasper_out_root=resolve_repo_path(args.jasper_out_root) / variant,
                feedback_mode=str(config["feedback_mode"]),
                prompt_version=str(config["prompt_version"]),
            )
            for case in cases
        ]
        summary = summarize(results)
        systems[variant] = variant_summary(
            variant=variant,
            config=config,
            results=results,
            summary=summary,
            jasper_check=args.jasper_check,
            jasper_dry_run=args.jasper_dry_run,
        )
        all_results.extend({"variant": variant, **result} for result in results)

    candidate_rows = sanitized_candidate_rows(all_results, model_route(args, llm_command))
    error_rows = error_case_rows(all_results)
    payload = {
        "metadata": {
            "created_utc": created_utc,
            "stage": "Stage 4A",
            "git_sha": git_sha,
            "case_count": len(cases),
            "case_set": args.case_set,
            "variant_count": len(args.variants),
            "variants": args.variants,
            "model_route": model_route(args, llm_command),
            "qwen_run": False,
            "benchmark_labels_modified": False,
            "jasper_check_requested": args.jasper_check,
            "jasper_dry_run": args.jasper_dry_run,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "systems": systems,
        "stage3_final_proof_reference": final_proof,
        "results": all_results,
    }

    artifact_meta = None
    if args.candidate_artifact_out:
        artifact_meta = write_candidate_artifact(args.candidate_artifact_out, candidate_rows)
        payload["candidate_artifact"] = artifact_meta

    if args.out:
        write_json(args.out, payload)
    if args.manifest_out:
        manifest = compact_manifest(payload, artifact_meta)
        write_json(args.manifest_out, manifest)
    if args.summary_out:
        write_text(args.summary_out, render_summary(payload, artifact_meta))
    if args.error_cases_out:
        write_text(args.error_cases_out, render_error_cases(payload, error_rows))

    print(
        json.dumps(
            {
                "num_cases": len(cases),
                "systems": {
                    variant: {key: value for key, value in system.items() if key != "rows"}
                    for variant, system in systems.items()
                },
            },
            indent=2,
        )
    )
    return 0


CLAIM_BOUNDARY = (
    "Scaffold success, selected-output Jasper proof, and best-of-candidates proof are separate metrics. "
    "Best-of-k is an upper-bound search metric, not single-output repair success. "
    "New Stage 4A outputs do not claim Jasper proof unless --jasper-check was run on Moore."
)


def build_codex_adapter_command(timeout: int, model: str | None) -> str:
    cmd = [
        sys.executable,
        str(ROOT / "copilot" / "llm_adapters" / "codex_json.py"),
        "--schema",
        str(ROOT / "copilot" / "schemas" / "sva_repair_candidate.schema.json"),
        "--cd",
        str(ROOT),
        "--timeout",
        str(timeout),
    ]
    if model:
        cmd.extend(["--model", model])
    return subprocess.list2cmdline(cmd)


def variant_summary(
    variant: str,
    config: dict[str, object],
    results: list[dict[str, object]],
    summary: dict[str, object],
    jasper_check: bool,
    jasper_dry_run: bool,
) -> dict[str, object]:
    rows = summary.get("rows", [])
    action_rows = repair_action_rows(results)
    fallback_count = int(summary.get("source_counts", {}).get("structured_fallback", 0)) if isinstance(summary.get("source_counts"), dict) else 0
    llm_count = int(summary.get("source_counts", {}).get("llm", 0)) if isinstance(summary.get("source_counts"), dict) else 0
    exact_count = count_rows(rows, "final_exact_match", True)
    scaffold_count = count_rows(rows, "scaffold_success", True)
    hallucinated_count = count_rows(rows, "final_has_hallucinated_signal", True)
    proof_run = bool(jasper_check and not jasper_dry_run)
    return {
        "label": config["label"],
        "description": config["description"],
        "variant": variant,
        "prompt_version": config["prompt_version"],
        "feedback_mode": config["feedback_mode"],
        "max_rounds": config["max_rounds"],
        "case_count": len(results),
        "candidate_count": len(action_rows),
        "valid_json": llm_count,
        "fallback": fallback_count,
        "llm_error_count": int(summary.get("llm_error_count", 0)),
        "hallucinated_signal_count": hallucinated_count,
        "scaffold_repair_success": scaffold_count,
        "exact_template_match": exact_count,
        "scaffold_repair_success_rate": rate_count(scaffold_count, len(results)),
        "exact_template_match_rate": rate_count(exact_count, len(results)),
        "hallucinated_signal_rate": rate_count(hallucinated_count, len(results)),
        "average_rounds_to_success": summary.get("average_rounds_to_success"),
        "case_level_pass_at_1": pass_metric_from_rows(rows, proof_run),
        "case_level_pass_at_k": pass_metric_from_rows(rows, proof_run),
        "final_jasper_proof_run": proof_run,
        "jasper_note": "not_run_moore_handoff_required" if not proof_run else "live_jasper_requested",
        "rows": rows,
    }


def repair_action_rows(results: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        for round_record in result.get("rounds", []):
            if isinstance(round_record, dict) and isinstance(round_record.get("repair_action"), dict):
                rows.append(round_record["repair_action"])
    return rows


def pass_metric_from_rows(rows: object, proof_run: bool) -> dict[str, object]:
    if not proof_run or not isinstance(rows, list):
        return {"count": None, "denominator": len(rows) if isinstance(rows, list) else 0, "status": "not_run"}
    count = sum(
        1
        for row in rows
        if row.get("final_jasper_proof_status") == "proven" and row.get("final_jasper_vacuity_status") != "vacuous"
    )
    return {"count": count, "denominator": len(rows), "status": "measured"}


def count_rows(rows: object, key: str, value: object) -> int:
    if not isinstance(rows, list):
        return 0
    return sum(1 for row in rows if isinstance(row, dict) and row.get(key) == value)


def rate_count(count: int, total: int) -> float:
    return count / total if total else 0.0


def load_final_proof(path: Path) -> dict[str, object]:
    full_path = resolve_repo_path(path)
    if not full_path.exists():
        return {"available": False, "path": str(path)}
    data = json.loads(full_path.read_text())
    return {
        "available": True,
        "path": str(path),
        "run_id": data.get("run_id"),
        "case_ids": sorted(str(case_id) for case_id in data.get("cases", [])),
        "artifact": data.get("artifact"),
        "metrics_layered": data.get("metrics_layered"),
        "claim_boundary": data.get("claim_boundary"),
        "note": "Stage 3D proof metrics apply to restored baseline Codex candidates, not to newly generated Stage 4A variant outputs unless separately checked.",
    }


def filter_cases(
    cases: list[dict[str, object]],
    case_set: str,
    final_proof: dict[str, object],
) -> list[dict[str, object]]:
    if case_set == "all":
        return cases
    case_ids = final_proof.get("case_ids")
    if not isinstance(case_ids, list) or not case_ids:
        return cases
    allowed = {str(case_id) for case_id in case_ids}
    return [case for case in cases if str(case.get("case_id")) in allowed]


def sanitized_candidate_rows(results: list[dict[str, object]], route: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        rounds = result.get("rounds", [])
        final_round = rounds[-1] if isinstance(rounds, list) and rounds else {}
        final_metrics = final_round.get("metrics", {}) if isinstance(final_round, dict) else {}
        rows.append(
            {
                "variant": result.get("variant"),
                "case_id": result.get("case_id"),
                "design_id": result.get("design_id"),
                "property_id": result.get("property_id"),
                "prompt_version": result.get("prompt_version"),
                "feedback_mode": result.get("feedback_mode"),
                "model_route": route,
                "repair_rounds": result.get("repair_rounds"),
                "final_sva": final_round.get("sva") if isinstance(final_round, dict) else None,
                "scaffold_success": result.get("scaffold_success"),
                "final_exact_match": result.get("final_exact_match"),
                "hallucinated_signals": result.get("hallucinated_signals"),
                "jasper_checked": result.get("jasper_checked"),
                "final_jasper_proof_status": final_metrics.get("jasper_proof_status") if isinstance(final_metrics, dict) else None,
                "final_jasper_vacuity_status": final_metrics.get("jasper_vacuity_status") if isinstance(final_metrics, dict) else None,
            }
        )
    return rows


def write_candidate_artifact(path: Path, rows: list[dict[str, object]]) -> dict[str, object]:
    full_path = resolve_repo_path(path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    full_path.write_text(text)
    return {
        "path": str(path),
        "rows": len(rows),
        "bytes": full_path.stat().st_size,
        "sha256": hashlib.sha256(text.encode()).hexdigest().upper(),
        "sanitized": True,
        "raw_prompt_text": False,
        "raw_jasper_logs": False,
    }


def error_case_rows(results: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for result in results:
        if result.get("scaffold_success") is True and not result.get("hallucinated_signals"):
            continue
        rows.append(
            {
                "variant": result.get("variant"),
                "case_id": result.get("case_id"),
                "design_id": result.get("design_id"),
                "bug_type": result.get("bug_type"),
                "final_status": result.get("final_status"),
                "scaffold_success": result.get("scaffold_success"),
                "final_exact_match": result.get("final_exact_match"),
                "hallucinated_signals": result.get("hallucinated_signals"),
                "repair_rounds": result.get("repair_rounds"),
            }
        )
    return rows


def compact_manifest(payload: dict[str, object], artifact_meta: dict[str, object] | None) -> dict[str, object]:
    systems = payload["systems"]
    compact_systems = {
        variant: {key: value for key, value in summary.items() if key != "rows"}
        for variant, summary in systems.items()
    }
    return {
        "metadata": payload["metadata"],
        "systems": compact_systems,
        "stage3_final_proof_reference": payload["stage3_final_proof_reference"],
        "candidate_artifact": artifact_meta,
    }


def render_summary(payload: dict[str, object], artifact_meta: dict[str, object] | None) -> str:
    meta = payload["metadata"]
    lines = [
        "# Stage 4A SVA Repair Ablation Summary",
        "",
        f"Created UTC: {meta['created_utc']}",
        f"Git SHA: `{meta['git_sha']}`",
        "",
        "## Scope",
        "",
        "This report records a controlled SVA repair ablation over the existing 18 repair cases. It does not run Qwen and does not modify benchmark labels.",
        "",
        f"Claim boundary: {meta['claim_boundary']}",
        "",
        "## Variant Results",
        "",
        "| variant | prompt | max rounds | valid JSON | fallback | hallucinated | scaffold success | exact match | pass@1 | pass@k | Jasper proof |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for variant, system in payload["systems"].items():
        lines.append(
            "| {variant} | {prompt} | {rounds} | {valid} | {fallback} | {hallucinated} | {scaffold}/{cases} | {exact}/{cases} | {pass1} | {passk} | {jasper} |".format(
                variant=variant,
                prompt=system["prompt_version"],
                rounds=system["max_rounds"],
                valid=system["valid_json"],
                fallback=system["fallback"],
                hallucinated=system["hallucinated_signal_count"],
                scaffold=system["scaffold_repair_success"],
                exact=system["exact_template_match"],
                cases=system["case_count"],
                pass1=format_pass_metric(system["case_level_pass_at_1"]),
                passk=format_pass_metric(system["case_level_pass_at_k"]),
                jasper=system["jasper_note"],
            )
        )
    lines.extend(
        [
            "",
            "## Stage 3D Formal Reference",
            "",
            "The Stage 3D Moore/JasperGold manifest remains the only live final-proof result for restored Codex repair candidates in this branch.",
        ]
    )
    final_ref = payload.get("stage3_final_proof_reference", {})
    if isinstance(final_ref, dict) and final_ref.get("available"):
        metrics = final_ref.get("metrics_layered", {})
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(metrics, indent=2))
        lines.append("```")
        lines.append("")
        lines.append(str(final_ref.get("note")))
    else:
        lines.append("")
        lines.append("Stage 3D final proof reference was not found.")
    if artifact_meta:
        lines.extend(
            [
                "",
                "## Moore Handoff Artifact",
                "",
                f"- Path: `{artifact_meta['path']}`",
                f"- Rows: {artifact_meta['rows']}",
                f"- SHA256: `{artifact_meta['sha256']}`",
                "- Sanitized: no raw prompt text, no raw Jasper logs.",
            ]
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Best-of-k is reported only as an upper-bound search metric, never as single-output repair success.",
            "- Stage 4A generated candidates require Moore final proof before any new formal-success claim.",
            "- `jasper_vacuity_status == null` in Stage 3D is not an independent explicit non-vacuity certificate.",
            "",
        ]
    )
    return "\n".join(lines)


def render_error_cases(payload: dict[str, object], rows: list[dict[str, object]]) -> str:
    meta = payload["metadata"]
    lines = [
        "# Stage 4A SVA Repair Ablation Error Cases",
        "",
        f"Created UTC: {meta['created_utc']}",
        "",
        "Rows below are cases that did not reach local scaffold success or had hallucinated identifiers. They are not Jasper proof failures unless Jasper was explicitly run.",
        "",
        "| variant | case_id | design | bug_type | final_status | scaffold | exact | hallucinated | rounds |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |",
    ]
    if not rows:
        lines.append("| _none_ | | | | | | | | |")
    for row in rows:
        lines.append(
            "| {variant} | {case_id} | {design_id} | {bug_type} | {final_status} | {scaffold_success} | {final_exact_match} | {hallucinated} | {repair_rounds} |".format(
                hallucinated=", ".join(str(item) for item in row.get("hallucinated_signals") or []),
                **row,
            )
        )
    lines.append("")
    return "\n".join(lines)


def format_pass_metric(metric: object) -> str:
    if not isinstance(metric, dict) or metric.get("status") == "not_run":
        return "not run"
    return f"{metric.get('count')}/{metric.get('denominator')}"


def write_json(path: Path, payload: dict[str, object]) -> None:
    full_path = resolve_repo_path(path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(json.dumps(payload, indent=2) + "\n")


def write_text(path: Path, text: str) -> None:
    full_path = resolve_repo_path(path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(text)


def git_rev_parse(ref: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def model_route(args: argparse.Namespace, llm_command: str | None) -> str:
    if not args.llm:
        return "structured_fallback_no_llm"
    if args.codex_adapter:
        return "codex_cli_json_adapter"
    if llm_command:
        return "configured_llm_command"
    return "llm_requested_but_unconfigured"


if __name__ == "__main__":
    raise SystemExit(main())
