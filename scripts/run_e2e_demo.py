"""Run the Stage 5F offline end-to-end replay demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cli import main  # noqa: E402

DEMO_CASE = Path("examples/workflows/sva_repair_demo/demo_case.json")
DEFAULT_OUT_DIR = Path("artifacts/workflow-demo")
DEFAULT_REPORTS_DIR = Path("reports/workflows")
CLAIM_BOUNDARY = (
    "Stage 5F end-to-end demo evidence only. The replay demo loads local fixtures, "
    "prepares local manifests, imports a sanitized verifier sample, and runs static "
    "intent alignment. It does not call Codex, Qwen, JasperGold, Moore, or network "
    "services, and it does not claim production readiness."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the offline JasperLoop E2E replay demo.")
    parser.add_argument("--case", type=Path, default=DEMO_CASE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--timestamp", help="UTC timestamp suffix, e.g. 20260511T190000Z.")
    return parser


def run(args: argparse.Namespace) -> int:
    timestamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    command = [
        "workflow",
        "repair",
        "--case",
        str(args.case),
        "--backend",
        "replay",
        "--run-intent-alignment",
        "--prepare-moore-handoff",
        "--out-dir",
        str(args.out_dir),
        "--dry-run",
    ]
    exit_code = main(command)
    if exit_code != 0:
        return exit_code

    out_dir = resolve(args.out_dir)
    reports_dir = resolve(args.reports_dir)
    workflow_manifest_path = out_dir / "workflow_manifest.json"
    workflow_report_path = out_dir / "workflow_report.md"
    workflow_manifest = json.loads(workflow_manifest_path.read_text(encoding="utf-8"))

    report_manifest = {
        "schema_version": "stage5f.e2e_demo.v1",
        "timestamp_utc": timestamp,
        "command": ["python", "-m", "app.cli", *command],
        "workflow_manifest": display_path(workflow_manifest_path),
        "workflow_manifest_sha256": sha256_file(workflow_manifest_path),
        "workflow_report": display_path(workflow_report_path),
        "workflow_report_sha256": sha256_file(workflow_report_path),
        "backend": "replay",
        "external_backends_called": False,
        "codex_called": False,
        "qwen_called": False,
        "jaspergold_called": False,
        "moore_called": False,
        "network_used": False,
        "raw_logs_committed": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "workflow_status": workflow_manifest.get("status"),
        "workflow_artifact_refs": display_artifact_refs(workflow_manifest.get("artifact_refs", [])),
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = reports_dir / f"e2e_demo_manifest_{timestamp}.json"
    summary_path = reports_dir / f"e2e_demo_summary_{timestamp}.md"
    write_json(manifest_path, report_manifest)
    summary_path.write_text(summary_markdown(report_manifest), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "manifest": str(manifest_path)}, indent=2))
    return 0


def summary_markdown(manifest: dict[str, Any]) -> str:
    artifacts = "\n".join(
        f"- `{item.get('name')}`: `{item.get('path')}`"
        for item in manifest.get("workflow_artifact_refs", [])
        if isinstance(item, dict)
    )
    return (
        "# Stage 5F End-to-End Replay Demo Summary\n\n"
        f"- Timestamp UTC: `{manifest['timestamp_utc']}`\n"
        f"- Backend: `{manifest['backend']}`\n"
        f"- Workflow status: `{manifest['workflow_status']}`\n"
        f"- Workflow manifest: `{manifest['workflow_manifest']}`\n"
        f"- Workflow report: `{manifest['workflow_report']}`\n\n"
        "## Claim Boundary\n\n"
        f"{manifest['claim_boundary']}\n\n"
        "## External Call Boundary\n\n"
        "- Codex called: `false`\n"
        "- Qwen called: `false`\n"
        "- JasperGold called: `false`\n"
        "- Moore called: `false`\n"
        "- Network used: `false`\n\n"
        "## Workflow Artifacts\n\n"
        f"{artifacts}\n\n"
        "## Review Notes\n\n"
        "The imported verifier sample is sanitized demo context, not a new proof run. "
        "Intent alignment is a separate static review signal and is not a substitute "
        "for Jasper proof evidence.\n"
    )


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path | str) -> str:
    resolved = Path(path)
    if not resolved.is_absolute():
        return resolved.as_posix()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def display_artifact_refs(refs: Any) -> list[dict[str, Any]]:
    if not isinstance(refs, list):
        return []
    normalized = []
    for item in refs:
        if not isinstance(item, dict):
            continue
        ref = dict(item)
        if "path" in ref:
            ref["path"] = display_path(str(ref["path"]))
        normalized.append(ref)
    return normalized


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
