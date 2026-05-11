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
from app.models.core import (
    Candidate,
    CoreModel,
    Language,
    ProblemSpec,
    ToolName,
)
from copilot.agents.coverage_closure_agent import structured_fallback as coverage_fallback
from copilot.agents.dv_triage_agent import structured_fallback as triage_fallback
from copilot.agents.sva_repair_agent import structured_fallback as repair_fallback
from tools.build_evidence_packet import build_packet

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_CLAIM_BOUNDARY = (
    "Stage 5D workflow evidence is a manifest-driven dry-run orchestration record. "
    "It chains existing local CLI capabilities and static heuristics only; it does not "
    "call Codex, Qwen, JasperGold, Moore, network services, or cloud fallback by default, "
    "and it does not change Stage 4 reports, benchmark labels, schemas, or prior claims."
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
    external_send_allowed: bool
    local_only: bool
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
        print_workflow_result(manifest_path, report_path, blocked=True)
        return 2

    steps_executed.append("load_repair_case_metadata")
    problem = problem_spec_stub(workflow_id, case, case_path)
    problem_path = out_dir / "problem_spec_stub.json"
    write_json(problem_path, problem.model_dump(mode="json"))
    artifact_refs.append(artifact_ref("problem_spec_stub", problem_path))
    steps_executed.append("prepare_problem_spec_stub")
    steps_executed.append("choose_backend_route")

    candidate_payload = repair_candidate_for_backend(case, args.backend)
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

    verifier_payload = load_optional_json(args.verifier_result)
    if verifier_payload is not None and args.verifier_result is not None:
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
                evidence_refs=[str(candidate_path), *(str(args.verifier_result) for _ in [0] if args.verifier_result)],
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
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    print_workflow_result(manifest_path, report_path, blocked=False)
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
        print_workflow_result(manifest_path, report_path, blocked=True)
        return 2

    packet_path = out_dir / "evidence_packet.json"
    write_json(packet_path, packet)
    artifact_refs.append(artifact_ref("evidence_packet", packet_path))
    steps_executed.append("load_evidence_packet_or_minimal_packet" if workflow_type == "triage" else "load_coverage_context")
    steps_executed.append("choose_backend_route")

    if workflow_type == "triage":
        raw_candidate = triage_fallback(packet)
        schema_path = "copilot/schemas/diagnosis_output.schema.json"
        candidate_name = "diagnosis_candidate"
        candidate_step = "emit_diagnosis_candidate"
    else:
        raw_candidate = coverage_fallback(packet)
        schema_path = "copilot/schemas/coverage_closure_output.schema.json"
        candidate_name = "coverage_recommendation"
        candidate_step = "emit_closure_recommendation"

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
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    print_workflow_result(manifest_path, report_path, blocked=False)
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
    steps_executed = (
        ["block_external_backend_without_acknowledgement"]
        if blocked_reason
        else ["plan_repair_workflow", "plan_triage_workflow", "plan_coverage_workflow", "emit_final_workflow_report"]
    )
    report_path = out_dir / "workflow_report.md"
    write_text(report_path, final_report("demo", str(case_id), args.backend, blocked_reason, steps_executed))
    artifact_refs = [artifact_ref("final_report", report_path)]
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
    )
    manifest_path = write_manifest(args, out_dir, manifest)
    print_workflow_result(manifest_path, report_path, blocked=bool(blocked_reason))
    return 2 if blocked_reason else 0


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


def repair_candidate_for_backend(case: dict[str, Any], backend: str) -> dict[str, Any]:
    if backend == "local":
        return repair_fallback(case)
    if backend == "codex":
        return {
            "source": "planned_codex_dry_run_no_send",
            "property_id": str(case.get("property_id", "generated_property")),
            "sva": str(case.get("broken_sva") or case.get("reference_sva")),
            "explanation": "Codex route was planned only. Dry-run forbids external prompt send.",
        }
    return {
        "source": "replay",
        "property_id": str(case.get("property_id", "generated_property")),
        "sva": str(case.get("reference_sva") or case.get("broken_sva")),
        "explanation": "Replay candidate selected from existing benchmark reference metadata.",
    }


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
) -> WorkflowManifest:
    external_send_allowed = external_send_allowed_for(args)
    return WorkflowManifest(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        git_sha=git_head_sha(),
        timestamp=format_utc(created_at),
        case_id=case_id,
        backend=str(args.backend),
        external_send_allowed=external_send_allowed,
        local_only=not external_send_allowed,
        steps_planned=steps_planned,
        steps_executed=steps_executed,
        artifact_refs=artifact_refs,
        verifier_required=bool(getattr(args, "prepare_moore_handoff", False)),
        verifier_outcome_ref=verifier_outcome_ref,
        intent_alignment_ref=intent_alignment_ref,
        final_report_ref=final_report_ref,
        claim_boundary=WORKFLOW_CLAIM_BOUNDARY,
        dry_run=bool(args.dry_run),
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
    return None


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
        WORKFLOW_CLAIM_BOUNDARY,
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


def print_workflow_result(manifest_path: Path, report_path: Path, *, blocked: bool) -> None:
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "report": str(report_path),
                "dry_run": True,
                "blocked": blocked,
            },
            indent=2,
        )
    )
