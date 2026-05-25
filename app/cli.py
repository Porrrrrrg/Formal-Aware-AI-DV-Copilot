"""Unified JasperLoop-DV command-line wrapper."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.alignment.intent_alignment import (
    IntentAlignmentResult,
    evaluate_intent_alignment_cases,
    load_cases,
)
from app.core.artifacts import (
    artifact_manifest_key,
    canonical_json_bytes,
    make_run_id,
    sha256_bytes,
    short_hash,
)
from app.models.core import (
    ArtifactEncoding,
    ArtifactKind,
    ArtifactManifest,
    ArtifactRecord,
    RunManifest,
    RunStatus,
    ToolchainVersions,
)
from app.workflow import add_workflow_parser, run_workflow_command

ROOT = Path(__file__).resolve().parents[1]

CLAIM_BOUNDARY = (
    "Stage 5A CLI wrapper evidence only. This command records the planned local "
    "runner/script and dry-run safety posture; it does not change Stage 2/3/4 "
    "reports, benchmark labels, schemas, or prior result semantics."
)

MOORE_CLAIM_BOUNDARY = (
    "Stage 5B JasperGold host handoff automation records sanitized local handoff metadata only. "
    "It does not run a host environment, JasperGold, Codex, Qwen, or new experiments, and it does "
    "not change benchmark labels or Stage 2/3/4 result semantics."
)

ALIGNMENT_CLAIM_BOUNDARY = (
    "Stage 5C intent alignment evidence is static/offline heuristic review only. "
    "It does not call Codex, Qwen, JasperGold, or Moore; it does not establish "
    "formal equivalence or production readiness."
)

MOORE_TASK_TYPES = (
    "evidence-packets",
    "codex-repair-final-proof",
    "sva-repair-ablation-proof",
)

FORBIDDEN_ARTIFACT_PATTERNS = (
    "*.log",
    "*.jou",
    "*.vcd",
    "*.fsdb",
    "*/trace/*",
    "*/traces/*",
    "*/jgproject/*",
    "*/license*",
    "*/generated_harness_dumps/*",
)

FORBIDDEN_PATH_MARKERS = (
    ".log",
    ".jou",
    ".vcd",
    ".fsdb",
    "/trace/",
    "/traces/",
    "/jgproject/",
    "/generated_harness_dumps/",
    "license",
)


@dataclass(frozen=True)
class CommandSpec:
    """Static metadata for one Stage 5A CLI subcommand."""

    evidence_type: str
    planned_runner: str | None
    planned_args: tuple[str, ...]
    description: str


COMMANDS: dict[str, CommandSpec] = {
    "build-packet": CommandSpec(
        evidence_type="stage5a_evidence_packet_build_plan",
        planned_runner="scripts/build_all_evidence_packets.py",
        planned_args=(),
        description="Plan evidence-packet construction through existing packet builders.",
    ),
    "repair": CommandSpec(
        evidence_type="stage5a_sva_repair_plan",
        planned_runner="evaluation/run_sva_repair_eval.py",
        planned_args=("--jasper-dry-run",),
        description="Plan SVA repair evaluation through the existing repair runner.",
    ),
    "triage": CommandSpec(
        evidence_type="stage5a_triage_plan",
        planned_runner="evaluation/run_agent_eval.py",
        planned_args=("--systems", "structured"),
        description="Plan deterministic structured triage through the existing runner.",
    ),
    "coverage": CommandSpec(
        evidence_type="stage5a_coverage_plan",
        planned_runner="evaluation/run_coverage_eval.py",
        planned_args=("--systems", "structured"),
        description="Plan deterministic coverage closure through the existing runner.",
    ),
    "eval": CommandSpec(
        evidence_type="stage5a_eval_plan",
        planned_runner="evaluation/run_fveval_subset.py",
        planned_args=(),
        description="Plan local FVEval-compatible subset evaluation without model or Jasper calls.",
    ),
    "moore-handoff": CommandSpec(
        evidence_type="stage5a_moore_handoff_plan",
        planned_runner="scripts/run_jasper_sva_repair_eval.sh",
        planned_args=(),
        description="Plan a JasperGold host handoff without invoking JasperGold or model calls.",
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jasperloop",
        description="Unified JasperLoop-DV Stage 5A CLI wrapper.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    for name, spec in COMMANDS.items():
        subparser = subparsers.add_parser(name, description=spec.description, help=spec.description)
        subparser.add_argument(
            "--dry-run",
            action="store_true",
            help="Emit manifests and planned runner metadata without executing a runner.",
        )
        subparser.add_argument(
            "--out-dir",
            type=Path,
            default=Path("artifacts") / "jasperloop_cli" / name,
            help="Directory for Stage 5A manifests.",
        )
        if name == "moore-handoff":
            moore_subparsers = subparser.add_subparsers(dest="moore_action")
            prepare = moore_subparsers.add_parser(
                "prepare",
                description="Prepare a sanitized JasperGold host handoff manifest.",
                help="Prepare a sanitized JasperGold host handoff manifest.",
            )
            prepare.add_argument("task_type", choices=MOORE_TASK_TYPES)
            prepare.add_argument(
                "--out-dir",
                type=Path,
                default=Path("artifacts") / "jasperloop_cli" / name,
                help="Directory for handoff_manifest.json.",
            )
            prepare.add_argument("--dry-run", action="store_true")

            validate = moore_subparsers.add_parser(
                "validate",
                description="Validate a JasperGold host handoff manifest without host access.",
                help="Validate a JasperGold host handoff manifest without host access.",
            )
            validate.add_argument("--manifest", type=Path, required=True)
            validate.add_argument("--out-dir", type=Path)
            validate.add_argument("--dry-run", action="store_true")

            import_result = moore_subparsers.add_parser(
                "import-result",
                description="Import a sanitized JasperGold host summary manifest.",
                help="Import a sanitized JasperGold host summary manifest.",
            )
            import_result.add_argument("summary_manifest", type=Path, nargs="?")
            import_result.add_argument("--manifest", type=Path, dest="summary_manifest_option")
            import_result.add_argument(
                "--out-dir",
                type=Path,
                default=Path("artifacts") / "jasper_import",
                help="Directory for imported lightweight summaries.",
            )
            import_result.add_argument("--dry-run", action="store_true")
    add_workflow_parser(subparsers)
    align = subparsers.add_parser(
        "align-intent",
        description="Evaluate SVA candidates against intent/reference metadata using static heuristics.",
        help="Evaluate SVA candidates against intent/reference metadata using static heuristics.",
    )
    align.add_argument("--dry-run", action="store_true")
    align.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts") / "alignment",
        help="Directory for intent-alignment reports.",
    )
    align.add_argument(
        "--cases",
        type=Path,
        default=Path("benchmarks") / "sva_repair_cases.json",
        help="JSON or JSONL cases with intent, reference SVA, and signal metadata.",
    )
    align.add_argument(
        "--candidates",
        type=Path,
        default=Path("artifacts") / "alignment" / "candidates.jsonl",
        help="Optional JSON or JSONL repaired/generated candidate records.",
    )
    align.add_argument("--limit", type=int, default=None, help="Limit cases for smoke runs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_command(args, argv if argv is not None else sys.argv[1:])


def run_command(args: argparse.Namespace, argv: list[str]) -> int:
    subcommand = str(args.subcommand)
    if subcommand == "workflow":
        return run_workflow_command(args, argv)
    if subcommand == "moore-handoff" and getattr(args, "moore_action", None):
        return run_moore_handoff(args)
    if subcommand == "align-intent":
        return run_align_intent(args, argv)

    spec = COMMANDS[subcommand]
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dry_run = bool(args.dry_run)
    git_sha = git_head_sha()
    created_at = datetime.now(timezone.utc)
    nonce = short_hash(f"{subcommand}:{out_dir}:{created_at.isoformat()}", length=6)
    run_id = make_run_id(git_sha, now=created_at, nonce=nonce)
    planned_command = planned_internal_command(spec, out_dir)

    stage5_manifest = {
        "manifest_type": "RunManifest",
        "schema_version": "stage5a.cli.v1",
        "run_id": run_id,
        "git_sha": git_sha,
        "command": "jasperloop",
        "argv": ["jasperloop", *argv],
        "subcommand": subcommand,
        "dry_run": dry_run,
        "created_at_utc": format_utc(created_at),
        "out_dir": str(out_dir),
        "external_calls_allowed": False,
        "evidence_type": spec.evidence_type,
        "claim_boundary": CLAIM_BOUNDARY,
        "planned_internal_runner": spec.planned_runner,
        "planned_internal_command": planned_command,
        "runner_invoked": False,
        "status": "planned" if dry_run else "blocked_external_execution_disabled",
        "notes": [
            "Stage 5A keeps external calls disabled; there is no flag in this CLI to enable them.",
            "Dry-run mode writes manifests only and does not invoke model, JasperGold, or Moore paths.",
        ],
    }
    if not dry_run:
        stage5_manifest["notes"].append(
            "Non-dry execution is intentionally blocked in Stage 5A until an explicit gate is added."
        )

    stage5_path = out_dir / "jasperloop_run_manifest.json"
    write_json(stage5_path, stage5_manifest)
    core_run = build_core_run_manifest(
        run_id=run_id,
        created_at=created_at,
        git_sha=git_sha,
        subcommand=subcommand,
        out_dir=out_dir,
        stage5_manifest_path=stage5_path,
        stage5_manifest=stage5_manifest,
    )
    core_run_path = out_dir / "core_run_manifest.json"
    write_json(core_run_path, core_run.model_dump(mode="json"))
    artifact_manifest = build_artifact_manifest(
        run_id=run_id,
        created_at=created_at,
        stage5_path=stage5_path,
        core_run_path=core_run_path,
    )
    artifact_manifest_path = out_dir / "core_artifact_manifest.json"
    write_json(artifact_manifest_path, artifact_manifest.model_dump(mode="json"))

    print(json.dumps({"manifest": str(stage5_path), "dry_run": dry_run}, indent=2))
    return 0 if dry_run else 2


def run_align_intent(args: argparse.Namespace, argv: list[str]) -> int:
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    git_sha = git_head_sha()
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    cases_path = resolve_path(args.cases)
    candidates_path = resolve_path(args.candidates) if args.candidates else None
    cases = load_cases(cases_path, candidates_path, limit=args.limit)
    results = evaluate_intent_alignment_cases(cases)
    report_path = out_dir / f"intent_alignment_smoke_summary_{timestamp}.md"
    manifest_path = out_dir / f"intent_alignment_smoke_manifest_{timestamp}.json"
    results_path = out_dir / f"intent_alignment_results_{timestamp}.jsonl"
    write_text(report_path, build_alignment_report(results, created_at))
    write_text(
        results_path,
        "\n".join(json.dumps(result.model_dump(mode="json"), sort_keys=True) for result in results) + "\n",
    )
    manifest = {
        "manifest_type": "IntentAlignmentSmokeManifest",
        "schema_version": "stage5c.intent_alignment.v1",
        "created_at_utc": format_utc(created_at),
        "git_sha": git_sha,
        "command": "jasperloop align-intent",
        "argv": ["jasperloop", *argv],
        "dry_run": bool(args.dry_run),
        "external_calls_allowed": False,
        "runner_invoked": True,
        "evidence_type": "static_offline_heuristic_evaluator",
        "claim_boundary": ALIGNMENT_CLAIM_BOUNDARY,
        "cases": str(cases_path),
        "candidates": str(candidates_path) if candidates_path else None,
        "case_count": len(cases),
        "result_count": len(results),
        "label_counts": label_counts(results),
        "manual_review_required_count": sum(1 for result in results if result.manual_review_required),
        "artifacts": [
            {"path": str(report_path), "sha256": sha256_bytes(report_path.read_bytes())},
            {"path": str(results_path), "sha256": sha256_bytes(results_path.read_bytes())},
        ],
        "notes": [
            "No external model, JasperGold, or Moore calls are made.",
            "Proof pass context is preserved as context only and never treated as semantic equivalence.",
            "Labels are conservative static heuristics and ambiguous cases require manual review.",
        ],
    }
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "report": str(report_path),
                "results": str(results_path),
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )
    return 0


def build_alignment_report(results: list[IntentAlignmentResult], created_at: datetime) -> str:
    counts = label_counts(results)
    lines = [
        "# Intent Alignment Smoke Summary",
        "",
        f"Created UTC: {format_utc(created_at)}",
        "",
        "Evidence type: static/offline heuristic evaluator.",
        "",
        (
            "This smoke report does not claim new benchmark results, formal equivalence, "
            "or production readiness. Jasper proof status, when present, remains separate "
            "from intent alignment."
        ),
        "",
        "## Summary",
        "",
        f"- Results: {len(results)}",
        f"- Manual review required: {sum(1 for result in results if result.manual_review_required)}",
        f"- Label counts: {json.dumps(counts, sort_keys=True)}",
        "",
        "## Cases",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"- `{result.case_id}` / `{result.property_id or result.candidate_id}`: "
                f"{result.alignment_label.value} ({result.alignment_score:.3f}); "
                f"manual_review_required={str(result.manual_review_required).lower()}",
            ]
        )
    return "\n".join(lines) + "\n"


def label_counts(results: list[IntentAlignmentResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        label = result.alignment_label.value
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def run_moore_handoff(args: argparse.Namespace) -> int:
    action = str(args.moore_action)
    if action == "prepare":
        return moore_prepare(args)
    if action == "validate":
        return moore_validate(args)
    if action == "import-result":
        return moore_import_result(args)
    raise ValueError(f"unsupported moore-handoff action: {action}")


def moore_prepare(args: argparse.Namespace) -> int:
    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    task_type = str(args.task_type)
    task = moore_task_spec(task_type, out_dir)
    created_at = datetime.now(timezone.utc)
    manifest = {
        "manifest_type": "MooreHandoffManifest",
        "schema_version": "stage5b.moore_handoff.v1",
        "git_sha": git_head_sha(),
        "branch": git_branch(),
        "task_type": task_type,
        "command_to_run_on_moore": task["command_to_run_on_moore"],
        "expected_outputs": task["expected_outputs"],
        "forbidden_outputs": list(FORBIDDEN_ARTIFACT_PATTERNS),
        "input_artifact_refs": input_artifact_refs(task["input_artifacts"]),
        "timestamp": format_utc(created_at),
        "generated_by": "jasperloop moore-handoff prepare",
        "dry_run": bool(args.dry_run),
        "external_calls_allowed": False,
        "raw_prompt_text_included": False,
        "claim_boundary": MOORE_CLAIM_BOUNDARY,
    }
    manifest_path = out_dir / "handoff_manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"manifest": str(manifest_path), "dry_run": bool(args.dry_run)}, indent=2))
    return 0


def moore_validate(args: argparse.Namespace) -> int:
    manifest_path = resolve_path(args.manifest)
    failures: list[str] = []
    manifest: dict[str, Any] | None = None
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            failures.append("manifest root is not a JSON object")
        else:
            manifest = loaded
    except FileNotFoundError:
        failures.append(f"manifest does not exist: {manifest_path}")
    except json.JSONDecodeError as exc:
        failures.append(f"manifest is not parseable JSON: {exc}")

    if manifest is not None:
        failures.extend(validate_input_artifacts(manifest))
        failures.extend(validate_expected_outputs(manifest))
        failures.extend(validate_staged_forbidden_paths(manifest))

    report = {
        "manifest": str(manifest_path),
        "dry_run": bool(args.dry_run),
        "valid": not failures,
        "failures": failures,
        "external_calls_allowed": False,
    }
    if args.out_dir:
        out_dir = resolve_path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / "validation_report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if not failures else 2


def moore_import_result(args: argparse.Namespace) -> int:
    summary_manifest = args.summary_manifest_option or args.summary_manifest
    if summary_manifest is None:
        print(json.dumps({"valid": False, "error": "missing summary manifest"}, indent=2))
        return 2
    source = resolve_path(summary_manifest)
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(json.dumps({"valid": False, "error": f"invalid JSON: {exc}"}, indent=2))
        return 2
    except FileNotFoundError:
        print(json.dumps({"valid": False, "error": f"missing summary manifest: {source}"}, indent=2))
        return 2
    if not isinstance(payload, dict):
        print(json.dumps({"valid": False, "error": "summary manifest root is not an object"}, indent=2))
        return 2

    forbidden = find_forbidden_paths(payload)
    if forbidden:
        print(
            json.dumps(
                {
                    "valid": False,
                    "error": "Moore result references forbidden raw artifacts",
                    "forbidden_paths": forbidden,
                },
                indent=2,
            )
        )
        return 2

    out_dir = resolve_path(args.out_dir)
    created_at = datetime.now(timezone.utc)
    git_sha = git_head_sha()
    run_id = make_run_id(git_sha, now=created_at)
    summary = {
        "manifest_type": "MooreImportedSummary",
        "schema_version": "stage5b.moore_import.v1",
        "source_manifest": str(source),
        "source_sha256": sha256_bytes(source.read_bytes()),
        "git_sha": git_sha,
        "branch": git_branch(),
        "imported_at": format_utc(created_at),
        "dry_run": bool(args.dry_run),
        "external_calls_allowed": False,
        "raw_artifact_policy": raw_artifact_policy(),
        "moore_summary": sanitized_summary(payload),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "moore_import_summary.json"
    write_json(summary_path, summary)
    artifact_manifest = build_import_artifact_manifest(
        run_id=run_id,
        created_at=created_at,
        summary_path=summary_path,
    )
    artifact_manifest_path = out_dir / "moore_import_artifact_manifest.json"
    write_json(artifact_manifest_path, artifact_manifest.model_dump(mode="json"))

    print(
        json.dumps(
            {
                "summary": str(summary_path),
                "artifact_manifest": str(artifact_manifest_path),
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )
    return 0


def planned_internal_command(spec: CommandSpec, out_dir: Path) -> list[str] | None:
    if spec.planned_runner is None:
        return None
    command = ["bash" if spec.planned_runner.endswith(".sh") else sys.executable, spec.planned_runner]
    command.extend(spec.planned_args)
    if spec.planned_runner.endswith("build_all_evidence_packets.py"):
        command.extend(["--out-dir", str(out_dir / "case_packets")])
    elif spec.planned_runner.endswith("run_fveval_subset.py"):
        command.extend(["--markdown", str(out_dir / "fveval_subset_results.md")])
        command.extend(["--out", str(out_dir / "runner_output.json")])
    elif spec.planned_runner.startswith("scripts/run_jasper_"):
        pass
    else:
        command.extend(["--out", str(out_dir / "runner_output.json")])
    return command


def moore_task_spec(task_type: str, out_dir: Path) -> dict[str, Any]:
    manifest_out = out_dir / "moore_result_manifest.json"
    if task_type == "evidence-packets":
        return {
            "input_artifacts": [
                Path("benchmarks/sva_generation_cases.json"),
                Path("benchmarks/sva_repair_cases.json"),
                Path("scripts/build_all_evidence_packets.py"),
            ],
            "command_to_run_on_moore": [
                "tcsh",
                "-fc",
                (
                    "source /vol/eecs391/cadence.env; "
                    "python3.11 scripts/build_all_evidence_packets.py"
                ),
            ],
            "expected_outputs": [
                "jasper/reports/case_packets/<design>/<case>/evidence_packet.json",
                "artifacts/jasper_handoff/evidence_packet_summary_<timestamp>.md",
            ],
        }
    if task_type == "codex-repair-final-proof":
        artifact = "artifacts/qwen_jasper_recheck/sva_repair_qwen_full.json"
        return {
            "input_artifacts": [
                Path(artifact),
                Path("scripts/run_jasper_sva_repair_eval.sh"),
            ],
            "command_to_run_on_moore": [
                "bash",
                "scripts/run_jasper_sva_repair_eval.sh",
            ],
            "expected_outputs": [
                "evaluation/results/sva_repair_jasper_local.json",
                "jasper/reports/sva_repair/<case>/",
            ],
        }
    if task_type == "sva-repair-ablation-proof":
        artifact = "artifacts/sva_repair_ablation/candidates.jsonl"
        return {
            "input_artifacts": [
                Path(artifact),
                Path("scripts/run_jasper_sva_repair_eval.sh"),
            ],
            "command_to_run_on_moore": [
                "bash",
                "scripts/run_jasper_sva_repair_eval.sh",
            ],
            "expected_outputs": [
                "artifacts/sva_repair_ablation/jasper_summary_<timestamp>.md",
                "jasper/reports/sva_repair_ablation/",
            ],
        }
    raise ValueError(f"unsupported Moore handoff task type: {task_type}")


def input_artifact_refs(paths: list[Path]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for path in paths:
        resolved = resolve_path(path)
        record: dict[str, Any] = {"path": path.as_posix(), "exists": resolved.exists()}
        if resolved.exists() and resolved.is_file():
            record["sha256"] = sha256_bytes(resolved.read_bytes())
            record["size_bytes"] = resolved.stat().st_size
        else:
            record["sha256"] = None
            record["size_bytes"] = None
        refs.append(record)
    return refs


def validate_input_artifacts(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for ref in manifest.get("input_artifact_refs", []):
        if not isinstance(ref, dict):
            failures.append("input_artifact_refs entry is not an object")
            continue
        path_value = ref.get("path")
        if not isinstance(path_value, str):
            failures.append("input artifact is missing path")
            continue
        path = resolve_path(Path(path_value))
        if not path.exists():
            failures.append(f"missing input artifact: {path_value}")
            continue
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as exc:
                failures.append(f"input JSON is not parseable: {path_value}: {exc}")
        expected_sha = ref.get("sha256")
        if isinstance(expected_sha, str) and expected_sha:
            actual_sha = sha256_bytes(path.read_bytes())
            if actual_sha.lower() != expected_sha.lower():
                failures.append(f"input artifact sha256 mismatch: {path_value}")
    return failures


def validate_expected_outputs(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected = manifest.get("expected_outputs", [])
    if not isinstance(expected, list) or not expected:
        return ["expected_outputs must be a non-empty list"]
    for item in expected:
        if not isinstance(item, str):
            failures.append("expected output entry is not a string")
            continue
        normalized = item.replace("\\", "/")
        name = Path(normalized).name
        if not (
            normalized.startswith("artifacts/")
            or normalized.startswith("evaluation/results/")
            or normalized.startswith("jasper/reports/")
        ):
            failures.append(
                "expected output must stay under artifacts/, evaluation/results/, "
                f"or jasper/reports/: {item}"
            )
        if " " in name:
            failures.append(f"expected output filename contains spaces: {item}")
        if not (name.endswith(".json") or name.endswith(".md")):
            failures.append(f"expected output must be a JSON manifest or Markdown summary: {item}")
    return failures


def validate_staged_forbidden_paths(manifest: dict[str, Any]) -> list[str]:
    forbidden = list(manifest.get("forbidden_outputs", FORBIDDEN_ARTIFACT_PATTERNS))
    staged = staged_paths()
    bad = [path for path in staged if path_is_forbidden(path, forbidden)]
    return [f"forbidden artifact is staged: {path}" for path in bad]


def staged_paths() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def path_is_forbidden(path: str, patterns: list[Any]) -> bool:
    normalized = path.replace("\\", "/").lower()
    if any(marker in normalized for marker in FORBIDDEN_PATH_MARKERS):
        return True
    return any(Path(normalized).match(str(pattern).lower()) for pattern in patterns)


def find_forbidden_paths(payload: Any) -> list[str]:
    found: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)
        elif isinstance(value, str) and looks_like_path(value) and path_is_forbidden(value, []):
            found.append(value)

    walk(payload)
    return sorted(set(found))


def looks_like_path(value: str) -> bool:
    return "/" in value or "\\" in value or Path(value).suffix != ""


def raw_artifact_policy() -> str:
    return (
        "Do not commit raw Jasper logs, trace directories, generated harness dumps, "
        "license output, or large generated artifacts. Import only lightweight JSON "
        "manifests and Markdown summaries."
    )


def sanitized_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "created_utc",
        "host",
        "task_type",
        "summary",
        "cases",
        "metrics",
        "artifact",
        "source_handoff",
    )
    return {key: payload[key] for key in keys if key in payload}


def build_import_artifact_manifest(
    *,
    run_id: str,
    created_at: datetime,
    summary_path: Path,
) -> ArtifactManifest:
    return ArtifactManifest(
        manifest_id=run_id,
        run_id=run_id,
        generated_at=created_at,
        artifacts=[
            artifact_record(
                path=summary_path,
                key=summary_path.name,
                kind=ArtifactKind.REPORT,
                created_at=created_at,
            )
        ],
        metadata={
            "command": "jasperloop moore-handoff import-result",
            "external_calls_allowed": False,
            "raw_artifact_policy": raw_artifact_policy(),
            "claim_boundary": MOORE_CLAIM_BOUNDARY,
        },
    )


def build_core_run_manifest(
    *,
    run_id: str,
    created_at: datetime,
    git_sha: str,
    subcommand: str,
    out_dir: Path,
    stage5_manifest_path: Path,
    stage5_manifest: dict[str, Any],
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        created_at=created_at,
        git_sha=git_sha,
        dataset_version="stage5a-cli-wrapper",
        prompt_version="not_applicable",
        model_snapshot="none_external_calls_disabled",
        toolchain=ToolchainVersions(),
        artifacts_key=artifact_manifest_key(run_id),
        status=RunStatus.PASSED if stage5_manifest["dry_run"] else RunStatus.BLOCKED,
        metadata={
            "command": "jasperloop",
            "subcommand": subcommand,
            "dry_run": stage5_manifest["dry_run"],
            "created_at_utc": stage5_manifest["created_at_utc"],
            "out_dir": str(out_dir),
            "external_calls_allowed": False,
            "evidence_type": stage5_manifest["evidence_type"],
            "claim_boundary": CLAIM_BOUNDARY,
            "planned_internal_runner": stage5_manifest["planned_internal_runner"],
            "planned_internal_command": stage5_manifest["planned_internal_command"],
            "stage5_manifest": str(stage5_manifest_path),
        },
    )


def build_artifact_manifest(
    *,
    run_id: str,
    created_at: datetime,
    stage5_path: Path,
    core_run_path: Path,
) -> ArtifactManifest:
    records = [
        artifact_record(
            path=stage5_path,
            key="jasperloop_run_manifest.json",
            kind=ArtifactKind.RUN_MANIFEST,
            created_at=created_at,
        ),
        artifact_record(
            path=core_run_path,
            key="core_run_manifest.json",
            kind=ArtifactKind.RUN_MANIFEST,
            created_at=created_at,
        ),
    ]
    return ArtifactManifest(
        manifest_id=run_id,
        run_id=run_id,
        generated_at=created_at,
        artifacts=records,
        metadata={
            "command": "jasperloop",
            "external_calls_allowed": False,
            "claim_boundary": CLAIM_BOUNDARY,
        },
    )


def artifact_record(
    *,
    path: Path,
    key: str,
    kind: ArtifactKind,
    created_at: datetime,
) -> ArtifactRecord:
    payload = path.read_bytes()
    return ArtifactRecord(
        key=key,
        path=key,
        kind=kind,
        sha256=sha256_bytes(payload),
        size_bytes=len(payload),
        media_type="application/json",
        encoding=ArtifactEncoding.JSON,
        created_at=created_at,
        producer="jasperloop-cli",
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload) + b"\n")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def git_head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def git_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip() or "detached"


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
