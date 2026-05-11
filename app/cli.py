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

ROOT = Path(__file__).resolve().parents[1]

CLAIM_BOUNDARY = (
    "Stage 5A CLI wrapper evidence only. This command records the planned local "
    "runner/script and dry-run safety posture; it does not change Stage 2/3/4 "
    "reports, benchmark labels, schemas, or prior result semantics."
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
        planned_runner="scripts/run_moore_codex_repair_final_proof.sh",
        planned_args=("--dry-run",),
        description="Plan Moore handoff without invoking Moore, JasperGold, or model calls.",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_command(args, argv if argv is not None else sys.argv[1:])


def run_command(args: argparse.Namespace, argv: list[str]) -> int:
    subcommand = str(args.subcommand)
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
    elif spec.planned_runner.endswith("run_moore_codex_repair_final_proof.sh"):
        command.extend(["--manifest-out", str(out_dir / "moore_handoff_manifest.json")])
    else:
        command.extend(["--out", str(out_dir / "runner_output.json")])
    return command


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


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
