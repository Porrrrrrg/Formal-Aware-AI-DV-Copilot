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


def test_local_workflow_dry_run_does_not_call_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_endpoint(*args: object, **kwargs: object) -> object:
        raise AssertionError("local endpoint should not be called in dry-run")

    monkeypatch.setattr("app.local_llm_backend.request_json", fail_endpoint)

    for workflow_type in ("repair", "triage", "coverage"):
        out_dir = tmp_path / workflow_type
        exit_code = main(
            ["workflow", workflow_type, "--backend", "local", "--dry-run", "--out-dir", str(out_dir)]
        )
        manifest = json.loads((out_dir / "workflow_manifest.json").read_text(encoding="utf-8"))

        assert exit_code == 0
        assert manifest["backend"] == "local"
        assert manifest["workflow_type"] == workflow_type
        assert manifest["status"] == "dry_run"
        assert manifest["LOCAL_ONLY"] is True
        assert manifest["cloud_fallback_allowed"] is False
        assert manifest["cloud_fallback_called"] is False


def test_local_endpoint_unavailable_returns_structured_blocked_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_ONLY", "true")

    def unavailable(*args: object, **kwargs: object) -> tuple[int, dict[str, str]]:
        return 0, {"error": "connection refused"}

    monkeypatch.setattr("app.local_llm_backend.request_json", unavailable)
    monkeypatch.setattr("app.workflow.write_qwen_workflow_readiness_report", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "workflow",
            "repair",
            "--backend",
            "local",
            "--run-local-model",
            "--local-only",
            "--acknowledge-local-model-run",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 2
    assert manifest["status"] == "local_unavailable"
    assert manifest["blocked_reason"] == "local_unavailable"
    assert manifest["llm_error_count"] == 1
    assert manifest["cloud_fallback_called"] is False


def test_local_only_blocks_cloud_fallback_even_with_cloud_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_ONLY", "true")
    monkeypatch.setenv("CLOUD_OPENAI_API_KEY", "present")
    monkeypatch.setenv("CLOUD_OPENAI_MODEL", "gpt-cloud")
    monkeypatch.setattr("app.local_llm_backend.request_json", lambda *args, **kwargs: (0, {"error": "down"}))
    monkeypatch.setattr("app.workflow.write_qwen_workflow_readiness_report", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "workflow",
            "triage",
            "--backend",
            "local",
            "--run-local-model",
            "--local-only",
            "--acknowledge-local-model-run",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 2
    assert manifest["LOCAL_ONLY"] is True
    assert manifest["cloud_fallback_allowed"] is False
    assert manifest["cloud_fallback_called"] is False
    assert manifest["fallback_count"] == 0


def test_local_backend_cannot_run_without_explicit_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_ONLY", "true")

    def fail_endpoint(*args: object, **kwargs: object) -> object:
        raise AssertionError("local endpoint should be gated before any call")

    monkeypatch.setattr("app.local_llm_backend.request_json", fail_endpoint)

    exit_code = main(
        [
            "workflow",
            "coverage",
            "--backend",
            "local",
            "--run-local-model",
            "--local-only",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 2
    assert manifest["blocked_reason"] == "backend=local executable runs require --acknowledge-local-model-run"
    assert manifest["status"] == "blocked"


def test_local_manifest_includes_backend_model_endpoint_and_local_only_fields(tmp_path: Path) -> None:
    exit_code = main(
        [
            "workflow",
            "demo",
            "--backend",
            "local",
            "--dry-run",
            "--local-model",
            "Qwen/local-test",
            "--local-base-url",
            "http://127.0.0.1:8001/v1",
            "--local-backend-type",
            "vllm",
            "--local-max-model-len",
            "4096",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["backend"] == "local"
    assert manifest["model_id"] == "Qwen/local-test"
    assert manifest["endpoint_url"] == "http://127.0.0.1:8001/v1"
    assert manifest["backend_type"] == "vllm"
    assert manifest["max_model_len"] == 4096
    assert manifest["LOCAL_ONLY"] is True
    assert manifest["cloud_fallback_allowed"] is False


def test_mocked_local_response_passes_strict_repair_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_ONLY", "true")

    def mock_response(*args: object, **kwargs: object) -> tuple[int, dict[str, object]]:
        content = json.dumps(
            {
                "property_id": "p_mutex",
                "sva": "assert property (@(posedge clk) !(gnt0 && gnt1));",
                "explanation": "Repairs mutex assertion syntax.",
            }
        )
        return 200, {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr("app.local_llm_backend.request_json", mock_response)

    exit_code = main(
        [
            "workflow",
            "repair",
            "--backend",
            "local",
            "--run-local-model",
            "--local-only",
            "--acknowledge-local-model-run",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))
    candidate = json.loads((tmp_path / "repair_candidate.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["status"] == "ok"
    assert manifest["dry_run"] is False
    assert manifest["valid_json"] is True
    assert manifest["fallback_count"] == 0
    assert set(candidate) == {"property_id", "sva", "explanation"}


def test_local_invalid_json_does_not_fallback_to_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_ONLY", "true")
    monkeypatch.setattr(
        "app.local_llm_backend.request_json",
        lambda *args, **kwargs: (200, {"choices": [{"message": {"content": "not json"}}]}),
    )
    monkeypatch.setattr("app.workflow.write_qwen_workflow_readiness_report", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "workflow",
            "repair",
            "--backend",
            "local",
            "--run-local-model",
            "--local-only",
            "--acknowledge-local-model-run",
            "--out-dir",
            str(tmp_path),
        ]
    )
    manifest = json.loads((tmp_path / "workflow_manifest.json").read_text(encoding="utf-8"))

    assert exit_code == 2
    assert manifest["status"] == "invalid_json"
    assert manifest["blocked_reason"] == "invalid_json"
    assert manifest["fallback_count"] == 1
    assert manifest["cloud_fallback_called"] is False
    assert "local_response_invalid_json" in manifest["steps_executed"]
    assert not (tmp_path / "repair_candidate.json").exists()
