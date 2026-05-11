"""Manifest-driven Stage 5D workflow orchestration."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator
from pydantic import Field

from app.alignment.intent_alignment import (
    IntentAlignmentCase,
    evaluate_intent_alignment,
)
from app.core.artifacts import make_run_id, sha256_bytes, short_hash
from app.local_llm_backend import (
    LOCAL_WORKFLOW_CLAIM_BOUNDARY,
    LocalBackendResult,
    call_local_task,
    gpu_snapshot,
    local_backend_config,
    local_execution_blocker,
    local_execution_requested,
    local_only_effective,
)
from app.models.core import (
    Candidate,
    CoreModel,
    Language,
    ProblemSpec,
    ToolName,
)
from copilot.agents.coverage_closure_agent import structured_fallback as coverage_fallback
from copilot.agents.coverage_closure_agent import build_prompt as build_coverage_prompt
from copilot.agents.dv_triage_agent import structured_fallback as triage_fallback
from copilot.agents.dv_triage_agent import build_prompt as build_triage_prompt
from copilot.agents.sva_repair_agent import structured_fallback as repair_fallback
from copilot.agents.sva_repair_agent import build_prompt as build_repair_prompt
from tools.build_evidence_packet import build_packet

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_CLAIM_BOUNDARY = (
    "Stage 5F workflow evidence is a manifest-driven orchestration record. "
    "Dry-runs chain existing local CLI capabilities and static heuristics only. "
    "The local backend path is LOCAL_ONLY, never calls cloud fallback, and does not "
    "call JasperGold, Moore, run full benchmarks, compare Qwen with Codex, change Stage 4 "
    "reports, benchmark labels, schemas, or prior claims."
)

REPAIR_DEFAULT_CASE_ID = "repair_arbiter_mutex_syntax"
TRIAGE_DEFAULT_CASE_ID = "arbiter_A1"
COVERAGE_DEFAULT_CASE_ID = "apb_C10"

WORKFLOW_TYPES = ("repair", "triage", "coverage", "demo")
BACKENDS = ("replay", "codex", "local")


class WorkflowManifest(CoreModel):
    """Top-level ledger for one Stage 5D workflow dry-run."""

    manifest_type: Literal["WorkflowManifest"] = "WorkflowManifest"
    schema_version: Literal["stage5d.workflow.v1"] = "stage5d.workflow.v1"
    workflow_id: str = Field(min_length=1)
    workflow_type: Literal["repair", "triage", "coverage", "demo"]
    git_sha: str = Field(min_length=7)
    timestamp: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    backend: Literal["replay", "codex", "local"]
    status: Literal["dry_run", "ok", "blocked", "local_unavailable", "local_error", "invalid_json", "schema_invalid"]
    external_send_allowed: bool
    local_only: bool
    model_id: str | None = None
    endpoint_url: str | None = None
    backend_type: Literal["vllm", "sglang", "ollama", "unknown"] | None = None
    LOCAL_ONLY: bool
    cloud_fallback_allowed: bool = False
    cloud_fallback_called: bool = False
    max_model_len: int | None = None
    gpu_name: str | None = None
    gpu_vram_gb: float | None = None
    task_type: Literal["repair", "triage", "coverage", "demo"]
    case_count: int = 1
    valid_json: bool | None = None
    fallback_count: int = 0
    llm_error_count: int = 0
    latency_ms: float | None = None
    steps_planned: list[str]
    steps_executed: list[str]
    artifact_refs: list[dict[str, Any]]
    verifier_required: bool
    verifier_outcome_ref: str | None = None
    intent_alignment_ref: str | None = None
    final_report_ref: str | None = None
    claim_boundary: str = Field(min_length=1)
    dry_run: bool = True
    blocked_reason: str | None = None


def add_workflow_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    workflow = subparsers.add_parser(
        "workflow",
        description="Run safe Stage 5D manifest-driven JasperLoop workflows.",
        help="Run safe Stage 5D manifest-driven JasperLoop workflows.",
    )
    workflow_subparsers = workflow.add_subparsers(dest="workflow_action", required=True)
    for name in WORKFLOW_TYPES:
        parser = workflow_subparsers.add_parser(
            name,
            description=f"Run the Stage 5D {name} workflow.",
            help=f"Run the Stage 5D {name} workflow.",
        )
        add_common_workflow_options(parser, name)


def add_common_workflow_options(parser: argparse.ArgumentParser, name: str) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Emit workflow artifacts without external model, JasperGold, Moore, or network calls.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts") / "workflow" / name,
        help="Directory for workflow artifacts.",
    )
    parser.add_argument("--case-id", help="Case identifier to load from benchmark metadata.")
    parser.add_argument("--case", help="Case identifier or path to a case/evidence-packet JSON file.")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="replay",
        help="Route to plan. Codex is external and requires explicit acknowledgement.",
    )
    parser.add_argument(
        "--require-explicit-external-send",
        action="store_true",
        help="Acknowledge that an external backend route may be planned. Dry-run still sends nothing.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Require LOCAL_ONLY behavior for backend=local executable runs.",
    )
    parser.add_argument(
        "--acknowledge-local-model-run",
        action="store_true",
        help="Explicitly acknowledge a bounded local model call. Cloud fallback remains disabled.",
    )
    parser.add_argument(
        "--run-local-model",
        action="store_true",
        help="For backend=local, run exactly the selected single case after LOCAL_ONLY acknowledgement.",
    )
    parser.add_argument(
        "--run-local-subset",
        action="store_true",
        help="For workflow demo with backend=local, run only the 3 repair + 3 triage + 3 coverage subset.",
    )
    parser.add_argument("--local-base-url", default=None, help="OpenAI-compatible local base URL.")
    parser.add_argument("--local-api-key", default=None, help="Local endpoint API key, if required.")
    parser.add_argument("--local-model", default=None, help="Served local model id.")
    parser.add_argument(
        "--local-backend-type",
        choices=("vllm", "sglang", "ollama", "unknown"),
        default=None,
        help="Local serving backend profile.",
    )
    parser.add_argument("--local-timeout-s", type=int, default=None, help="Local endpoint timeout.")
    parser.add_argument("--local-max-tokens", type=int, default=None, help="Local response token budget.")
    parser.add_argument("--local-temperature", type=float, default=None, help="Local sampling temperature.")
    parser.add_argument("--local-max-model-len", type=int, default=None, help="Served max model length.")
    parser.add_argument(
        "--local-no-response-format",
        action="store_true",
        help="Do not request OpenAI JSON response_format from the local endpoint.",
    )
    parser.add_argument(
        "--prepare-moore-handoff",
        action="store_true",
        help="Prepare a local Moore handoff manifest only; do not run Moore or JasperGold.",
    )
    parser.add_argument(
        "--run-intent-alignment",
        action="store_true",
        help="Run the static local intent-alignment evaluator when candidate/reference/intent are present.",
    )
    parser.add_argument("--manifest-out", type=Path, help="Explicit path for WorkflowManifest JSON.")
    parser.add_argument(
        "--verifier-result",
        type=Path,
        help="Optional existing verifier outcome/summary JSON to import as workflow context.",
    )


def run_workflow_command(args: argparse.Namespace, argv: list[str]) -> int:
    workflow_type = str(args.workflow_action)
    if workflow_type == "repair":
        return run_repair_workflow(args, argv)
    if workflow_type == "triage":
        return run_packet_workflow(args, argv, workflow_type="triage")
    if workflow_type == "coverage":
        return run_packet_workflow(args, argv, workflow_type="coverage")
    if workflow_type == "demo":
        return run_demo_workflow(args, argv)
    raise ValueError(f"unsupported workflow action: {workflow_type}")


def run_repair_workflow(args: argparse.Namespace, argv: list[str]) -> int:
    created_at = datetime.now(timezone.utc)
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    case, case_path = load_repair_case(args.case_id, args.case)
    case_id = str(case["case_id"])
    workflow_id = workflow_id_for("repair", case_id, created_at)
    steps_planned = [
        "load_repair_case_metadata",
        "prepare_problem_spec_stub",
        "choose_backend_route",
        "prepare_candidate_stub_or_replay_candidate",
        "prepare_moore_handoff_manifest_if_requested",
        "import_verifier_outcome_if_available",
        "run_intent_alignment_if_requested_and_available",
        "emit_final_workflow_report",
        "emit_workflow_manifest",
    ]
    artifact_refs: list[dict[str, Any]] = []
    steps_executed: list[str] = []
    blocked_reason = external_backend_blocker(args)

    if blocked_reason:
        steps_executed.append("block_external_backend_without_acknowledgement")
        report_path = out_dir / "workflow_report.md"
        write_text(report_path, final_report("repair", case_id, args.backend, blocked_reason, []))
        artifact_refs.append(artifact_ref("final_report", report_path))
        manifest = build_manifest(
            args=args,
            workflow_id=workflow_id,
            workflow_type="repair",
            created_at=created_at,
            case_id=case_id,
            steps_planned=steps_planned,
            steps_executed=steps_executed,
            artifact_refs=artifact_refs,
            final_report_ref=str(report_path),
            blocked_reason=blocked_reason,
        )
        manifest_path = write_manifest(args, out_dir, manifest)
        print_workflow_result(manifest_path, report_path, blocked=True, dry_run=True)
        return 2

    steps_executed.append("load_repair_case_metadata")
    problem = problem_spec_stub(workflow_id, case, case_path)
    problem_path = out_dir / "problem_spec_stub.json"
    write_json(problem_path, problem.model_dump(mode="json"))
    artifact_refs.append(artifact_ref("problem_spec_stub", problem_path))
    steps_executed.append("prepare_problem_spec_stub")
    steps_executed.append("choose_backend_route")

    local_result = None
    if args.backend == "local" and local_execution_requested(args):
        local_result = call_local_task(
            config=local_backend_config(args),
            task_type="repair",
            prompt=build_repair_prompt(case, str(case.get("broken_sva", ""))),
            context=case,
            schema_path=resolve_path(Path("copilot/schemas/sva_repair_candidate.schema.json")),
        )
        if local_result.status != "ok":
            return write_blocked_local_workflow(
                args=args,
                out_dir=out_dir,
                workflow_id=workflow_id,
                workflow_type="repair",
                created_at=created_at,
                case_id=case_id,
                steps_planned=steps_planned,
                steps_executed=[*steps_executed, local_failure_step(local_result)],
                artifact_refs=artifact_refs,
                local_result=local_result,
                case_count=1,
            )
        candidate_payload = local_result.output if local_result.output is not None else repair_candidate_for_backend(case, args.backend)
    else:
        candidate_payload = repair_candidate_for_backend(case, args.backend, case_path)
    candidate_path = out_dir / "repair_candidate.json"
    write_json(candidate_path, strip_extra(candidate_payload, "copilot/schemas/sva_repair_candidate.schema.json"))
    artifact_refs.append(artifact_ref("repair_candidate", candidate_path))
    candidate_stub = candidate_core_stub(workflow_id, problem.problem_id, candidate_payload, args.backend)
    candidate_stub_path = out_dir / "candidate_stub.json"
    write_json(candidate_stub_path, candidate_stub.model_dump(mode="json"))
    artifact_refs.append(artifact_ref("candidate_stub", candidate_stub_path))
    steps_executed.append("prepare_candidate_stub_or_replay_candidate")

    verifier_ref = None
    if args.prepare_moore_handoff:
        handoff_path = write_moore_handoff_manifest(out_dir, "codex-repair-final-proof")
        artifact_refs.append(artifact_ref("moore_handoff_manifest", handoff_path))
        steps_executed.append("prepare_moore_handoff_manifest_if_requested")

    verifier_result_path = args.verifier_result or verifier_result_path_from_case(case, case_path)
    verifier_payload = load_optional_json(verifier_result_path)
    if verifier_payload is not None and verifier_result_path is not None:
        verifier_path = out_dir / "imported_verifier_outcome.json"
        write_json(verifier_path, verifier_payload)
        artifact_refs.append(artifact_ref("imported_verifier_outcome", verifier_path))
        verifier_ref = str(verifier_path)
        steps_executed.append("import_verifier_outcome_if_available")

    alignment_ref = None
    if args.run_intent_alignment and can_align(case, candidate_payload):
        alignment_result = evaluate_intent_alignment(
            IntentAlignmentCase(
                case_id=case_id,
                property_id=as_optional_str(case.get("property_id")),
                intent_summary=str(case.get("intent") or case.get("property_intent")),
                candidate_sva=str(candidate_payload["sva"]),
                reference_sva=as_optional_str(case.get("reference_sva")),
                allowed_signals=[str(item) for item in case.get("signals", [])],
                required_signals=[str(item) for item in case.get("signals", [])],
                proof_status_context=verifier_payload if isinstance(verifier_payload, dict) else None,
                evidence_refs=[
                    str(candidate_path),
                    *(str(verifier_result_path) for _ in [0] if verifier_result_path),
                ],
            )
        )
        alignment_path = out_dir / "intent_alignment_result.json"
        write_json(alignment_path, alignment_result.model_dump(mode="json"))
        artifact_refs.append(artifact_ref("intent_alignment_result", alignment_path))
        alignment_ref = str(alignment_path)
        steps_executed.append("run_intent_alignment_if_requested_and_available")

    report_path = out_dir / "workflow_report.md"
    write_text(
        report_path,
        final_report(
            "repair",
            case_id,
            args.backend,
            None,
            steps_executed,
            verifier_ref=verifier_ref,
            alignment_ref=alignment_ref,
        ),
    )
    artifact_refs.append(artifact_ref("final_report", report_path))
    steps_executed.append("emit_final_workflow_report")
    manifest = build_manifest(
        args=args,
        workflow_id=workflow_id,
        workflow_type="repair",
        created_at=created_at,
        case_id=case_id,
        steps_planned=steps_planned,
        steps_executed=[*steps_executed, "emit_workflow_manifest"],
        artifact_refs=artifact_refs,
        verifier_outcome_ref=verifier_ref,
        intent_alignment_ref=alignment_ref,
        final_report_ref=str(report_path),
        local_result=local_result,
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    print_workflow_result(manifest_path, report_path, blocked=False, dry_run=manifest.dry_run)
    return 0


def run_packet_workflow(args: argparse.Namespace, argv: list[str], *, workflow_type: Literal["triage", "coverage"]) -> int:
    del argv
    created_at = datetime.now(timezone.utc)
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    default_case = TRIAGE_DEFAULT_CASE_ID if workflow_type == "triage" else COVERAGE_DEFAULT_CASE_ID
    packet, case_id = load_packet_context(args.case_id, args.case, default_case)
    workflow_id = workflow_id_for(workflow_type, case_id, created_at)
    steps_planned = [
        "load_evidence_packet_or_minimal_packet" if workflow_type == "triage" else "load_coverage_context",
        "choose_backend_route",
        "emit_diagnosis_candidate" if workflow_type == "triage" else "emit_closure_recommendation",
        "validate_schema",
        "prepare_moore_handoff_manifest_if_requested",
        "import_verifier_outcome_if_available",
        f"emit_human_reviewable_{workflow_type}_report",
        "emit_workflow_manifest",
    ]
    artifact_refs: list[dict[str, Any]] = []
    steps_executed: list[str] = []
    blocked_reason = external_backend_blocker(args)

    if blocked_reason:
        steps_executed.append("block_external_backend_without_acknowledgement")
        report_path = out_dir / "workflow_report.md"
        write_text(report_path, final_report(workflow_type, case_id, args.backend, blocked_reason, []))
        artifact_refs.append(artifact_ref("final_report", report_path))
        manifest = build_manifest(
            args=args,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            created_at=created_at,
            case_id=case_id,
            steps_planned=steps_planned,
            steps_executed=steps_executed,
            artifact_refs=artifact_refs,
            final_report_ref=str(report_path),
            blocked_reason=blocked_reason,
        )
        manifest_path = write_manifest(args, out_dir, manifest)
        print_workflow_result(manifest_path, report_path, blocked=True, dry_run=True)
        return 2

    packet_path = out_dir / "evidence_packet.json"
    write_json(packet_path, packet)
    artifact_refs.append(artifact_ref("evidence_packet", packet_path))
    steps_executed.append("load_evidence_packet_or_minimal_packet" if workflow_type == "triage" else "load_coverage_context")
    steps_executed.append("choose_backend_route")

    local_result = None
    if workflow_type == "triage":
        schema_path = "copilot/schemas/diagnosis_output.schema.json"
        candidate_name = "diagnosis_candidate"
        candidate_step = "emit_diagnosis_candidate"
        if args.backend == "local" and local_execution_requested(args):
            local_result = call_local_task(
                config=local_backend_config(args),
                task_type="triage",
                prompt=build_triage_prompt(packet),
                context=packet,
                schema_path=resolve_path(Path(schema_path)),
            )
            if local_result.status != "ok":
                return write_blocked_local_workflow(
                    args=args,
                    out_dir=out_dir,
                    workflow_id=workflow_id,
                    workflow_type=workflow_type,
                    created_at=created_at,
                    case_id=case_id,
                    steps_planned=steps_planned,
                    steps_executed=[*steps_executed, local_failure_step(local_result)],
                    artifact_refs=artifact_refs,
                    local_result=local_result,
                    case_count=1,
                )
            raw_candidate = local_result.output if local_result.output is not None else triage_fallback(packet)
        else:
            raw_candidate = triage_fallback(packet)
    else:
        schema_path = "copilot/schemas/coverage_closure_output.schema.json"
        candidate_name = "coverage_recommendation"
        candidate_step = "emit_closure_recommendation"
        if args.backend == "local" and local_execution_requested(args):
            local_result = call_local_task(
                config=local_backend_config(args),
                task_type="coverage",
                prompt=build_coverage_prompt(packet),
                context=packet,
                schema_path=resolve_path(Path(schema_path)),
            )
            if local_result.status != "ok":
                return write_blocked_local_workflow(
                    args=args,
                    out_dir=out_dir,
                    workflow_id=workflow_id,
                    workflow_type=workflow_type,
                    created_at=created_at,
                    case_id=case_id,
                    steps_planned=steps_planned,
                    steps_executed=[*steps_executed, local_failure_step(local_result)],
                    artifact_refs=artifact_refs,
                    local_result=local_result,
                    case_count=1,
                )
            raw_candidate = local_result.output if local_result.output is not None else coverage_fallback(packet)
        else:
            raw_candidate = coverage_fallback(packet)

    candidate = strip_extra(raw_candidate, schema_path)
    candidate_path = out_dir / f"{candidate_name}.json"
    write_json(candidate_path, candidate)
    artifact_refs.append(artifact_ref(candidate_name, candidate_path))
    steps_executed.append(candidate_step)
    validate_against_schema(candidate, resolve_path(Path(schema_path)))
    steps_executed.append("validate_schema")

    verifier_ref = None
    if args.prepare_moore_handoff:
        handoff_path = write_moore_handoff_manifest(out_dir, "evidence-packets")
        artifact_refs.append(artifact_ref("moore_handoff_manifest", handoff_path))
        steps_executed.append("prepare_moore_handoff_manifest_if_requested")

    verifier_payload = load_optional_json(args.verifier_result)
    if verifier_payload is not None and args.verifier_result is not None:
        verifier_path = out_dir / "imported_verifier_outcome.json"
        write_json(verifier_path, verifier_payload)
        artifact_refs.append(artifact_ref("imported_verifier_outcome", verifier_path))
        verifier_ref = str(verifier_path)
        steps_executed.append("import_verifier_outcome_if_available")

    report_path = out_dir / "workflow_report.md"
    write_text(
        report_path,
        final_report(
            workflow_type,
            case_id,
            args.backend,
            None,
            steps_executed,
            verifier_ref=verifier_ref,
        ),
    )
    artifact_refs.append(artifact_ref("final_report", report_path))
    steps_executed.append(f"emit_human_reviewable_{workflow_type}_report")
    manifest = build_manifest(
        args=args,
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        created_at=created_at,
        case_id=case_id,
        steps_planned=steps_planned,
        steps_executed=[*steps_executed, "emit_workflow_manifest"],
        artifact_refs=artifact_refs,
        verifier_outcome_ref=verifier_ref,
        final_report_ref=str(report_path),
        local_result=local_result,
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    print_workflow_result(manifest_path, report_path, blocked=False, dry_run=manifest.dry_run)
    return 0


def run_demo_workflow(args: argparse.Namespace, argv: list[str]) -> int:
    del argv
    created_at = datetime.now(timezone.utc)
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    case_id = args.case_id or args.case or REPAIR_DEFAULT_CASE_ID
    workflow_id = workflow_id_for("demo", str(case_id), created_at)
    steps_planned = [
        "plan_repair_workflow",
        "plan_triage_workflow",
        "plan_coverage_workflow",
        "emit_final_workflow_report",
        "emit_workflow_manifest",
    ]
    blocked_reason = external_backend_blocker(args)
    local_result = None
    subset_artifact_refs: list[dict[str, Any]] = []
    steps_executed = (
        ["block_external_backend_without_acknowledgement"]
        if blocked_reason
        else ["plan_repair_workflow", "plan_triage_workflow", "plan_coverage_workflow", "emit_final_workflow_report"]
    )
    if not blocked_reason and args.backend == "local" and args.run_local_subset:
        subset = run_local_demo_subset(args, out_dir)
        local_result = subset["aggregate_result"]
        subset_artifact_refs = subset["artifact_refs"]
        if local_result.status != "ok":
            return write_blocked_local_workflow(
                args=args,
                out_dir=out_dir,
                workflow_id=workflow_id,
                workflow_type="demo",
                created_at=created_at,
                case_id=str(case_id),
                steps_planned=steps_planned,
                steps_executed=[*subset["steps_executed"], local_failure_step(local_result)],
                artifact_refs=subset_artifact_refs,
                local_result=local_result,
                case_count=9,
            )
        steps_executed = [*subset["steps_executed"], "emit_final_workflow_report"]
    report_path = out_dir / "workflow_report.md"
    write_text(report_path, final_report("demo", str(case_id), args.backend, blocked_reason, steps_executed))
    artifact_refs = [*subset_artifact_refs, artifact_ref("final_report", report_path)]
    manifest = build_manifest(
        args=args,
        workflow_id=workflow_id,
        workflow_type="demo",
        created_at=created_at,
        case_id=str(case_id),
        steps_planned=steps_planned,
        steps_executed=[*steps_executed, "emit_workflow_manifest"] if not blocked_reason else steps_executed,
        artifact_refs=artifact_refs,
        final_report_ref=str(report_path),
        blocked_reason=blocked_reason,
        case_count=9 if args.backend == "local" and args.run_local_subset else 1,
        local_result=local_result,
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    if args.backend == "local" and args.run_local_subset and not blocked_reason:
        write_qwen_workflow_readiness_report(manifest.model_dump(mode="json"), blocked=False)
    print_workflow_result(manifest_path, report_path, blocked=bool(blocked_reason), dry_run=manifest.dry_run)
    return 2 if blocked_reason else 0


def write_blocked_local_workflow(
    *,
    args: argparse.Namespace,
    out_dir: Path,
    workflow_id: str,
    workflow_type: Literal["repair", "triage", "coverage", "demo"],
    created_at: datetime,
    case_id: str,
    steps_planned: list[str],
    steps_executed: list[str],
    artifact_refs: list[dict[str, Any]],
    local_result: LocalBackendResult,
    case_count: int,
) -> int:
    report_path = out_dir / "workflow_report.md"
    write_text(report_path, final_report(workflow_type, case_id, "local", "local_unavailable", steps_executed))
    artifact_refs = [*artifact_refs, artifact_ref("final_report", report_path)]
    manifest = build_manifest(
        args=args,
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        created_at=created_at,
        case_id=case_id,
        steps_planned=steps_planned,
        steps_executed=steps_executed,
        artifact_refs=artifact_refs,
        final_report_ref=str(report_path),
        blocked_reason=local_result.status,
        case_count=case_count,
        local_result=local_result,
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    write_qwen_workflow_readiness_report(manifest.model_dump(mode="json"), blocked=True)
    print_workflow_result(manifest_path, report_path, blocked=True, dry_run=manifest.dry_run)
    return 2


def local_failure_step(local_result: LocalBackendResult) -> str:
    return {
        "local_unavailable": "local_endpoint_unavailable",
        "invalid_json": "local_response_invalid_json",
        "schema_invalid": "local_response_schema_invalid",
        "local_error": "local_endpoint_error",
        "ok": "local_response_ok",
    }[local_result.status]


def run_local_demo_subset(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    config = local_backend_config(args)
    subset_dir = out_dir / "local_subset"
    subset_dir.mkdir(parents=True, exist_ok=True)
    artifact_refs: list[dict[str, Any]] = []
    steps_executed: list[str] = []
    results: list[LocalBackendResult] = []

    for index, case in enumerate(load_repair_subset(3), start=1):
        case_id = str(case.get("case_id", f"repair_{index}"))
        result = call_local_task(
            config=config,
            task_type="repair",
            prompt=build_repair_prompt(case, str(case.get("broken_sva", ""))),
            context=case,
            schema_path=resolve_path(Path("copilot/schemas/sva_repair_candidate.schema.json")),
        )
        results.append(result)
        if result.status != "ok":
            break
        payload = result.output if result.output is not None else repair_candidate_for_backend(case, "local")
        path = subset_dir / f"repair_{index}_{safe_filename(case_id)}.json"
        write_json(path, strip_extra(payload, "copilot/schemas/sva_repair_candidate.schema.json"))
        artifact_refs.append(artifact_ref("local_subset_repair", path))
        steps_executed.append("run_local_subset_repair_case")

    if results and results[-1].status != "ok":
        return local_subset_summary(artifact_refs, steps_executed, results)

    for index, packet in enumerate(load_packet_subset("triage", 3), start=1):
        case_id = str(packet.get("case_id", f"triage_{index}"))
        result = call_local_task(
            config=config,
            task_type="triage",
            prompt=build_triage_prompt(packet),
            context=packet,
            schema_path=resolve_path(Path("copilot/schemas/diagnosis_output.schema.json")),
        )
        results.append(result)
        if result.status != "ok":
            break
        payload = result.output if result.output is not None else triage_fallback(packet)
        path = subset_dir / f"triage_{index}_{safe_filename(case_id)}.json"
        write_json(path, strip_extra(payload, "copilot/schemas/diagnosis_output.schema.json"))
        artifact_refs.append(artifact_ref("local_subset_triage", path))
        steps_executed.append("run_local_subset_triage_case")

    if results and results[-1].status != "ok":
        return local_subset_summary(artifact_refs, steps_executed, results)

    for index, packet in enumerate(load_packet_subset("coverage", 3), start=1):
        case_id = str(packet.get("case_id", f"coverage_{index}"))
        result = call_local_task(
            config=config,
            task_type="coverage",
            prompt=build_coverage_prompt(packet),
            context=packet,
            schema_path=resolve_path(Path("copilot/schemas/coverage_closure_output.schema.json")),
        )
        results.append(result)
        if result.status != "ok":
            break
        payload = result.output if result.output is not None else coverage_fallback(packet)
        path = subset_dir / f"coverage_{index}_{safe_filename(case_id)}.json"
        write_json(path, strip_extra(payload, "copilot/schemas/coverage_closure_output.schema.json"))
        artifact_refs.append(artifact_ref("local_subset_coverage", path))
        steps_executed.append("run_local_subset_coverage_case")

    summary_path = subset_dir / "subset_summary.json"
    write_json(
        summary_path,
        {
            "case_count": len(results),
            "status": aggregate_local_results(results).status,
            "valid_json_count": sum(1 for item in results if item.valid_json),
            "fallback_count": sum(item.fallback_count for item in results),
            "llm_error_count": sum(item.llm_error_count for item in results),
            "claim_boundary": LOCAL_WORKFLOW_CLAIM_BOUNDARY,
        },
    )
    artifact_refs.append(artifact_ref("local_subset_summary", summary_path))
    steps_executed.append("emit_local_subset_summary")
    return local_subset_summary(artifact_refs, steps_executed, results)


def local_subset_summary(
    artifact_refs: list[dict[str, Any]],
    steps_executed: list[str],
    results: list[LocalBackendResult],
) -> dict[str, Any]:
    return {
        "artifact_refs": artifact_refs,
        "steps_executed": steps_executed,
        "aggregate_result": aggregate_local_results(results),
    }


def aggregate_local_results(results: list[LocalBackendResult]) -> LocalBackendResult:
    if not results:
        return LocalBackendResult(
            status="local_error",
            output=None,
            valid_json=False,
            fallback_count=0,
            llm_error_count=1,
            latency_ms=None,
            http_status=None,
            error="no local subset cases executed",
        )
    status = "ok"
    for item in results:
        if item.status != "ok":
            status = item.status
            break
    latencies = [item.latency_ms for item in results if item.latency_ms is not None]
    return LocalBackendResult(
        status=status,
        output=None,
        valid_json=all(item.valid_json for item in results),
        fallback_count=sum(item.fallback_count for item in results),
        llm_error_count=sum(item.llm_error_count for item in results),
        latency_ms=round(sum(latencies), 2) if latencies else None,
        http_status=results[-1].http_status,
        error=next((item.error for item in results if item.error), None),
    )


def load_repair_subset(limit: int) -> list[dict[str, Any]]:
    cases_path = ROOT / "benchmarks" / "sva_repair_cases.json"
    payload = json.loads(cases_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("sva_repair_cases.json must be a JSON array")
    return [item for item in payload if isinstance(item, dict)][:limit]


def load_packet_subset(workflow_type: Literal["triage", "coverage"], limit: int) -> list[dict[str, Any]]:
    paths = []
    for path in sorted((ROOT / "benchmarks").glob("*/cases/*.json")):
        is_coverage = path.name.startswith("coverage_")
        if workflow_type == "coverage" and not is_coverage:
            continue
        if workflow_type == "triage" and is_coverage:
            continue
        paths.append(path)
        if len(paths) == limit:
            break
    return [build_packet(case_path=path) for path in paths]


def safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)[:80] or "case"


def load_repair_case(case_id_arg: str | None, case_arg: str | None) -> tuple[dict[str, Any], Path | None]:
    if case_arg:
        case_path = resolve_path(Path(case_arg))
        if case_path.exists():
            payload = json.loads(case_path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, list):
                case_id = case_id_arg or REPAIR_DEFAULT_CASE_ID
                return find_case_row(payload, case_id), case_path
            if isinstance(payload, dict):
                return payload, case_path
        case_id_arg = case_arg
    case_id = case_id_arg or REPAIR_DEFAULT_CASE_ID
    cases_path = ROOT / "benchmarks" / "sva_repair_cases.json"
    payload = json.loads(cases_path.read_text(encoding="utf-8-sig"))
    return find_case_row(payload, case_id), cases_path


def load_packet_context(case_id_arg: str | None, case_arg: str | None, default_case_id: str) -> tuple[dict[str, Any], str]:
    if case_arg:
        case_path = resolve_path(Path(case_arg))
        if case_path.exists():
            payload = json.loads(case_path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("workflow --case JSON must be an object for triage/coverage")
            case_id = str(payload.get("case_id", case_path.stem))
            if "failing_property" in payload or "coverage_evidence" in payload:
                return payload, case_id
            return build_packet(case_path=case_path), case_id
        case_id_arg = case_arg
    case_id = case_id_arg or default_case_id
    case_path = find_benchmark_case_path(case_id)
    return build_packet(case_path=case_path), case_id


def find_case_row(rows: Any, case_id: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError("case collection must be a JSON array")
    for row in rows:
        if isinstance(row, dict) and row.get("case_id") == case_id:
            return row
    raise ValueError(f"case id not found: {case_id}")


def find_benchmark_case_path(case_id: str) -> Path:
    for path in sorted((ROOT / "benchmarks").glob("*/cases/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("case_id") == case_id:
            return path
    raise ValueError(f"benchmark case id not found: {case_id}")


def repair_candidate_for_backend(
    case: dict[str, Any],
    backend: str,
    case_path: Path | None = None,
) -> dict[str, Any]:
    if backend == "local":
        return repair_fallback(case)
    if backend == "codex":
        return {
            "source": "planned_codex_dry_run_no_send",
            "property_id": str(case.get("property_id", "generated_property")),
            "sva": str(case.get("broken_sva") or case.get("reference_sva")),
            "explanation": "Codex route was planned only. Dry-run forbids external prompt send.",
        }
    inline_candidate = case.get("replay_candidate")
    if isinstance(inline_candidate, dict):
        return dict(inline_candidate)
    replay_path = case_relative_path(case.get("replay_candidate_path"), case_path)
    if replay_path is not None and replay_path.exists():
        payload = json.loads(replay_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("replay_candidate_path must point to a JSON object")
        return payload
    return {
        "source": "replay",
        "property_id": str(case.get("property_id", "generated_property")),
        "sva": str(case.get("reference_sva") or case.get("broken_sva")),
        "explanation": "Replay candidate selected from existing benchmark reference metadata.",
    }


def verifier_result_path_from_case(case: dict[str, Any], case_path: Path | None) -> Path | None:
    return case_relative_path(case.get("verifier_outcome_path"), case_path)


def case_relative_path(value: Any, case_path: Path | None) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    if case_path is not None:
        return case_path.parent / path
    return resolve_path(path)


def problem_spec_stub(workflow_id: str, case: dict[str, Any], case_path: Path | None) -> ProblemSpec:
    digest = short_hash(json.dumps(case, sort_keys=True, default=str), length=12)
    return ProblemSpec(
        problem_id=f"problem_z3_{digest}",
        tool=ToolName.Z3,
        language=Language.SMT2,
        statement=str(case.get("intent") or case.get("property_intent") or case.get("broken_sva")),
        assumptions=[],
        context_refs=[],
        metadata={
            "workflow_id": workflow_id,
            "case_id": case.get("case_id"),
            "property_id": case.get("property_id"),
            "case_path": str(case_path) if case_path else None,
            "evidence_context": case.get("evidence_context"),
            "stage5d_stub_only": True,
        },
    )


def candidate_core_stub(
    workflow_id: str,
    problem_id: str,
    candidate_payload: dict[str, Any],
    backend: str,
) -> Candidate:
    created_at = datetime.now(timezone.utc)
    git_sha = git_head_sha()
    run_id = make_run_id(git_sha, now=created_at, nonce=short_hash(workflow_id, length=6))
    digest = short_hash(json.dumps(candidate_payload, sort_keys=True), length=12)
    return Candidate(
        candidate_id=f"cand_0001_workflow_{digest}",
        run_id=run_id,
        problem_id=problem_id,
        attempt_id="attempt_0001",
        producer=f"stage5d_{backend}_dry_run",
        content=str(candidate_payload["sva"]),
        content_type="text/systemverilog-assertion",
        model=None,
        tokens_in=0,
        tokens_out=0,
        artifact_refs=[],
        metadata={
            "workflow_id": workflow_id,
            "dry_run": True,
            "external_model_called": False,
        },
    )


def write_moore_handoff_manifest(out_dir: Path, task_type: str) -> Path:
    path = out_dir / "moore_handoff_manifest.json"
    manifest = {
        "manifest_type": "MooreHandoffManifest",
        "schema_version": "stage5d.workflow_handoff.v1",
        "task_type": task_type,
        "generated_by": "jasperloop workflow repair --prepare-moore-handoff",
        "dry_run": True,
        "external_calls_allowed": False,
        "jaspergold_invoked": False,
        "moore_invoked": False,
        "expected_import": "sanitized verifier summary JSON only",
        "claim_boundary": (
            "This handoff manifest prepares the boundary for a future Moore-side verification. "
            "It does not run Moore or JasperGold and does not include raw logs or traces."
        ),
    }
    write_json(path, manifest)
    return path


def load_optional_json(path: Path | None) -> Any | None:
    if path is None:
        return None
    resolved = resolve_path(path)
    return json.loads(resolved.read_text(encoding="utf-8-sig"))


def can_align(case: dict[str, Any], candidate_payload: dict[str, Any]) -> bool:
    return bool(
        case.get("case_id")
        and case.get("property_id")
        and (case.get("intent") or case.get("property_intent"))
        and candidate_payload.get("sva")
        and case.get("reference_sva")
    )


def strip_extra(payload: dict[str, Any], schema_path: str) -> dict[str, Any]:
    schema = json.loads(resolve_path(Path(schema_path)).read_text(encoding="utf-8-sig"))
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return payload
    return {key: payload[key] for key in properties if key in payload}


def validate_against_schema(payload: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    Draft202012Validator(schema).validate(payload)


def build_manifest(
    *,
    args: argparse.Namespace,
    workflow_id: str,
    workflow_type: Literal["repair", "triage", "coverage", "demo"],
    created_at: datetime,
    case_id: str,
    steps_planned: list[str],
    steps_executed: list[str],
    artifact_refs: list[dict[str, Any]],
    verifier_outcome_ref: str | None = None,
    intent_alignment_ref: str | None = None,
    final_report_ref: str | None = None,
    blocked_reason: str | None = None,
    case_count: int = 1,
    local_result: LocalBackendResult | None = None,
) -> WorkflowManifest:
    external_send_allowed = external_send_allowed_for(args)
    config = local_backend_config(args) if args.backend == "local" else None
    gpu = gpu_snapshot() if args.backend == "local" else {}
    if local_result is not None:
        status = local_result.status
    elif blocked_reason:
        status = "blocked"
    elif args.dry_run:
        status = "dry_run"
    else:
        status = "ok"
    return WorkflowManifest(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        git_sha=git_head_sha(),
        timestamp=format_utc(created_at),
        case_id=case_id,
        backend=str(args.backend),
        status=status,
        external_send_allowed=external_send_allowed,
        local_only=local_only_effective(args) if args.backend == "local" else not external_send_allowed,
        model_id=config.model_id if config else None,
        endpoint_url=config.endpoint_url if config else None,
        backend_type=config.backend_type if config else None,
        LOCAL_ONLY=local_only_effective(args) if args.backend == "local" else not external_send_allowed,
        cloud_fallback_allowed=False if args.backend == "local" else external_send_allowed,
        cloud_fallback_called=False,
        max_model_len=config.max_model_len if config else None,
        gpu_name=str(gpu.get("name")) if gpu.get("name") else None,
        gpu_vram_gb=float(gpu["memory_total_gb"]) if gpu.get("memory_total_gb") is not None else None,
        task_type=workflow_type,
        case_count=case_count,
        valid_json=local_result.valid_json if local_result else None,
        fallback_count=local_result.fallback_count if local_result else 0,
        llm_error_count=local_result.llm_error_count if local_result else 0,
        latency_ms=local_result.latency_ms if local_result else None,
        steps_planned=steps_planned,
        steps_executed=steps_executed,
        artifact_refs=artifact_refs,
        verifier_required=bool(getattr(args, "prepare_moore_handoff", False)),
        verifier_outcome_ref=verifier_outcome_ref,
        intent_alignment_ref=intent_alignment_ref,
        final_report_ref=final_report_ref,
        claim_boundary=LOCAL_WORKFLOW_CLAIM_BOUNDARY if args.backend == "local" else WORKFLOW_CLAIM_BOUNDARY,
        dry_run=not local_execution_requested(args),
        blocked_reason=blocked_reason,
    )


def write_manifest(args: argparse.Namespace, out_dir: Path, manifest: WorkflowManifest) -> Path:
    manifest_path = resolve_path(args.manifest_out) if args.manifest_out else out_dir / "workflow_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest.model_dump(mode="json"))
    return manifest_path


def external_backend_blocker(args: argparse.Namespace) -> str | None:
    if args.backend == "codex" and not args.require_explicit_external_send:
        return "backend=codex is external and requires --require-explicit-external-send"
    return local_execution_blocker(args)


def external_send_allowed_for(args: argparse.Namespace) -> bool:
    return bool(
        args.backend == "codex"
        and args.require_explicit_external_send
        and not args.dry_run
    )


def final_report(
    workflow_type: str,
    case_id: str,
    backend: str,
    blocked_reason: str | None,
    steps_executed: list[str],
    *,
    verifier_ref: str | None = None,
    alignment_ref: str | None = None,
) -> str:
    status = "blocked" if blocked_reason else "dry-run complete"
    lines = [
        f"# JasperLoop Workflow {workflow_type.title()} Report",
        "",
        f"Case: `{case_id}`",
        f"Backend route: `{backend}`",
        f"Status: {status}",
        "",
        "## Claim Boundary",
        "",
        LOCAL_WORKFLOW_CLAIM_BOUNDARY if backend == "local" else WORKFLOW_CLAIM_BOUNDARY,
        "",
        "Proof status and intent alignment are separate evidence dimensions. A proof pass does not imply semantic intent alignment.",
        "Best-of-k, when referenced by upstream repair reports, is an upper-bound search metric and not single-output success.",
        "",
    ]
    if blocked_reason:
        lines.extend(["## Blocked", "", blocked_reason, ""])
    if verifier_ref:
        lines.extend(["## Imported Verifier Context", "", f"- `{verifier_ref}`", ""])
    if alignment_ref:
        lines.extend(["## Intent Alignment", "", f"- `{alignment_ref}`", ""])
    lines.extend(["## Steps Executed", ""])
    if steps_executed:
        lines.extend(f"- {step}" for step in steps_executed)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def artifact_ref(name: str, path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "path": str(path),
        "sha256": sha256_bytes(path.read_bytes()) if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else None,
    }


def write_qwen_workflow_readiness_report(manifest_payload: dict[str, Any], *, blocked: bool) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reports_dir = ROOT / "reports" / "local_llm"
    reports_dir.mkdir(parents=True, exist_ok=True)
    if blocked:
        manifest_path = reports_dir / f"qwen_workflow_readiness_manifest_{timestamp}.json"
        report_path = reports_dir / f"qwen_workflow_readiness_blocker_{timestamp}.md"
        title = "Qwen Workflow Readiness Blocker"
    else:
        manifest_path = reports_dir / f"qwen_workflow_subset_manifest_{timestamp}.json"
        report_path = reports_dir / f"qwen_workflow_subset_summary_{timestamp}.md"
        title = "Qwen Workflow Subset Summary"
    write_json(manifest_path, manifest_payload)
    lines = [
        f"# {title}",
        "",
        f"- Workflow ID: `{manifest_payload.get('workflow_id')}`",
        f"- Git SHA: `{manifest_payload.get('git_sha')}`",
        f"- Backend: `{manifest_payload.get('backend')}`",
        f"- Status: `{manifest_payload.get('status')}`",
        f"- Model: `{manifest_payload.get('model_id')}`",
        f"- Endpoint: `{manifest_payload.get('endpoint_url')}`",
        f"- Backend type: `{manifest_payload.get('backend_type')}`",
        f"- LOCAL_ONLY: `{manifest_payload.get('LOCAL_ONLY')}`",
        f"- Cloud fallback allowed: `{manifest_payload.get('cloud_fallback_allowed')}`",
        f"- Cloud fallback called: `{manifest_payload.get('cloud_fallback_called')}`",
        f"- Case count: `{manifest_payload.get('case_count')}`",
        f"- Valid JSON: `{manifest_payload.get('valid_json')}`",
        f"- Fallback count: `{manifest_payload.get('fallback_count')}`",
        f"- LLM error count: `{manifest_payload.get('llm_error_count')}`",
        "",
        "## Claim Boundary",
        "",
        str(manifest_payload.get("claim_boundary") or LOCAL_WORKFLOW_CLAIM_BOUNDARY),
        "",
    ]
    write_text(report_path, "\n".join(lines))


def workflow_id_for(workflow_type: str, case_id: str, created_at: datetime) -> str:
    nonce = short_hash(f"{workflow_type}:{case_id}:{created_at.isoformat()}", length=8)
    return f"workflow_{workflow_type}_{created_at.strftime('%Y%m%dT%H%M%SZ')}_{nonce}"


def resolve_path(path: Path | str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return ROOT / candidate


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "0" * 40
    return result.stdout.strip()


def as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def print_workflow_result(manifest_path: Path, report_path: Path, *, blocked: bool, dry_run: bool) -> None:
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "report": str(report_path),
                "dry_run": dry_run,
                "blocked": blocked,
            },
            indent=2,
        )
    )
