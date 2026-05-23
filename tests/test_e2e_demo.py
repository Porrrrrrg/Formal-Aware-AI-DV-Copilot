from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.cli import main

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "examples" / "workflows" / "sva_repair_demo"
DEMO_CASE = DEMO_DIR / "demo_case.json"
FORBIDDEN_RAW_PATTERNS = ("*.log", "*.jou", "*.vcd", "*.fsdb")


def test_demo_fixture_loads() -> None:
    case = json.loads(DEMO_CASE.read_text(encoding="utf-8"))
    candidate = json.loads((DEMO_DIR / case["replay_candidate_path"]).read_text(encoding="utf-8"))
    verifier = json.loads((DEMO_DIR / case["verifier_outcome_path"]).read_text(encoding="utf-8"))

    assert case["case_id"] == "demo_repair_arbiter_mutex_syntax"
    assert case["evidence_context"]["evidence_kind"] == "structured_replay_context"
    assert set(candidate) == {"property_id", "sva", "explanation"}
    assert verifier["manifest_type"] == "VerifierOutcomeSample"
    assert verifier["raw_logs_included"] is False


def test_demo_repair_dry_run_emits_workflow_manifest(tmp_path: Path) -> None:
    exit_code = main(
        [
            "workflow",
            "repair",
            "--case",
            str(DEMO_CASE),
            "--backend",
            "replay",
            "--run-intent-alignment",
            "--prepare-moore-handoff",
            "--out-dir",
            str(tmp_path),
            "--dry-run",
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))
    candidate = json.loads((tmp_path / "repair_candidate.json").read_text(encoding="utf-8"))
    problem = json.loads((tmp_path / "problem_spec_stub.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["manifest_type"] == "WorkflowManifest"
    assert manifest["workflow_type"] == "repair"
    assert manifest["case_id"] == "demo_repair_arbiter_mutex_syntax"
    assert manifest["backend"] == "replay"
    assert manifest["verifier_required"] is True
    assert manifest["verifier_outcome_ref"]
    assert manifest["intent_alignment_ref"]
    assert manifest["cloud_fallback_called"] is False
    assert candidate["sva"].endswith(";")
    assert problem["metadata"]["evidence_context"]["evidence_kind"] == "structured_replay_context"


def test_final_demo_report_includes_claim_boundary(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_e2e_demo.py",
            "--out-dir",
            str(tmp_path / "workflow-demo"),
            "--reports-dir",
            str(reports_dir),
            "--timestamp",
            "20260511T000000Z",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    summary = reports_dir / "e2e_demo_summary_20260511T000000Z.md"
    manifest = json.loads((reports_dir / "e2e_demo_manifest_20260511T000000Z.json").read_text(encoding="utf-8"))
    text = summary.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "## Claim Boundary" in text
    assert "does not claim production readiness" in text
    assert manifest["codex_called"] is False
    assert manifest["qwen_called"] is False
    assert manifest["jaspergold_called"] is False
    assert manifest["moore_called"] is False


def test_demo_replay_does_not_call_external_backends(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_external(*args: object, **kwargs: object) -> object:
        raise AssertionError("external backend should not be called by replay demo")

    monkeypatch.setattr("app.workflow.call_local_task", fail_external)
    monkeypatch.setattr("app.local_llm_backend.request_json", fail_external)
    monkeypatch.setattr("copilot.llm_client.call_llm_json", fail_external)
    monkeypatch.setattr("tools.run_jasper.run", fail_external, raising=False)

    exit_code = main(
        [
            "workflow",
            "repair",
            "--case",
            str(DEMO_CASE),
            "--backend",
            "replay",
            "--run-intent-alignment",
            "--prepare-moore-handoff",
            "--out-dir",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0


def test_demo_fixtures_do_not_commit_raw_logs() -> None:
    for pattern in FORBIDDEN_RAW_PATTERNS:
        assert list(DEMO_DIR.rglob(pattern)) == []
