from __future__ import annotations

import json
from pathlib import Path

from tools.check_generated_sva import check_generated_sva


def test_design2sva_dry_run_preserves_embedding_artifacts_and_paths(tmp_path: Path) -> None:
    native = (
        "p_native_mutex: assert property "
        "(@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"
    )
    reference = (
        "p_mutex: assert property "
        "(@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"
    )
    cover = (
        "cov_p_mutex_antecedent: cover property "
        "(@(posedge clk) disable iff (rst) (gnt0 && gnt1));"
    )
    case = {
        "case_id": "design2sva_arbiter_mutex",
        "design_id": "arbiter_rr2",
        "property_id": "p_mutex",
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
        "original_native_property_expression": native,
        "evaluation_metadata": {"reference_sva": reference},
    }
    prediction = {
        "property_id": "p_mutex",
        "sva": reference,
        "helper_code": "",
        "metadata": {"cover_sva": cover},
    }

    result = check_generated_sva(
        case=case,
        prediction=prediction,
        system="audit_test",
        out_root=tmp_path,
        dry_run=True,
    )

    artifact_paths = result["artifact_paths"]
    report_dir = Path(str(result["report_dir"]))
    debug_dir = Path(str(artifact_paths["debug_artifact_dir"]))
    assert debug_dir.parent == report_dir
    assert Path(str(artifact_paths["generated_properties"])).is_file()
    assert Path(str(artifact_paths["generated_harness"])).is_file()
    assert Path(str(artifact_paths["candidate_json"])).is_file()
    assert Path(str(artifact_paths["run_command"])).is_file()
    assert Path(str(artifact_paths["tcl_path"])).is_file()
    assert Path(str(artifact_paths["tcl_snapshot"])).is_file()
    debug_properties = Path(str(artifact_paths["debug_generated_properties"]))
    generated_properties = Path(str(artifact_paths["generated_properties"]))
    debug_harness = Path(str(artifact_paths["debug_generated_harness"]))
    generated_harness = Path(str(artifact_paths["generated_harness"]))
    debug_candidate_json = Path(str(artifact_paths["debug_candidate_json"]))
    generated_properties_text = generated_properties.read_text(encoding="utf-8")
    generated_harness_text = generated_harness.read_text(encoding="utf-8")
    assert debug_properties.read_text(encoding="utf-8") == generated_properties.read_text(
        encoding="utf-8"
    )
    assert debug_harness.read_text(encoding="utf-8") == generated_harness.read_text(
        encoding="utf-8"
    )
    assert json.loads(debug_candidate_json.read_text(encoding="utf-8")) == prediction

    run_metadata = json.loads(
        Path(str(artifact_paths["run_metadata_json"])).read_text(encoding="utf-8")
    )
    assert run_metadata["tcl_path"] == artifact_paths["tcl_path"]
    assert (
        run_metadata["jasperloop_env"]["JASPERLOOP_GENERATED_PROPERTIES"]
        == artifact_paths["generated_properties"]
    )
    assert (
        run_metadata["jasperloop_env"]["JASPERLOOP_GENERATED_HARNESS"]
        == artifact_paths["generated_harness"]
    )
    assert run_metadata["jasperloop_env"]["JASPERLOOP_TOP"] == "arbiter_rr2_harness"
    assert run_metadata["jasperloop_env"]["JASPERLOOP_PROPERTY_MODULE"] == (
        "arbiter_rr2_properties"
    )
    assert run_metadata["jasperloop_env"]["JASPERLOOP_FORMAL_MODE"] == "prove"
    assert "module arbiter_rr2_properties" in generated_properties_text
    assert "module arbiter_rr2_harness" in generated_harness_text
    assert "arbiter_rr2_assumptions assumptions_i" in generated_harness_text
    assert "arbiter_rr2_properties properties_i" in generated_harness_text

    audit_path = Path(str(artifact_paths["embedding_audit_json"]))
    markdown_path = Path(str(artifact_paths["embedding_audit_markdown"]))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["schema_version"] == "stage12_wrapper_parity_audit_v1"
    assert audit["comparison"]["original_native_property_expression"] == native
    assert audit["comparison"]["reference_sva"] == case["evaluation_metadata"]["reference_sva"]
    assert audit["comparison"]["embedded_candidate_sva"] == prediction["sva"]
    assert audit["comparison"]["generated_cover_before_assert_sva"] == cover
    assert audit["native_flow"]["top_module"] == "arbiter_rr2_harness"
    assert audit["wrapper_flow"]["generated_harness_source"] == (
        "benchmarks/arbiter_rr2/formal/arbiter_rr2_harness.sv"
    )
    assert audit["wrapper_parity"]["parity_pass"] is True
    assert audit["wrapper_parity"]["critical_checks"]["assumptions_path_match"] is True
    assert audit["wrapper_parity"]["critical_checks"]["property_instance_connected"] is True
    assert audit["root_cause_detail"] == "wrapper_reuses_native_harness_with_prove_mode"
    assert audit["artifact_paths"] == artifact_paths
    assert result["embedding_audit"]["artifact_paths"] == artifact_paths
    assert all(flag is False for flag in audit["issue_flags"].values())
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Candidate Embedding Audit" in markdown
    assert "Wrapper Parity" in markdown


def test_design2sva_wrapper_labels_unlabeled_candidate_with_property_id(
    tmp_path: Path,
) -> None:
    case = {
        "case_id": "design2sva_arbiter_mutex",
        "design_id": "arbiter_rr2",
        "property_id": "p_mutex",
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
    }
    prediction = {
        "property_id": "p_mutex",
        "sva": "assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
        "helper_code": "",
    }

    result = check_generated_sva(
        case=case,
        prediction=prediction,
        system="unlabeled_candidate",
        out_root=tmp_path,
        dry_run=True,
    )

    generated_properties = Path(str(result["artifact_paths"]["generated_properties"]))
    assert (
        "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"
        in generated_properties.read_text(encoding="utf-8")
    )


def test_design2sva_embedding_audit_flags_string_level_issues(tmp_path: Path) -> None:
    reference = (
        "p_in_ready_when_full_and_out_ready: assert property "
        "(@(posedge clk) disable iff (rst) full && out_ready |-> in_ready);"
    )
    bad_sva = (
        "p_bad: assert property "
        "(@(posedge pclk) disable iff (!presetn) full |-> in_ready); "
        "module bad_helper; endmodule"
    )
    case = {
        "case_id": "design2sva_rv_buffer_ready_full",
        "design_id": "rv_buffer",
        "property_id": "p_in_ready_when_full_and_out_ready",
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
        "evaluation_metadata": {"reference_sva": reference},
    }
    prediction = {
        "property_id": "p_in_ready_when_full_and_out_ready",
        "sva": bad_sva,
        "helper_code": "logic seen_full;",
        "metadata": {
            "top_module": "rv_buffer",
            "generated_properties_path": "wrong/generated_properties.sv",
            "cover_sva": "p_bad: cover property (@(posedge pclk) disable iff (!presetn) (full));",
        },
    }

    result = check_generated_sva(
        case=case,
        prediction=prediction,
        system="audit_flags",
        out_root=tmp_path,
        dry_run=True,
    )

    audit = json.loads(
        Path(str(result["artifact_paths"]["embedding_audit_json"])).read_text(encoding="utf-8")
    )
    checks = audit["checks"]
    expected_checks = {
        "label_collisions",
        "wrong_top_module",
        "missing_bind_or_instantiation",
        "wrong_include_or_path_metadata",
        "clock_reset_mismatch",
        "disable_iff_mismatch",
        "helper_code_placement",
    }
    assert expected_checks <= set(checks)
    assert checks["label_collisions"]["has_issue"] is True
    assert checks["label_collisions"]["duplicate_embedded_labels"] == ["p_bad"]
    assert checks["wrong_top_module"]["has_issue"] is True
    assert checks["wrong_include_or_path_metadata"]["has_issue"] is True
    assert checks["clock_reset_mismatch"]["has_issue"] is True
    assert checks["disable_iff_mismatch"]["has_issue"] is True
    assert checks["helper_code_placement"]["has_issue"] is True
    assert checks["missing_bind_or_instantiation"]["has_issue"] is False


def test_design2sva_cover_prediction_uses_cover_formal_mode(tmp_path: Path) -> None:
    case = {
        "case_id": "design2sva_rv_buffer_ready_full",
        "design_id": "rv_buffer",
        "property_id": "p_in_ready_when_full_and_out_ready",
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
    }
    prediction = {
        "property_id": "cov_p_in_ready_when_full_and_out_ready_antecedent",
        "sva": (
            "cov_p_in_ready_when_full_and_out_ready_antecedent: cover property "
            "(@(posedge clk) disable iff (rst) (full && out_ready));"
        ),
        "helper_code": "",
        "check_kind": "cover",
    }

    result = check_generated_sva(
        case=case,
        prediction=prediction,
        system="cover_mode",
        out_root=tmp_path,
        dry_run=True,
    )

    artifact_paths = result["artifact_paths"]
    run_metadata = json.loads(
        Path(str(artifact_paths["run_metadata_json"])).read_text(encoding="utf-8")
    )
    audit = json.loads(
        Path(str(artifact_paths["embedding_audit_json"])).read_text(encoding="utf-8")
    )

    assert run_metadata["jasperloop_env"]["JASPERLOOP_FORMAL_MODE"] == "cover"
    assert audit["wrapper_flow"]["formal_mode"] == "cover"
    assert audit["root_cause_detail"] == "wrapper_reuses_native_harness_with_cover_mode"
    tcl = Path(str(artifact_paths["tcl_snapshot"])).read_text(encoding="utf-8")
    assert "prove -all" in tcl
    assert "cover -all" not in tcl


def test_design2sva_dry_run_ignores_stale_jasper_reports(tmp_path: Path) -> None:
    case = {
        "case_id": "design2sva_arbiter_mutex",
        "design_id": "arbiter_rr2",
        "property_id": "p_mutex",
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
    }
    prediction = {
        "property_id": "p_mutex",
        "sva": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
        "helper_code": "",
    }
    stale_dir = tmp_path / "stale_report" / "design2sva_arbiter_mutex"
    stale_dir.mkdir(parents=True)
    (stale_dir / "properties.rpt").write_text("p_mutex proven\n", encoding="utf-8")
    (stale_dir / "vacuity.rpt").write_text("p_mutex vacuous\n", encoding="utf-8")

    result = check_generated_sva(
        case=case,
        prediction=prediction,
        system="stale_report",
        out_root=tmp_path,
        dry_run=True,
    )

    assert result["syntax_pass"] is None
    assert result["proof_status"] is None
    assert result["vacuity_status"] is None
