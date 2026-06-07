#!/usr/bin/env python3
"""End-to-end RTL2Repair dry-run/evaluation runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - dependency-minimal local smoke runs.

    class Draft202012Validator:  # type: ignore[no-redef]
        def __init__(self, _schema: dict[str, Any]) -> None:
            pass

        def validate(self, _instance: dict[str, Any]) -> None:
            return None


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copilot.agents.design2sva_agent import (  # noqa: E402
    allowed_signal_set,
    candidate_referenced_signals,
    generate_candidates,
    validate_candidate as validate_design2sva_candidate,
)
from copilot.agents.design2sva_reachability import (  # noqa: E402
    apply_cover_status,
    antecedent_reachable,
    build_antecedent_metadata,
)
from copilot.agents.design2sva_repair_agent import (  # noqa: E402
    repair_design2sva_candidate,
    validate_repair_candidate as validate_design2sva_repair_candidate,
)
from copilot.agents.rtl_repair_agent import (  # noqa: E402
    propose_rtl_repair,
    validate_candidate as validate_rtl_repair_candidate,
)
from copilot.retrieval import Design2SVAContextOptions, build_design2sva_context  # noqa: E402
from copilot.sva_library import hallucinated_identifiers, syntax_scaffold_ok  # noqa: E402
from tools.apply_rtl_patch import apply_rtl_patch  # noqa: E402
from tools.build_patched_manifest import build_patched_manifest  # noqa: E402
from tools.build_formal_debug_bundle import build_formal_debug_bundle  # noqa: E402
from tools.check_generated_sva import check_generated_sva  # noqa: E402
from tools.rtl_patch_safety import PatchSafetyError, diff_touched_paths  # noqa: E402
from tools.rtl_project_intake import create_rtl_project  # noqa: E402


PATCH_RECHECK_SCHEMA = ROOT / "copilot" / "schemas" / "rtl_patch_recheck.schema.json"


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_rtl_repair_replay(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    resolved = resolve_repo_path(path)
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        data = json.loads(stripped)
        if not isinstance(data, dict):
            raise ValueError(f"{resolved}:{line_number} must contain a JSON object.")
        records.append(data)
    return records


def select_rtl_repair_replay_candidate(
    records: list[dict[str, Any]],
    *,
    task: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    if not records:
        return None
    case_id = str(task.get("case_id") or "")
    design_id = str(task.get("design_id") or manifest.get("design_id") or "")
    property_id = str(task.get("property_id") or "")
    for record in records:
        if not replay_record_matches(record, case_id=case_id, design_id=design_id, property_id=property_id):
            continue
        response = record.get("response")
        candidate = response if isinstance(response, dict) else record
        if not isinstance(candidate, dict):
            continue
        validate_rtl_repair_candidate(candidate)
        return candidate
    return None


def replay_record_matches(record: dict[str, Any], *, case_id: str, design_id: str, property_id: str) -> bool:
    if str(record.get("task") or "rtl2repair") != "rtl2repair":
        return False
    for key, expected in (("case_id", case_id), ("design_id", design_id), ("property_id", property_id)):
        value = str(record.get(key) or "")
        if value and value != expected:
            return False
    return True


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
    rtl_patch_stable_sva: dict[str, Any] | None = None
    rtl_patch_target_before: dict[str, Any] | None = None
    rtl_repair_replay_records = load_rtl_repair_replay(args.rtl_repair_replay)
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
            check_result, cover_status = attach_antecedent_reachability(
                args=args,
                task=task,
                candidate=current,
                check_result=check_result,
                manifest_path=manifest_path,
                candidate_index=index,
                round_index=round_index,
                out_path=out_path,
            )
            formal_metrics_status = combine_formal_status(formal_metrics_status, cover_status)
            check_result = attach_candidate_quality(
                task=task,
                context=context,
                candidate=current,
                check_result=check_result,
            )
            bundle = build_formal_debug_bundle(
                check_result=check_result,
                embedding_audit=check_result.get("embedding_audit")
                if isinstance(check_result.get("embedding_audit"), dict)
                else None,
                candidate=current,
            )
            row = candidate_row(task, context, current, check_result, bundle)
            apply_candidate_quality_to_bundle(row, bundle)
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
                    rtl_patch_stable_sva = current
                    rtl_patch_target_before = {
                        "candidate": current,
                        "check_result": check_result,
                        "row": row,
                        "formal_status": check_status,
                    }
                    replay_candidate = select_rtl_repair_replay_candidate(
                        rtl_repair_replay_records,
                        task=task,
                        manifest=manifest,
                    )
                    if replay_candidate is not None:
                        rtl_patch_candidate = replay_candidate
                    else:
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

    patch_recheck = run_patch_recheck(
        args=args,
        manifest=manifest,
        manifest_path=manifest_path,
        task=task,
        rtl_patch_candidate=rtl_patch_candidate,
        stable_sva=rtl_patch_stable_sva,
        target_before=rtl_patch_target_before,
        accepted_properties=accepted_properties,
        out_path=out_path,
    )
    if patch_recheck["status"] == "blocked":
        formal_metrics_status = combine_formal_status(formal_metrics_status, "blocked")
    elif patch_recheck["attempted"]:
        formal_metrics_status = combine_formal_status(formal_metrics_status, "ran" if args.jasper_check and not args.dry_run else "not_run")
    payload = {
        "schema_version": "rtl2repair_eval_v1",
        "rtl_project_manifest": str(manifest_path),
        "task": task,
        "formal_metrics_status": formal_metrics_status,
        "generated_sva_candidates": candidate_records,
        "accepted_properties": accepted_properties,
        "rtl_patch_candidate": rtl_patch_candidate,
        "patch_recheck": patch_recheck,
        "metrics": summarize_metrics(candidate_records, patch_recheck, formal_metrics_status),
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
    system: str | None = None,
) -> tuple[dict[str, Any], str]:
    dry_run = bool(args.dry_run or not args.jasper_check)
    system = system or f"rtl2repair_c{candidate_index}_r{round_index}"
    try:
        result = check_generated_sva(
            case=task,
            prediction=candidate,
            system=system,
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
            "report_dir": str(out_path.parent / "jasper" / system),
            "artifact_paths": {},
        }, "blocked"


def attach_antecedent_reachability(
    *,
    args: argparse.Namespace,
    task: dict[str, Any],
    candidate: dict[str, Any],
    check_result: dict[str, Any],
    manifest_path: Path,
    candidate_index: int,
    round_index: int,
    out_path: Path,
) -> tuple[dict[str, Any], str]:
    updated = dict(check_result)
    property_id = str(candidate.get("property_id") or task.get("property_id") or "generated_property")
    metadata = build_antecedent_metadata(str(candidate.get("sva") or ""), property_id)
    cover_status = "not_run"
    if metadata.get("requires_antecedent_cover") and metadata.get("cover_sva"):
        cover_candidate = {
            "property_id": metadata["cover_property_id"],
            "sva": metadata["cover_sva"],
            "helper_code": "",
            "check_kind": "cover",
        }
        cover_result, cover_status = run_dynamic_check(
            args=args,
            task=task,
            candidate=cover_candidate,
            manifest_path=manifest_path,
            candidate_index=candidate_index,
            round_index=round_index,
            out_path=out_path,
            system=f"rtl2repair_c{candidate_index}_r{round_index}_antecedent_cover",
        )
        metadata = apply_cover_status(metadata, proof_metadata_from_check_result(cover_result))
        updated["antecedent_cover_check"] = cover_result
    updated["antecedent_metadata"] = metadata
    updated["antecedent_reachable"] = antecedent_reachable(metadata)
    updated["cover_reachable"] = antecedent_reachable(metadata)
    return updated, cover_status


def attach_candidate_quality(
    *,
    task: dict[str, Any],
    context: dict[str, Any],
    candidate: dict[str, Any],
    check_result: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(check_result)
    valid_json, validation_error = validate_candidate_json(candidate)
    sva = str(candidate.get("sva") or "")
    helper_code = str(candidate.get("helper_code") or "")
    allowed = sorted(allowed_signal_set(task, context) | {str(candidate.get("property_id") or task.get("property_id") or "")})
    unknown = hallucinated_identifiers(sva, allowed)
    updated["valid_json"] = valid_json
    updated["validation_error"] = validation_error
    updated["unknown_signals"] = unknown
    updated["hallucinated_identifiers"] = unknown
    updated["referenced_signals"] = candidate_referenced_signals(task, context, sva)
    updated["unsupported_helper_code_issue"] = helper_code_disallowed(task, helper_code)
    updated["reset_clock_mismatch"] = reset_clock_mismatch(task, sva)
    return updated


def candidate_row(
    task: dict[str, Any],
    context: dict[str, Any],
    candidate: dict[str, Any],
    check_result: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    syntax_pass = check_result.get("syntax_pass")
    sva = str(candidate.get("sva") or "")
    syntax_ok = syntax_pass is True or (syntax_pass is None and syntax_scaffold_ok(sva))
    if syntax_pass is False:
        syntax_ok = False
    validation_error = str(check_result.get("validation_error") or "")
    hallucinated = [str(item) for item in list_value(check_result.get("hallucinated_identifiers"))]
    antecedent_metadata = check_result.get("antecedent_metadata")
    if not isinstance(antecedent_metadata, dict):
        antecedent_metadata = build_antecedent_metadata(
            sva,
            str(candidate.get("property_id") or task.get("property_id") or "generated_property"),
        )
    proof_metadata = proof_metadata_from_check_result(check_result)
    row = {
        "valid_json": bool(check_result.get("valid_json")),
        "validation_error": validation_error,
        "syntax_ok": syntax_ok,
        "has_hallucinated_signal": bool(hallucinated),
        "unsupported_helper_code_issue": bool(check_result.get("unsupported_helper_code_issue")),
        "reset_clock_mismatch": bool(check_result.get("reset_clock_mismatch"))
        or bool(bundle["root_cause_signals"].get("clock_reset_mismatch")),
        "exact_match": None,
        "antecedent_reachable": antecedent_reachable(antecedent_metadata),
        "cover_reachable": antecedent_reachable(antecedent_metadata),
        "antecedent_metadata": antecedent_metadata,
        "proof_metadata": proof_metadata,
        "failure_category": "not_run",
        "hallucinated_identifiers": hallucinated,
        "referenced_signals": list_value(check_result.get("referenced_signals")),
        "candidate_sva": sva,
        "property_id": candidate.get("property_id") or task.get("property_id"),
        "source": str(candidate.get("source") or "unknown"),
    }
    row["failure_category"] = candidate_failure_category(row, bundle)
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
            or proof_status in {"falsified", "cex", "failed", "fail"} and row.get("antecedent_reachable") is True
        )
    )


def validate_candidate_json(candidate: dict[str, Any]) -> tuple[bool, str]:
    validators = (validate_design2sva_candidate, validate_design2sva_repair_candidate)
    errors: list[str] = []
    for validator in validators:
        try:
            validator(candidate)
            return True, ""
        except Exception as exc:  # noqa: BLE001 - report schema validation detail in row metrics.
            errors.append(str(exc).splitlines()[0])
    return False, " | ".join(error for error in errors if error)


def helper_code_disallowed(task: dict[str, Any], helper_code: str) -> bool:
    policy = task.get("helper_code_policy")
    allowed = bool(policy.get("allowed")) if isinstance(policy, dict) else False
    return bool(helper_code.strip()) and not allowed


def reset_clock_mismatch(task: dict[str, Any], sva: str) -> bool:
    clock_reset = task.get("clock_reset")
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


def proof_metadata_from_check_result(check_result: dict[str, Any]) -> dict[str, Any]:
    syntax_pass = check_result.get("syntax_pass")
    return {
        "proof_status": check_result.get("proof_status"),
        "vacuity_status": check_result.get("vacuity_status"),
        "syntax_status": "passed" if syntax_pass is True else "not_run" if syntax_pass is None else "syntax_error",
        "artifact_paths": check_result.get("artifact_paths", {}),
        "report_dir": check_result.get("report_dir"),
    }


def candidate_failure_category(row: dict[str, Any], bundle: dict[str, Any]) -> str:
    if not row.get("valid_json"):
        return "invalid_json"
    if row.get("has_hallucinated_signal"):
        return "unknown_signal"
    if row.get("unsupported_helper_code_issue"):
        return "unsupported_helper_code"
    if row.get("reset_clock_mismatch"):
        return "reset_clock_mismatch"
    if row.get("syntax_ok") is False:
        return "syntax_error"
    antecedent = row.get("antecedent_metadata")
    if isinstance(antecedent, dict) and antecedent_reachable(antecedent) is False:
        return "unreachable_antecedent"
    return str(bundle.get("repair_recommendation", {}).get("next_owner") or "unknown")


def apply_candidate_quality_to_bundle(row: dict[str, Any], bundle: dict[str, Any]) -> None:
    category = str(row.get("failure_category") or "")
    if category in {
        "invalid_json",
        "unknown_signal",
        "unsupported_helper_code",
        "reset_clock_mismatch",
        "syntax_error",
        "unreachable_antecedent",
    }:
        bundle["repair_recommendation"] = {
            "next_owner": "sva",
            "reason": f"Candidate quality gate failed: {category}.",
        }
    root = bundle.setdefault("root_cause_signals", {})
    if isinstance(root, dict):
        root["unknown_signals"] = row.get("hallucinated_identifiers", [])
        root["clock_reset_mismatch"] = bool(row.get("reset_clock_mismatch"))
        root["antecedent_reachable"] = row.get("antecedent_reachable")


def run_patch_recheck(
    *,
    args: argparse.Namespace,
    manifest: dict[str, Any],
    manifest_path: Path,
    task: dict[str, Any],
    rtl_patch_candidate: dict[str, Any] | None,
    stable_sva: dict[str, Any] | None,
    target_before: dict[str, Any] | None,
    accepted_properties: list[dict[str, Any]],
    out_path: Path,
) -> dict[str, Any]:
    recheck = empty_patch_recheck(rtl_patch_candidate)
    recheck["target_before"] = target_before
    if not rtl_patch_candidate:
        return validate_patch_recheck(recheck)
    if str(rtl_patch_candidate.get("issue_type") or "") != "rtl_design_bug":
        recheck["reason"] = "Patch candidate issue_type is not rtl_design_bug."
        recheck["acceptance_reason"] = recheck["reason"]
        return validate_patch_recheck(recheck)
    if not str(rtl_patch_candidate.get("unified_diff") or "").strip():
        recheck["reason"] = "Patch candidate has no unified diff."
        recheck["acceptance_reason"] = recheck["reason"]
        return validate_patch_recheck(recheck)
    if stable_sva is None:
        recheck["status"] = "blocked"
        recheck["attempted"] = True
        recheck["reason"] = "No stable falsified SVA was available for target recheck."
        recheck["acceptance_reason"] = recheck["reason"]
        return validate_patch_recheck(recheck)

    recheck["attempted"] = True
    unified_diff = str(rtl_patch_candidate["unified_diff"])
    allowed_files = [resolve_repo_path(Path(path)) for path in manifest.get("rtl_files", [])]
    try:
        patch_repo_root = infer_patch_repo_root(allowed_files, unified_diff)
        apply_manifest = apply_rtl_patch(
            unified_diff=unified_diff,
            allowed_patch_files=allowed_files,
            scratch_dir=out_path.parent / "patched_rtl",
            repo_root=patch_repo_root,
            out_path=out_path.parent / "patched_rtl" / "applied_patch_manifest.json",
        )
        patched_manifest_path = out_path.parent / "patched_rtl_project_manifest.json"
        build_patched_manifest(
            original_manifest=manifest,
            applied_patch_manifest=apply_manifest,
            out_path=patched_manifest_path,
        )
    except (PatchSafetyError, ValueError, OSError) as exc:
        recheck["status"] = "blocked"
        recheck["reason"] = str(exc)
        recheck["acceptance_reason"] = recheck["reason"]
        return validate_patch_recheck(recheck)

    recheck["status"] = "applied"
    recheck["apply_manifest"] = apply_manifest
    recheck["patched_manifest"] = str(patched_manifest_path)

    target_check, target_status = run_dynamic_check(
        args=args,
        task=task,
        candidate=stable_sva,
        manifest_path=patched_manifest_path,
        candidate_index=0,
        round_index=0,
        out_path=out_path,
        system="rtl2repair_patch_target",
    )
    recheck["target_check"] = {
        "candidate": stable_sva,
        "check_result": target_check,
        "formal_status": target_status,
        "pass": target_property_passes(target_check),
    }
    recheck["target_after"] = recheck["target_check"]

    regression_checks = []
    for regression_index, regression in enumerate(accepted_properties):
        regression_result, regression_status = run_dynamic_check(
            args=args,
            task=task,
            candidate=regression,
            manifest_path=patched_manifest_path,
            candidate_index=regression_index,
            round_index=0,
            out_path=out_path,
            system=f"rtl2repair_patch_regression_{regression_index}",
        )
        regression_checks.append(
            {
                "candidate": regression,
                "check_result": regression_result,
                "formal_status": regression_status,
                "pass": target_property_passes(regression_result),
            }
        )
    recheck["regression_checks"] = regression_checks
    target_before_pass = target_before_is_falsified_reachable(target_before)
    target_pass = bool(recheck["target_after"]["pass"])
    regression_pass_count = sum(1 for item in regression_checks if item.get("pass"))
    regression_total = len(regression_checks)
    regression_pass_rate = 1.0 if regression_total == 0 else rate(regression_pass_count, regression_total)
    recheck["metrics"] = {
        "target_pass": target_pass,
        "regression_pass_count": regression_pass_count,
        "regression_total": regression_total,
        "regression_pass_rate": regression_pass_rate,
    }
    recheck["accepted"] = target_before_pass and target_pass and regression_pass_count == regression_total
    recheck["status"] = "accepted" if recheck["accepted"] else "rejected"
    recheck["acceptance_reason"] = (
        "Patch passed target and regression rechecks."
        if recheck["accepted"]
        else patch_rejection_reason(
            target_before_pass=target_before_pass,
            target_after_pass=target_pass,
            regression_pass_count=regression_pass_count,
            regression_total=regression_total,
        )
    )
    recheck["reason"] = recheck["acceptance_reason"]
    return validate_patch_recheck(recheck)


def empty_patch_recheck(rtl_patch_candidate: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "schema_version": "rtl_patch_recheck_v1",
        "status": "not_attempted",
        "attempted": False,
        "accepted": False,
        "reason": "No RTL patch candidate was produced.",
        "acceptance_reason": "No RTL patch candidate was produced.",
        "rtl_patch_candidate": rtl_patch_candidate,
        "apply_manifest": None,
        "patched_manifest": None,
        "target_before": None,
        "target_after": None,
        "target_check": None,
        "regression_checks": [],
        "metrics": {
            "target_pass": False,
            "regression_pass_count": 0,
            "regression_total": 0,
            "regression_pass_rate": 0.0,
        },
    }


def validate_patch_recheck(recheck: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads(PATCH_RECHECK_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(recheck)
    return recheck


def infer_patch_repo_root(allowed_files: list[Path], unified_diff: str) -> Path:
    touched = diff_touched_paths(unified_diff)
    allowed_resolved = {path.resolve() for path in allowed_files}
    for candidate in [ROOT, *candidate_roots_from_touched_paths(allowed_resolved, touched)]:
        root = candidate.resolve()
        try:
            if all((root / touched_path).resolve() in allowed_resolved for touched_path in touched):
                return root
        except OSError:
            continue
    return ROOT


def candidate_roots_from_touched_paths(allowed_files: set[Path], touched: list[str]) -> list[Path]:
    roots: list[Path] = []
    for file_path in allowed_files:
        for touched_path in touched:
            parts = Path(touched_path).parts
            root = file_path
            for _ in parts:
                root = root.parent
            if root not in roots:
                roots.append(root)
    return roots


def target_property_passes(check_result: dict[str, Any]) -> bool:
    proof_status = str(check_result.get("proof_status") or "").lower()
    vacuity_status = str(check_result.get("vacuity_status") or "").lower()
    syntax_pass = check_result.get("syntax_pass")
    return syntax_pass is not False and proof_status == "proven" and vacuity_status != "vacuous"


def target_before_is_falsified_reachable(target_before: dict[str, Any] | None) -> bool:
    if not isinstance(target_before, dict):
        return False
    row = target_before.get("row")
    if isinstance(row, dict):
        proof = row.get("proof_metadata") if isinstance(row.get("proof_metadata"), dict) else {}
        proof_status = str(proof.get("proof_status") or "").lower()
        return proof_status in {"falsified", "cex", "failed", "fail"} and row.get("antecedent_reachable") is True
    check_result = target_before.get("check_result")
    if isinstance(check_result, dict):
        proof_status = str(check_result.get("proof_status") or "").lower()
        return proof_status in {"falsified", "cex", "failed", "fail"} and check_result.get("antecedent_reachable") is True
    return False


def patch_rejection_reason(
    *,
    target_before_pass: bool,
    target_after_pass: bool,
    regression_pass_count: int,
    regression_total: int,
) -> str:
    if not target_before_pass:
        return "Target before state was not a reachable falsified property."
    if not target_after_pass:
        return "Target after recheck was not proven non-vacuous."
    if regression_pass_count != regression_total:
        return "One or more regression rechecks failed."
    return "Patch failed target or regression recheck."


def combine_formal_status(current: str, observed: str) -> str:
    order = {"not_run": 0, "ran": 1, "blocked": 2}
    return observed if order.get(observed, 0) > order.get(current, 0) else current


def summarize_metrics(
    candidate_records: list[dict[str, Any]],
    patch_recheck: dict[str, Any],
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
            in {"falsified", "cex", "failed", "fail"}
            and row.get("antecedent_reachable") is True
        ),
        "rtl_patch_attempt_count": 1 if patch_recheck.get("attempted") else 0,
        "rtl_patch_accept_count": 1 if patch_recheck.get("accepted") else 0,
        "regression_pass_rate": float(
            (patch_recheck.get("metrics") or {}).get("regression_pass_rate", 0.0)
        ),
        "fallback_rate": 0.0,
        "formal_metrics_status": formal_metrics_status,
    }


def rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


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
        f"- RTL patch accepted: `{metrics['rtl_patch_accept_count']}`",
        f"- Patch recheck status: `{payload['patch_recheck']['status']}`",
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
    parser.add_argument("--rtl-repair-replay", type=Path)
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
