from __future__ import annotations

import json
from pathlib import Path

from evaluation import run_rtl2repair_eval


def write_tiny_arb(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "module tiny_arb(\n"
        "  input logic clk,\n"
        "  input logic rst,\n"
        "  input logic req0,\n"
        "  input logic req1,\n"
        "  output logic gnt0,\n"
        "  output logic gnt1\n"
        ");\n"
        "  assign gnt0 = req0;\n"
        "  assign gnt1 = req1;\n"
        "endmodule\n",
        encoding="utf-8",
    )
    return path


def replay_diff() -> str:
    return (
        "diff --git a/rtl/tiny_arb.sv b/rtl/tiny_arb.sv\n"
        "--- a/rtl/tiny_arb.sv\n"
        "+++ b/rtl/tiny_arb.sv\n"
        "@@ -8,4 +8,4 @@ module tiny_arb(\n"
        " );\n"
        "   assign gnt0 = req0;\n"
        "-  assign gnt1 = req1;\n"
        "+  assign gnt1 = req1 && !gnt0;\n"
        " endmodule\n"
    )


def invalid_replay_diff() -> str:
    return (
        "diff --git a/rtl/tiny_arb.sv b/rtl/tiny_arb.sv\n"
        "--- a/rtl/tiny_arb.sv\n"
        "+++ b/rtl/tiny_arb.sv\n"
        "@@ -8,4 +8,4 @@ module tiny_arb(\n"
        "-this hunk does not match\n"
        "+this hunk does not match either\n"
    )


def design2sva_candidate() -> dict[str, object]:
    return {
        "property_id": "p_rtl2repair_01",
        "sva": "p_rtl2repair_01: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
        "helper_code": "",
        "referenced_signals": ["gnt0", "gnt1"],
        "intent_summary": "Never grant both clients.",
        "source": "unknown",
        "repair_metadata": {
            "round": 0,
            "failure_category": "not_run",
            "feedback": "",
            "changed_by_repair": False,
        },
        "proof_metadata": {
            "backend": "jaspergold",
            "status": "not_run",
            "syntax_status": "not_run",
            "proof_status": None,
            "vacuity_status": None,
            "report_dir": None,
        },
    }


def replay_record(diff: str) -> dict[str, object]:
    return {
        "task": "rtl2repair",
        "case_id": "tiny_arb_rtl2repair",
        "design_id": "tiny_arb",
        "property_id": "p_rtl2repair_01",
        "issue_type": "rtl_design_bug",
        "response": {
            "schema_version": "rtl_repair_candidate_v1",
            "issue_type": "rtl_design_bug",
            "target_files": ["rtl/tiny_arb.sv"],
            "unified_diff": diff,
            "suspect_signals": ["gnt1"],
            "rationale": "Replay patch gates gnt1 when gnt0 is asserted.",
            "expected_effect": "Mutual exclusion target should close after patch.",
            "risk_notes": ["Unit-test replay patch."],
            "requires_recheck": True,
        },
    }


def write_replay(path: Path, diff: str) -> Path:
    path.write_text(json.dumps(replay_record(diff)) + "\n", encoding="utf-8")
    return path


def install_falsified_then_not_run(monkeypatch) -> None:
    monkeypatch.setattr(run_rtl2repair_eval, "generate_candidates", lambda *_args, **_kwargs: [design2sva_candidate()])
    monkeypatch.setattr(
        run_rtl2repair_eval,
        "propose_rtl_repair",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("replay should bypass proposal")),
    )

    def fake_check_generated_sva(**kwargs):
        if str(kwargs["system"]) == "rtl2repair_c0_r0":
            return {
                "syntax_pass": True,
                "proof_status": "falsified",
                "vacuity_status": None,
                "feedback": "reachable counterexample",
                "artifact_paths": {},
                "antecedent_reachable": True,
            }
        return {
            "syntax_pass": None,
            "proof_status": None,
            "vacuity_status": None,
            "feedback": "dry-run recheck",
            "artifact_paths": {},
            "antecedent_reachable": True,
        }

    monkeypatch.setattr(run_rtl2repair_eval, "check_generated_sva", fake_check_generated_sva)


def run_eval(tmp_path: Path, rtl: Path, replay: Path, out: Path) -> None:
    assert run_rtl2repair_eval.main(
        [
            "--rtl",
            str(rtl),
            "--top",
            "tiny_arb",
            "--clock",
            "clk",
            "--reset",
            "rst",
            "--reset-polarity",
            "active_high",
            "--intent",
            "The arbiter must never grant both clients in the same cycle.",
            "--k",
            "1",
            "--max-sva-rounds",
            "0",
            "--max-rtl-rounds",
            "1",
            "--rtl-repair-replay",
            str(replay),
            "--dry-run",
            "--out",
            str(out),
        ]
    ) == 0


def test_rtl_repair_replay_dry_run_applies_patch_but_does_not_accept(
    tmp_path: Path,
    monkeypatch,
) -> None:
    rtl = write_tiny_arb(tmp_path / "rtl" / "tiny_arb.sv")
    replay = write_replay(tmp_path / "rtl_repair_replay_outputs.jsonl", replay_diff())
    out = tmp_path / "run" / "rtl2repair_eval.json"
    install_falsified_then_not_run(monkeypatch)

    run_eval(tmp_path, rtl, replay, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    recheck = payload["patch_recheck"]
    assert recheck["attempted"] is True
    assert recheck["accepted"] is False
    assert recheck["status"] == "rejected"
    assert recheck["target_before"]["row"]["proof_metadata"]["proof_status"] == "falsified"
    assert recheck["target_after"]["formal_status"] == "not_run"
    assert recheck["acceptance_reason"] == "Target after recheck was not proven non-vacuous."
    assert payload["rtl_patch_candidate"]["unified_diff"] == replay_diff()
    patched_manifest = json.loads(Path(recheck["patched_manifest"]).read_text(encoding="utf-8"))
    assert "req1 && !gnt0" in Path(patched_manifest["rtl_files"][0]).read_text(encoding="utf-8")
    assert payload["metrics"]["rtl_patch_attempt_count"] == 1
    assert payload["metrics"]["rtl_patch_accept_count"] == 0


def test_rtl_repair_replay_invalid_diff_is_blocked(tmp_path: Path, monkeypatch) -> None:
    rtl = write_tiny_arb(tmp_path / "rtl" / "tiny_arb.sv")
    replay = write_replay(tmp_path / "rtl_repair_replay_outputs.jsonl", invalid_replay_diff())
    out = tmp_path / "run" / "rtl2repair_eval.json"
    install_falsified_then_not_run(monkeypatch)

    run_eval(tmp_path, rtl, replay, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    recheck = payload["patch_recheck"]
    assert recheck["attempted"] is True
    assert recheck["status"] == "blocked"
    assert recheck["target_before"]["row"]["proof_metadata"]["proof_status"] == "falsified"
    assert "git apply --check failed" in recheck["reason"]
