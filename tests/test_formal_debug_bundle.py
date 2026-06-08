from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.build_formal_debug_bundle import build_formal_debug_bundle, main

ROOT = Path(__file__).resolve().parents[1]


def schema_validator() -> Draft202012Validator:
    schema = json.loads(
        (ROOT / "copilot" / "schemas" / "formal_debug_bundle.schema.json").read_text(
            encoding="utf-8"
        )
    )
    return Draft202012Validator(schema)


def base_check_result() -> dict[str, object]:
    return {
        "syntax_pass": None,
        "proof_status": None,
        "vacuity_status": None,
        "feedback": "",
        "report_dir": "reports/case",
        "artifact_paths": {
            "report_dir": "reports/case",
            "embedding_audit_json": "reports/case/embedding_audit/embedding_audit.json",
            "embedding_audit_markdown": "reports/case/embedding_audit/embedding_audit.md",
            "generated_properties": "reports/case/generated_properties.sv",
            "generated_harness": "reports/case/generated_harness.sv",
            "run_command": "reports/case/run_command.txt",
            "log": "reports/case/jg.log",
            "properties_report": "reports/case/properties.rpt",
            "cover_report": "reports/case/cover.rpt",
            "vacuity_report": "reports/case/vacuity.rpt",
            "candidate_json": "reports/case/candidate_sva.json",
            "rtl_project_manifest": "artifacts/intake/rtl_project_manifest.json",
        },
    }


def base_audit(issue_flags: dict[str, bool] | None = None) -> dict[str, object]:
    flags = issue_flags or {}
    return {
        "case_id": "case0",
        "design_id": "tiny",
        "property_id": "p0",
        "issues": [name for name, flagged in flags.items() if flagged],
        "issue_flags": flags,
        "comparison": {
            "embedded_candidate_sva": "p0: assert property (@(posedge clk) disable iff (rst) ok);"
        },
        "wrapper_parity": {"parity_pass": not any(flags.values())},
    }


def test_bundle_recommends_sva_for_clock_reset_issue() -> None:
    bundle = build_formal_debug_bundle(
        check_result=base_check_result(),
        embedding_audit=base_audit({"clock_reset_mismatch": True}),
        candidate={"property_id": "p0", "sva": "p0: assert property (bad);"},
    )

    schema_validator().validate(bundle)
    assert bundle["root_cause_signals"]["clock_reset_mismatch"] is True
    assert bundle["repair_recommendation"]["next_owner"] == "sva"


def test_bundle_recommends_harness_for_missing_bind_issue() -> None:
    bundle = build_formal_debug_bundle(
        check_result=base_check_result(),
        embedding_audit=base_audit({"missing_bind_or_instantiation": True}),
        candidate={"property_id": "p0", "sva": "p0: assert property (bad);"},
    )

    assert bundle["repair_recommendation"]["next_owner"] == "harness"
    assert "generated_harness" in bundle["debug_artifacts"]


def test_bundle_recommends_rtl_for_falsified_reachable_property() -> None:
    check_result = {
        **base_check_result(),
        "syntax_pass": True,
        "proof_status": "falsified",
        "vacuity_status": "non_vacuous",
        "antecedent_reachable": True,
    }
    bundle = build_formal_debug_bundle(
        check_result=check_result,
        embedding_audit=base_audit({}),
        candidate={"property_id": "p0", "sva": "p0: assert property (bad);"},
    )

    assert bundle["status"]["syntax_status"] == "ok"
    assert bundle["root_cause_signals"]["antecedent_reachable"] is True
    assert bundle["repair_recommendation"]["next_owner"] == "rtl"


def test_cli_writes_bundle_from_check_result_paths(tmp_path: Path) -> None:
    audit_path = tmp_path / "embedding_audit.json"
    candidate_path = tmp_path / "candidate.json"
    check_path = tmp_path / "check.json"
    out_path = tmp_path / "formal_debug_bundle.json"
    audit_path.write_text(json.dumps(base_audit({"helper_code_placement": True})), encoding="utf-8")
    candidate_path.write_text(
        json.dumps({"property_id": "p0", "sva": "p0: assert property (bad);"}),
        encoding="utf-8",
    )
    check = base_check_result()
    check["artifact_paths"]["embedding_audit_json"] = str(audit_path)
    check["artifact_paths"]["candidate_json"] = str(candidate_path)
    check_path.write_text(json.dumps(check), encoding="utf-8")

    assert main(["--check-result", str(check_path), "--out", str(out_path)]) == 0

    bundle = json.loads(out_path.read_text(encoding="utf-8"))
    assert bundle["repair_recommendation"]["next_owner"] == "sva"
