from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.cli import main


def test_workflow_help_lists_subcommands() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "workflow", "--help"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "jasperloop workflow" in result.stdout
    for subcommand in ("repair", "triage", "coverage", "demo"):
        assert subcommand in result.stdout


def test_workflow_repair_dry_run_returns_zero(tmp_path: Path) -> None:
    exit_code = main(["workflow", "repair", "--dry-run", "--out-dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "workflow_report.md").exists()


def test_workflow_repair_dry_run_emits_workflow_manifest(tmp_path: Path) -> None:
    exit_code = main(["workflow", "repair", "--dry-run", "--out-dir", str(tmp_path)])
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["manifest_type"] == "WorkflowManifest"
    assert manifest["workflow_type"] == "repair"
    assert manifest["case_id"] == "repair_arbiter_mutex_syntax"
    assert manifest["backend"] == "replay"
    assert manifest["dry_run"] is True
    assert manifest["external_send_allowed"] is False
    assert manifest["local_only"] is True
    assert "prepare_candidate_stub_or_replay_candidate" in manifest["steps_executed"]
    assert manifest["final_report_ref"]
    assert manifest["claim_boundary"]


def test_workflow_dry_run_does_not_call_model_or_jasper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_model(*args: object, **kwargs: object) -> object:
        raise AssertionError("model call should not happen in workflow dry-run")

    def fail_jasper(*args: object, **kwargs: object) -> object:
        raise AssertionError("Jasper call should not happen in workflow dry-run")

    monkeypatch.setattr("copilot.llm_client.call_llm_json", fail_model)
    monkeypatch.setattr("tools.run_jasper.run", fail_jasper, raising=False)

    exit_code = main(["workflow", "repair", "--dry-run", "--out-dir", str(tmp_path)])

    assert exit_code == 0


def test_workflow_external_backend_without_ack_is_blocked(tmp_path: Path) -> None:
    exit_code = main(
        [
            "workflow",
            "repair",
            "--dry-run",
            "--backend",
            "codex",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 2
    assert manifest["blocked_reason"] == "backend=codex is external and requires --require-explicit-external-send"
    assert manifest["external_send_allowed"] is False
    assert manifest["steps_executed"] == ["block_external_backend_without_acknowledgement"]


def test_workflow_with_imported_verifier_result_can_call_intent_alignment(tmp_path: Path) -> None:
    verifier = tmp_path / "verifier_result.json"
    verifier.write_text(
        json.dumps({"status": "passed", "ok": True, "tool": "jaspergold"}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "workflow",
            "repair",
            "--dry-run",
            "--out-dir",
            str(tmp_path),
            "--verifier-result",
            str(verifier),
            "--run-intent-alignment",
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))
    alignment = json.loads((tmp_path / "intent_alignment_result.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["verifier_outcome_ref"]
    assert manifest["intent_alignment_ref"]
    assert "run_intent_alignment_if_requested_and_available" in manifest["steps_executed"]
    assert alignment["proof_status_context"]["status"] == "passed"


def test_packet_workflow_prepare_moore_handoff_emits_artifact(tmp_path: Path) -> None:
    exit_code = main(
        [
            "workflow",
            "triage",
            "--dry-run",
            "--out-dir",
            str(tmp_path),
            "--prepare-moore-handoff",
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["verifier_required"] is True
    assert "prepare_moore_handoff_manifest_if_requested" in manifest["steps_executed"]
    assert any(item["name"] == "moore_handoff_manifest" for item in manifest["artifact_refs"])
    assert (tmp_path / "moore_handoff_manifest.json").exists()


def test_packet_workflow_imports_verifier_result(tmp_path: Path) -> None:
    verifier = tmp_path / "verifier_result.json"
    verifier.write_text(json.dumps({"status": "packet_valid", "schema_valid": True}), encoding="utf-8")

    exit_code = main(
        [
            "workflow",
            "coverage",
            "--dry-run",
            "--out-dir",
            str(tmp_path),
            "--verifier-result",
            str(verifier),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["verifier_outcome_ref"]
    assert "import_verifier_outcome_if_available" in manifest["steps_executed"]
    assert (tmp_path / "imported_verifier_outcome.json").exists()


def test_workflow_final_report_includes_claim_boundary(tmp_path: Path) -> None:
    exit_code = main(["workflow", "repair", "--dry-run", "--out-dir", str(tmp_path)])
    report = (tmp_path / "workflow_report.md").read_text(encoding="utf-8")

    assert exit_code == 0
    assert "## Claim Boundary" in report
    assert "A proof pass does not imply semantic intent alignment." in report
