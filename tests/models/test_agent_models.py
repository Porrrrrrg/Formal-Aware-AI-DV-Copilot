from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from app.models.agent import (
    AgentRunManifest,
    BackendResult,
    BackendStatus,
    EvidencePacket,
    Task,
)

ROOT = Path(__file__).resolve().parents[2]


def test_evidence_packet_model_validates_against_committed_schema() -> None:
    packet = EvidencePacket(
        case_id="case0",
        design_id="rv_buffer",
        task_type="failure_triage",
        allowed_issue_types=["rtl_design_bug"],
        allowed_next_actions=["fix_rtl"],
        jasper_result={"summary": {"counts_by_status": {"falsified": 1}}},
    )
    schema = json.loads((ROOT / "copilot/schemas/evidence_packet.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(packet.to_dict()))
    assert errors == []


def test_backend_result_legacy_check_dict_preserves_eval_contract() -> None:
    result = BackendResult(status=BackendStatus.DRY_RUN, report_dir="jasper/reports/demo")
    legacy = result.to_legacy_check_dict()

    assert legacy["syntax_pass"] is None
    assert legacy["report_dir"] == "jasper/reports/demo"
    assert "backend_status" in legacy


def test_agent_run_manifest_round_trips() -> None:
    manifest = AgentRunManifest(
        run_id="agent_run_0",
        created_at=datetime.now(timezone.utc),
        task=Task(task_id="task0", task_type="sva_repair"),
        backend_results=[BackendResult(status=BackendStatus.PASSED)],
        status="passed",
    )
    assert AgentRunManifest.model_validate(manifest.to_dict()).run_id == "agent_run_0"
