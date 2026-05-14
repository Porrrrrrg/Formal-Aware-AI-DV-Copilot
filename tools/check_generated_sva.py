#!/usr/bin/env python3
"""Run JasperGold syntax/proof/vacuity checks for generated SVA candidates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    from tools.parse_jg_report import parse_report
except ModuleNotFoundError:
    from parse_jg_report import parse_report

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DesignConfig:
    rtl: str
    assumptions: str
    top: str
    clock: str
    reset_cmd: str
    properties_header: str
    harness: str


DESIGNS = {
    "arbiter_rr2": DesignConfig(
        rtl="benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv",
        assumptions="benchmarks/arbiter_rr2/formal/arbiter_rr2_assumptions.sv",
        top="arbiter_rr2_generated_harness",
        clock="clk",
        reset_cmd="reset rst",
        properties_header="""module generated_sva_properties (
  input logic clk,
  input logic rst,
  input logic req0,
  input logic req1,
  input logic gnt0,
  input logic gnt1,
  input logic turn
);""",
        harness="""module arbiter_rr2_generated_harness;
  logic clk;
  logic rst;
  logic req0;
  logic req1;
  logic gnt0;
  logic gnt1;
  logic turn;

  arbiter_rr2 dut (
    .clk(clk),
    .rst(rst),
    .req0(req0),
    .req1(req1),
    .gnt0(gnt0),
    .gnt1(gnt1),
    .turn(turn)
  );

  arbiter_rr2_assumptions assumptions_i (.*);
  generated_sva_properties generated_properties_i (.*);
endmodule
""",
    ),
    "rv_buffer": DesignConfig(
        rtl="benchmarks/rv_buffer/rtl/rv_buffer_correct.sv",
        assumptions="benchmarks/rv_buffer/formal/rv_buffer_assumptions.sv",
        top="rv_buffer_generated_harness",
        clock="clk",
        reset_cmd="reset rst",
        properties_header="""module generated_sva_properties #(
  parameter int WIDTH = 8
) (
  input logic             clk,
  input logic             rst,
  input logic             in_valid,
  input logic             in_ready,
  input logic [WIDTH-1:0] in_data,
  input logic             out_valid,
  input logic             out_ready,
  input logic [WIDTH-1:0] out_data,
  input logic             full
);""",
        harness="""module rv_buffer_generated_harness;
  localparam int WIDTH = 8;

  logic clk;
  logic rst;
  logic in_valid;
  logic in_ready;
  logic [WIDTH-1:0] in_data;
  logic out_valid;
  logic out_ready;
  logic [WIDTH-1:0] out_data;
  logic full;

  rv_buffer #(.WIDTH(WIDTH)) dut (.*);

  rv_buffer_assumptions #(.WIDTH(WIDTH)) assumptions_i (.*);
  generated_sva_properties #(.WIDTH(WIDTH)) generated_properties_i (.*);
endmodule
""",
    ),
    "apb_regblock": DesignConfig(
        rtl="benchmarks/apb_regblock/rtl/apb_regblock_correct.sv",
        assumptions="benchmarks/apb_regblock/formal/apb_regblock_assumptions.sv",
        top="apb_regblock_generated_harness",
        clock="pclk",
        reset_cmd="reset -expression {!presetn}",
        properties_header="""module generated_sva_properties (
  input logic        pclk,
  input logic        presetn,
  input logic        psel,
  input logic        penable,
  input logic        pwrite,
  input logic [7:0]  paddr,
  input logic [31:0] pwdata,
  input logic [31:0] prdata,
  input logic        pready,
  input logic        pslverr,
  input logic [31:0] reg0,
  input logic [31:0] reg1
);""",
        harness="""module apb_regblock_generated_harness;
  logic pclk;
  logic presetn;
  logic psel;
  logic penable;
  logic pwrite;
  logic [7:0] paddr;
  logic [31:0] pwdata;
  logic [31:0] prdata;
  logic pready;
  logic pslverr;
  logic [31:0] reg0;
  logic [31:0] reg1;

  apb_regblock dut (.*);

  apb_regblock_assumptions assumptions_i (.*);
  generated_sva_properties generated_properties_i (.*);
endmodule
""",
    ),
    "fifo_1r1w": DesignConfig(
        rtl="benchmarks/fifo_1r1w/rtl/fifo_1r1w_correct.sv",
        assumptions="benchmarks/fifo_1r1w/formal/fifo_1r1w_assumptions.sv",
        top="fifo_1r1w_generated_harness",
        clock="clk",
        reset_cmd="reset rst",
        properties_header="""module generated_sva_properties #(
  parameter int WIDTH = 8,
  parameter int DEPTH = 4,
  parameter int COUNT_W = $clog2(DEPTH + 1)
) (
  input logic               clk,
  input logic               rst,
  input logic               push_valid,
  input logic               push_ready,
  input logic [WIDTH-1:0]   push_data,
  input logic               pop_valid,
  input logic               pop_ready,
  input logic [WIDTH-1:0]   pop_data,
  input logic               full,
  input logic               empty,
  input logic [COUNT_W-1:0] level,
  input logic               push_fire,
  input logic               pop_fire
);""",
        harness="""module fifo_1r1w_generated_harness;
  localparam int WIDTH = 8;
  localparam int DEPTH = 4;
  localparam int COUNT_W = $clog2(DEPTH + 1);

  logic clk;
  logic rst;
  logic push_valid;
  logic push_ready;
  logic [WIDTH-1:0] push_data;
  logic pop_valid;
  logic pop_ready;
  logic [WIDTH-1:0] pop_data;
  logic full;
  logic empty;
  logic [COUNT_W-1:0] level;
  logic push_fire;
  logic pop_fire;

  fifo_1r1w #(.WIDTH(WIDTH), .DEPTH(DEPTH)) dut (.*);

  fifo_1r1w_assumptions #(.WIDTH(WIDTH), .DEPTH(DEPTH)) assumptions_i (.*);
  generated_sva_properties #(.WIDTH(WIDTH), .DEPTH(DEPTH)) generated_properties_i (.*);
endmodule
""",
    ),
}


def check_generated_sva(
    case: dict[str, object],
    prediction: dict[str, object],
    system: str,
    out_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    design_id = str(case["design_id"])
    if design_id not in DESIGNS:
        raise ValueError(f"Unsupported design for generated SVA check: {design_id}")
    config = DESIGNS[design_id]
    case_id = str(case["case_id"])
    property_id = str(prediction.get("property_id") or case.get("property_id", "generated_property"))
    sva = str(prediction.get("sva", ""))

    out_root = out_root or ROOT / "jasper" / "reports" / "sva_generation"
    report_dir = resolve_repo_path(out_root) / system / case_id
    report_dir.mkdir(parents=True, exist_ok=True)

    generated_properties = report_dir / "generated_properties.sv"
    generated_harness = report_dir / "generated_harness.sv"
    generated_properties.write_text(render_generated_properties(config, sva))
    generated_harness.write_text(config.harness)
    (report_dir / "candidate_sva.json").write_text(json.dumps(prediction, indent=2) + "\n")

    env = os.environ.copy()
    env["JASPERLOOP_ROOT"] = str(ROOT)
    env["JASPERLOOP_RTL"] = str(ROOT / config.rtl)
    env["JASPERLOOP_ASSUMPTIONS"] = str(ROOT / config.assumptions)
    env["JASPERLOOP_GENERATED_PROPERTIES"] = str(generated_properties)
    env["JASPERLOOP_GENERATED_HARNESS"] = str(generated_harness)
    env["JASPERLOOP_TOP"] = config.top
    env["JASPERLOOP_CLOCK"] = config.clock
    env["JASPERLOOP_RESET_CMD"] = config.reset_cmd
    env["JASPERLOOP_REPORT_DIR"] = str(report_dir)

    tcl = ROOT / "jasper" / "common" / "check_generated_sva.tcl"
    jasper_bin = env.get("JASPER_BIN", "jg")
    cmd = [
        jasper_bin,
        "-batch",
        "-allow_unsupported_OS",
        "-proj",
        str(report_dir / "jgproject"),
        "-tcl",
        str(tcl),
    ]
    (report_dir / "run_command.txt").write_text(" ".join(cmd) + "\n")

    if dry_run:
        return summarize_check(
            report_dir,
            property_id,
            syntax_pass=None,
            returncode=None,
            ignore_reports=True,
        )

    if shutil.which(jasper_bin) is None:
        raise RuntimeError(
            f"Cannot find JasperGold executable '{jasper_bin}'. "
            "Set JASPER_BIN or source the Cadence environment."
        )

    with (report_dir / "jg.log").open("w") as log:
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    syntax_pass = completed.returncode == 0 and (report_dir / "properties.rpt").exists()
    return summarize_check(report_dir, property_id, syntax_pass=syntax_pass, returncode=completed.returncode)


def render_generated_properties(config: DesignConfig, sva: str) -> str:
    return config.properties_header + "\n\n  " + sva.strip() + "\n\nendmodule\n"


def summarize_check(
    report_dir: Path,
    property_id: str,
    syntax_pass: bool | None,
    returncode: int | None,
    ignore_reports: bool = False,
) -> dict[str, object]:
    properties = (
        []
        if ignore_reports
        else parse_report(report_dir / "properties.rpt")
        if (report_dir / "properties.rpt").exists()
        else []
    )
    vacuity = (
        []
        if ignore_reports
        else parse_report(report_dir / "vacuity.rpt")
        if (report_dir / "vacuity.rpt").exists()
        else []
    )
    proof_status = find_status(properties, property_id)
    vacuity_status = find_status(vacuity, property_id)
    return {
        "syntax_pass": syntax_pass,
        "jasper_returncode": returncode,
        "proof_status": proof_status,
        "vacuity_status": vacuity_status,
        "feedback": summarize_feedback(report_dir, properties, vacuity, syntax_pass),
        "report_dir": str(report_dir),
        "properties_report": str(report_dir / "properties.rpt"),
        "vacuity_report": str(report_dir / "vacuity.rpt") if (report_dir / "vacuity.rpt").exists() else None,
        "log": str(report_dir / "jg.log"),
    }


def find_status(results: list[dict[str, object]], property_id: str) -> str | None:
    for result in results:
        name = str(result.get("property_id", ""))
        if name == property_id or name.endswith("." + property_id) or property_id in name:
            return str(result.get("status"))
    if len(results) == 1:
        return str(results[0].get("status"))
    return None


def summarize_feedback(
    report_dir: Path,
    properties: list[dict[str, object]],
    vacuity: list[dict[str, object]],
    syntax_pass: bool | None,
) -> str:
    if syntax_pass is False:
        log_path = report_dir / "jg.log"
        if log_path.exists():
            return "\n".join(select_log_lines(log_path.read_text(errors="ignore").splitlines()))
        return "JasperGold failed before producing a property report."
    vacuous = [
        f"{item.get('property_id')}: {item.get('status')}"
        for item in vacuity
        if item.get("property_id") and str(item.get("status", "")).lower() == "vacuous"
    ]
    if vacuous:
        return "Vacuity results: " + "; ".join(vacuous[:8])
    if properties:
        rendered = [
            f"{item.get('property_id')}: {item.get('status')}"
            for item in properties
            if item.get("property_id")
        ]
        if rendered:
            return "Property results: " + "; ".join(rendered[:8])
    if vacuity:
        rendered = [
            f"{item.get('property_id')}: {item.get('status')}"
            for item in vacuity
            if item.get("property_id")
        ]
        if rendered:
            return "Vacuity results: " + "; ".join(rendered[:8])
    return "No JasperGold status lines were parsed."


def select_log_lines(lines: list[str], limit: int = 20) -> list[str]:
    keywords = ["error", "syntax", "unknown", "failed", "can't", "cannot", "not found"]
    selected = [line.strip() for line in lines if any(keyword in line.lower() for keyword in keywords)]
    selected = [line for line in selected if line]
    if not selected:
        selected = [line.strip() for line in lines[-limit:] if line.strip()]
    return selected[-limit:]


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def first_object(data: object, path: Path) -> dict[str, object]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    raise ValueError(f"{path} must contain a JSON object or non-empty object array")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--prediction", required=True, type=Path)
    parser.add_argument("--system", default="manual")
    parser.add_argument("--out-root", type=Path, default=Path("jasper/reports/sva_generation"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    case = first_object(json.loads(args.case.read_text()), args.case)
    prediction = first_object(json.loads(args.prediction.read_text()), args.prediction)
    result = check_generated_sva(
        case=case,
        prediction=prediction,
        system=args.system,
        out_root=args.out_root,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
