from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.rtl_project_intake import IntakeError, create_rtl_project

ROOT = Path(__file__).resolve().parents[1]


def write_rtl(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def load_schema(name: str) -> dict[str, object]:
    data = json.loads((ROOT / "copilot" / "schemas" / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_single_module_intake_emits_manifest_tasks_and_report(tmp_path: Path) -> None:
    rtl = write_rtl(
        tmp_path / "rtl" / "unit.sv",
        """
module unit(
  input logic clk,
  input logic rst,
  input logic in_valid,
  output logic in_ready,
  output logic [1:0] gnt
);
  logic full;
  assign in_ready = !full;
endmodule
""",
    )

    out = tmp_path / "artifacts" / "rtl_project_manifest.json"
    outputs = create_rtl_project(rtl_inputs=[str(rtl)], out_path=out, cwd=tmp_path)

    assert out.exists()
    assert outputs.tasks_path.exists()
    assert outputs.report_path.exists()
    assert outputs.rtl_index_path.exists()
    assert outputs.manifest["schema_version"] == "rtl_project_manifest_v1"
    assert outputs.manifest["top_module"] == "unit"
    assert outputs.manifest["clock_reset"] == {
        "clock": "clk",
        "clock_edge": "posedge",
        "reset": "rst",
        "reset_polarity": "unknown",
    }
    assert {"clk", "rst", "in_valid", "in_ready"} <= set(outputs.manifest["visible_signals"])
    assert outputs.tasks["tasks"]

    Draft202012Validator(load_schema("rtl_project_manifest.schema.json")).validate(outputs.manifest)
    task_schema = Draft202012Validator(load_schema("rtl2sva_task.schema.json"))
    for task in outputs.tasks["tasks"]:
        task_schema.validate(task)


def test_ambiguous_top_requires_explicit_top(tmp_path: Path) -> None:
    write_rtl(tmp_path / "a.sv", "module a(input logic clk); endmodule\n")
    write_rtl(tmp_path / "b.sv", "module b(input logic clk); endmodule\n")

    with pytest.raises(IntakeError, match="Ambiguous top module"):
        create_rtl_project(
            rtl_inputs=[str(tmp_path)],
            out_path=tmp_path / "out" / "rtl_project_manifest.json",
            clock="clk",
            cwd=tmp_path,
        )


def test_clock_reset_override_resolves_ambiguous_candidates(tmp_path: Path) -> None:
    rtl = write_rtl(
        tmp_path / "multi_clock.sv",
        """
module multi_clock(
  input logic clk_a,
  input logic clk_b,
  input logic rst_a,
  input logic rst_b,
  output logic done
);
  assign done = rst_b;
endmodule
""",
    )

    outputs = create_rtl_project(
        rtl_inputs=[str(rtl)],
        out_path=tmp_path / "out" / "rtl_project_manifest.json",
        clock="clk_b",
        reset="rst_b",
        reset_polarity="active_high",
        cwd=tmp_path,
    )

    assert outputs.manifest["clock_reset"] == {
        "clock": "clk_b",
        "clock_edge": "posedge",
        "reset": "rst_b",
        "reset_polarity": "active_high",
    }


def test_spec_file_creates_spec_sourced_tasks(tmp_path: Path) -> None:
    rtl = write_rtl(
        tmp_path / "rv.sv",
        """
module rv(
  input logic clk,
  input logic rst,
  input logic out_valid,
  input logic out_ready,
  output logic [7:0] out_data
);
endmodule
""",
    )
    spec = tmp_path / "spec.md"
    spec.write_text("- Output data remains stable while stalled.\n", encoding="utf-8")

    outputs = create_rtl_project(
        rtl_inputs=[str(rtl)],
        out_path=tmp_path / "out" / "rtl_project_manifest.json",
        spec=spec,
        cwd=tmp_path,
    )

    assert outputs.tasks["tasks"][0]["source"] == "spec"
    assert outputs.tasks["tasks"][0]["intent"] == "Output data remains stable while stalled."
