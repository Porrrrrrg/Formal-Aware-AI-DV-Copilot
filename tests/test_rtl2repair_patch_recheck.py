from __future__ import annotations

import json
from pathlib import Path

from evaluation import run_rtl2repair_eval
from tools.apply_rtl_patch import apply_rtl_patch
from tools.build_patched_manifest import build_patched_manifest


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


def arb_patch() -> str:
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


def manifest_for(tmp_path: Path, rtl: Path) -> dict[str, object]:
    return {
        "schema_version": "rtl_project_manifest_v1",
        "project_id": "tiny_arb",
        "design_id": "tiny_arb",
        "rtl_files": ["rtl/tiny_arb.sv"],
        "top_module": "tiny_arb",
        "clock_reset": {
            "clock": "clk",
            "clock_edge": "posedge",
            "reset": "rst",
            "reset_polarity": "active_high",
        },
        "include_dirs": [],
        "defines": {},
        "assumption_files": [],
        "property_module": "generated_sva_properties",
        "property_instance": "generated_properties_i",
        "visible_signals": ["clk", "rst", "req0", "req1", "gnt0", "gnt1"],
        "signal_roles": {"clock": ["clk"], "reset": ["rst"]},
        "harness": {"strategy": "render_generic", "harness_path": None},
        "_rtl_path_for_test": rtl.as_posix(),
        "_root_for_test": tmp_path.as_posix(),
    }


def candidate() -> dict[str, object]:
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


def test_build_patched_manifest_points_rtl_files_at_scratch(tmp_path: Path) -> None:
    rtl = write_tiny_arb(tmp_path / "rtl" / "tiny_arb.sv")
    original = manifest_for(tmp_path, rtl)
    original.pop("_rtl_path_for_test")
    original.pop("_root_for_test")
    apply_manifest = apply_rtl_patch(
        unified_diff=arb_patch(),
        allowed_patch_files=[rtl],
        scratch_dir=tmp_path / "scratch",
        repo_root=tmp_path,
    )

    patched = build_patched_manifest(
        original_manifest=original,
        applied_patch_manifest=apply_manifest,
        out_path=tmp_path / "patched_manifest.json",
    )

    patched_rtl = Path(str(patched["rtl_files"][0]))
    assert patched_rtl == tmp_path / "scratch" / "rtl" / "tiny_arb.sv"
    assert "req1 && !gnt0" in patched_rtl.read_text(encoding="utf-8")


def test_rtl2repair_rechecks_non_empty_patch_on_patched_manifest(tmp_path: Path, monkeypatch) -> None:
    rtl = write_tiny_arb(tmp_path / "rtl" / "tiny_arb.sv")
    out = tmp_path / "run" / "rtl2repair_eval.json"

    monkeypatch.setattr(run_rtl2repair_eval, "generate_candidates", lambda *_args, **_kwargs: [candidate()])

    def fake_check_generated_sva(**kwargs):
        system = str(kwargs["system"])
        if system == "rtl2repair_c0_r0":
            return {
                "syntax_pass": True,
                "proof_status": "falsified",
                "vacuity_status": None,
                "feedback": "reachable counterexample",
                "artifact_paths": {},
                "antecedent_reachable": True,
            }
        return {
            "syntax_pass": True,
            "proof_status": "proven",
            "vacuity_status": "non_vacuous",
            "feedback": "",
            "artifact_paths": {},
            "antecedent_reachable": True,
        }

    monkeypatch.setattr(run_rtl2repair_eval, "check_generated_sva", fake_check_generated_sva)
    monkeypatch.setattr(
        run_rtl2repair_eval,
        "propose_rtl_repair",
        lambda **_kwargs: {
            "schema_version": "rtl_repair_candidate_v1",
            "issue_type": "rtl_design_bug",
            "target_files": [rtl.as_posix()],
            "unified_diff": arb_patch(),
            "suspect_signals": ["gnt1"],
            "rationale": "Counterexample shows simultaneous grants.",
            "expected_effect": "Gate gnt1 when gnt0 is asserted.",
            "risk_notes": ["Unit-test patch."],
            "requires_recheck": True,
        },
    )

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
            "--jasper-check",
            "--out",
            str(out),
        ]
    ) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    recheck = payload["patch_recheck"]
    assert recheck["status"] == "accepted"
    assert recheck["accepted"] is True
    assert recheck["target_check"]["formal_status"] == "ran"
    assert payload["metrics"]["rtl_patch_attempt_count"] == 1
    assert payload["metrics"]["rtl_patch_accept_count"] == 1
    patched_manifest = json.loads(Path(recheck["patched_manifest"]).read_text(encoding="utf-8"))
    assert "req1 && !gnt0" in Path(patched_manifest["rtl_files"][0]).read_text(encoding="utf-8")


def test_rtl2repair_recheck_includes_regression_candidates_file(tmp_path: Path, monkeypatch) -> None:
    rtl = write_tiny_arb(tmp_path / "rtl" / "tiny_arb.sv")
    out = tmp_path / "run" / "rtl2repair_eval.json"
    regressions = tmp_path / "regression_candidates.json"
    regressions.write_text(
        json.dumps(
            [
                {
                    "property_id": "p_no_spurious_gnt0",
                    "sva": "p_no_spurious_gnt0: assert property (@(posedge clk) disable iff (rst) gnt0 |-> req0);",
                    "helper_code": "",
                    "source": "regression_suite",
                },
                {
                    "property_id": "p_mutex",
                    "sva": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
                    "helper_code": "",
                    "source": "regression_suite",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(run_rtl2repair_eval, "generate_candidates", lambda *_args, **_kwargs: [candidate()])

    def fake_check_generated_sva(**kwargs):
        system = str(kwargs["system"])
        if system == "rtl2repair_c0_r0":
            return {
                "syntax_pass": True,
                "proof_status": "falsified",
                "vacuity_status": None,
                "feedback": "reachable counterexample",
                "artifact_paths": {},
                "antecedent_reachable": True,
            }
        return {
            "syntax_pass": True,
            "proof_status": "proven",
            "vacuity_status": "non_vacuous",
            "feedback": "",
            "artifact_paths": {},
            "antecedent_reachable": True,
        }

    monkeypatch.setattr(run_rtl2repair_eval, "check_generated_sva", fake_check_generated_sva)
    monkeypatch.setattr(
        run_rtl2repair_eval,
        "propose_rtl_repair",
        lambda **_kwargs: {
            "schema_version": "rtl_repair_candidate_v1",
            "issue_type": "rtl_design_bug",
            "target_files": [rtl.as_posix()],
            "unified_diff": arb_patch(),
            "suspect_signals": ["gnt1"],
            "rationale": "Counterexample shows simultaneous grants.",
            "expected_effect": "Gate gnt1 when gnt0 is asserted.",
            "risk_notes": ["Unit-test patch."],
            "requires_recheck": True,
        },
    )

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
            "--regression-candidates",
            str(regressions),
            "--jasper-check",
            "--out",
            str(out),
        ]
    ) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    recheck = payload["patch_recheck"]
    assert recheck["status"] == "accepted"
    assert recheck["metrics"]["regression_total"] == 2
    assert recheck["metrics"]["regression_pass_count"] == 2
    assert [item["source"] for item in recheck["regression_checks"]] == [
        "regression_candidates_file",
        "regression_candidates_file",
    ]
    assert [item["property_id"] for item in recheck["regression_checks"]] == [
        "p_no_spurious_gnt0",
        "p_mutex",
    ]
