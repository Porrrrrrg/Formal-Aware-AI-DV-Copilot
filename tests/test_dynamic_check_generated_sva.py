from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.check_generated_sva import check_generated_sva
from tools.rtl_project_intake import create_rtl_project

ROOT = Path(__file__).resolve().parents[1]


def write_rtl(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
module tiny_arb(
  input logic clk,
  input logic rst,
  input logic req0,
  input logic req1,
  output logic gnt0,
  output logic gnt1
);
  logic turn;
  assign gnt0 = req0 && !turn;
  assign gnt1 = req1 && turn;
endmodule
""",
        encoding="utf-8",
    )
    return path


def build_manifest(tmp_path: Path) -> Path:
    rtl = write_rtl(tmp_path / "rtl" / "tiny_arb.sv")
    out = tmp_path / "intake" / "rtl_project_manifest.json"
    create_rtl_project(
        rtl_inputs=[str(rtl)],
        out_path=out,
        top="tiny_arb",
        clock="clk",
        reset="rst",
        reset_polarity="active_high",
        cwd=tmp_path,
    )
    return out


def dynamic_case() -> dict[str, object]:
    return {
        "case_id": "tiny_arb_mutex",
        "design_id": "tiny_arb",
        "property_id": "p_mutex",
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
    }


def dynamic_prediction() -> dict[str, object]:
    return {
        "property_id": "p_mutex",
        "sva": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
        "helper_code": "",
    }


def test_dynamic_manifest_dry_run_writes_debug_artifacts(tmp_path: Path) -> None:
    manifest = build_manifest(tmp_path)

    result = check_generated_sva(
        case=dynamic_case(),
        prediction=dynamic_prediction(),
        system="dynamic",
        out_root=tmp_path / "reports",
        dry_run=True,
        design_manifest=manifest,
    )

    artifacts = result["artifact_paths"]
    generated_properties = Path(str(artifacts["generated_properties"]))
    generated_harness = Path(str(artifacts["generated_harness"]))
    audit_path = Path(str(artifacts["embedding_audit_json"]))
    debug_manifest = Path(str(artifacts["debug_rtl_project_manifest"]))

    assert generated_properties.is_file()
    assert generated_harness.is_file()
    assert audit_path.is_file()
    assert debug_manifest.is_file()
    assert artifacts["rtl_project_manifest"] == str(manifest.resolve())
    assert artifacts["dynamic_harness_strategy"] == "render_generic"
    assert json.loads(debug_manifest.read_text(encoding="utf-8"))["top_module"] == "tiny_arb"

    properties_text = generated_properties.read_text(encoding="utf-8")
    harness_text = generated_harness.read_text(encoding="utf-8")
    assert "module generated_sva_properties" in properties_text
    assert "input logic gnt0" in properties_text
    assert "module tiny_arb_generated_harness" in harness_text
    assert "tiny_arb dut (" in harness_text
    assert ".clk(clk)" in harness_text
    assert ".*" not in harness_text
    assert "generated_sva_properties generated_properties_i (" in harness_text
    assert ".turn(dut.turn)" in harness_text

    run_metadata = json.loads(Path(str(artifacts["run_metadata_json"])).read_text(encoding="utf-8"))
    env = run_metadata["jasperloop_env"]
    assert env["JASPERLOOP_TOP"] == "tiny_arb_generated_harness"
    assert "tiny_arb.sv" in env["JASPERLOOP_RTL_FILES"]
    assert env["JASPERLOOP_ASSUMPTIONS"] == ""

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["wrapper_flow"]["generated_harness_source"] == "render_generic"
    assert audit["wrapper_parity"]["parity_pass"] is True


def test_dynamic_manifest_cli_dry_run(tmp_path: Path) -> None:
    manifest = build_manifest(tmp_path)
    case_path = tmp_path / "case.json"
    prediction_path = tmp_path / "prediction.json"
    case_path.write_text(json.dumps(dynamic_case()), encoding="utf-8")
    prediction_path.write_text(json.dumps(dynamic_prediction()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "check_generated_sva.py"),
            "--case",
            str(case_path),
            "--prediction",
            str(prediction_path),
            "--design-manifest",
            str(manifest),
            "--system",
            "cli_dynamic",
            "--out-root",
            str(tmp_path / "cli_reports"),
            "--dry-run",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["syntax_pass"] is None
    assert Path(result["artifact_paths"]["generated_harness"]).is_file()
