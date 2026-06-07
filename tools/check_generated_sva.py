#!/usr/bin/env python3
"""Run JasperGold syntax/proof/vacuity checks for generated SVA candidates."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from tools.parse_jg_report import parse_report
except ModuleNotFoundError:
    from parse_jg_report import parse_report

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copilot.retrieval.rtl_index import build_rtl_index  # noqa: E402


@dataclass(frozen=True)
class DesignConfig:
    rtl: str
    assumptions: str
    top: str
    clock: str
    reset_cmd: str
    properties_header: str
    harness: str
    native_properties: str = ""
    native_harness: str = ""
    native_run_tcl: str = ""
    property_module: str = "generated_sva_properties"
    property_instance: str = "generated_properties_i"
    rtl_files: tuple[str, ...] = ()
    assumption_files: tuple[str, ...] = ()
    design_top: str = ""
    harness_strategy: str = "reuse_existing"
    dynamic_manifest: str = ""
    include_dirs: tuple[str, ...] = ()
    defines: tuple[str, ...] = ()

    @classmethod
    def from_manifest(
        cls,
        manifest: dict[str, object],
        root: Path | None = None,
        manifest_path: Path | None = None,
    ) -> "DesignConfig":
        root = root or ROOT
        top_module = str(manifest["top_module"])
        design_id = str(manifest.get("design_id") or top_module)
        rtl_files = tuple(
            str(resolve_manifest_path(str(path), root=root))
            for path in list_value(manifest.get("rtl_files"))
        )
        assumption_files = tuple(
            str(resolve_manifest_path(str(path), root=root))
            for path in list_value(manifest.get("assumption_files"))
        )
        include_dirs = tuple(
            str(resolve_manifest_path(str(path), root=root))
            for path in list_value(manifest.get("include_dirs"))
        )
        raw_defines = manifest.get("defines") if isinstance(manifest.get("defines"), dict) else {}
        defines = tuple(f"{key}={value}" for key, value in sorted(raw_defines.items()))
        if not rtl_files:
            raise ValueError("RTL project manifest must include at least one rtl_files entry.")

        clock_reset = manifest.get("clock_reset") if isinstance(manifest.get("clock_reset"), dict) else {}
        property_module = str(manifest.get("property_module") or "generated_sva_properties")
        property_instance = str(manifest.get("property_instance") or "generated_properties_i")
        visible_signals = [str(signal) for signal in list_value(manifest.get("visible_signals"))]
        index = build_rtl_index([Path(path) for path in rtl_files])
        properties_header = render_dynamic_properties_header(
            index=index,
            top_module=top_module,
            property_module=property_module,
            visible_signals=visible_signals,
        )

        harness = manifest.get("harness") if isinstance(manifest.get("harness"), dict) else {}
        harness_path = harness.get("harness_path")
        harness_strategy = str(harness.get("strategy") or "render_generic")
        if harness_path:
            resolved_harness = resolve_manifest_path(str(harness_path), root=root)
            harness_text = resolved_harness.read_text(encoding="utf-8")
            harness_modules = extract_module_names(harness_text)
            jasper_top = harness_modules[0] if harness_modules else top_module
            harness_strategy = "reuse_existing"
        else:
            jasper_top = sanitize_sv_identifier(f"{design_id}_generated_harness")
            harness_text = render_generic_harness(
                index=index,
                dut_module=top_module,
                harness_module=jasper_top,
                property_module=property_module,
                property_instance=property_instance,
                visible_signals=visible_signals,
            )
            harness_strategy = "render_generic"

        return cls(
            rtl=rtl_files[0],
            assumptions=assumption_files[0] if assumption_files else "",
            top=jasper_top,
            clock=str(clock_reset.get("clock") or ""),
            reset_cmd=reset_command_from_clock_reset(clock_reset),
            properties_header=properties_header,
            harness=harness_text,
            property_module=property_module,
            property_instance=property_instance,
            rtl_files=rtl_files,
            assumption_files=assumption_files,
            design_top=top_module,
            harness_strategy=harness_strategy,
            dynamic_manifest=str(manifest_path) if manifest_path else "",
            include_dirs=include_dirs,
            defines=defines,
        )


DESIGNS = {
    "arbiter_rr2": DesignConfig(
        rtl="benchmarks/arbiter_rr2/rtl/arbiter_rr2_correct.sv",
        assumptions="benchmarks/arbiter_rr2/formal/arbiter_rr2_assumptions.sv",
        top="arbiter_rr2_harness",
        clock="clk",
        reset_cmd="reset rst",
        properties_header="""module arbiter_rr2_properties (
  input logic clk,
  input logic rst,
  input logic req0,
  input logic req1,
  input logic gnt0,
  input logic gnt1,
  input logic turn
);""",
        harness="""module arbiter_rr2_harness;
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
  arbiter_rr2_properties properties_i (.*);
endmodule
""",
        native_properties="benchmarks/arbiter_rr2/formal/arbiter_rr2_properties.sv",
        native_harness="benchmarks/arbiter_rr2/formal/arbiter_rr2_harness.sv",
        native_run_tcl="benchmarks/arbiter_rr2/formal/run_jg.tcl",
        property_module="arbiter_rr2_properties",
        property_instance="properties_i",
    ),
    "rv_buffer": DesignConfig(
        rtl="benchmarks/rv_buffer/rtl/rv_buffer_correct.sv",
        assumptions="benchmarks/rv_buffer/formal/rv_buffer_assumptions.sv",
        top="rv_buffer_harness",
        clock="clk",
        reset_cmd="reset rst",
        properties_header="""module rv_buffer_properties #(
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
        harness="""module rv_buffer_harness;
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
  rv_buffer_properties #(.WIDTH(WIDTH)) properties_i (.*);
endmodule
""",
        native_properties="benchmarks/rv_buffer/formal/rv_buffer_properties.sv",
        native_harness="benchmarks/rv_buffer/formal/rv_buffer_harness.sv",
        native_run_tcl="benchmarks/rv_buffer/formal/run_jg.tcl",
        property_module="rv_buffer_properties",
        property_instance="properties_i",
    ),
    "apb_regblock": DesignConfig(
        rtl="benchmarks/apb_regblock/rtl/apb_regblock_correct.sv",
        assumptions="benchmarks/apb_regblock/formal/apb_regblock_assumptions.sv",
        top="apb_regblock_harness",
        clock="pclk",
        reset_cmd="reset -expression {!presetn}",
        properties_header="""module apb_regblock_properties (
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
        harness="""module apb_regblock_harness;
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
  apb_regblock_properties properties_i (.*);
endmodule
""",
        native_properties="benchmarks/apb_regblock/formal/apb_regblock_properties.sv",
        native_harness="benchmarks/apb_regblock/formal/apb_regblock_harness.sv",
        native_run_tcl="benchmarks/apb_regblock/formal/run_jg.tcl",
        property_module="apb_regblock_properties",
        property_instance="properties_i",
    ),
    "fifo_1r1w": DesignConfig(
        rtl="benchmarks/fifo_1r1w/rtl/fifo_1r1w_correct.sv",
        assumptions="benchmarks/fifo_1r1w/formal/fifo_1r1w_assumptions.sv",
        top="fifo_1r1w_harness",
        clock="clk",
        reset_cmd="reset rst",
        properties_header="""module fifo_1r1w_properties #(
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
        harness="""module fifo_1r1w_harness;
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
  fifo_1r1w_properties #(.WIDTH(WIDTH), .DEPTH(DEPTH)) properties_i (.*);
endmodule
""",
        native_properties="benchmarks/fifo_1r1w/formal/fifo_1r1w_properties.sv",
        native_harness="benchmarks/fifo_1r1w/formal/fifo_1r1w_harness.sv",
        native_run_tcl="benchmarks/fifo_1r1w/formal/run_jg.tcl",
        property_module="fifo_1r1w_properties",
        property_instance="properties_i",
    ),
}


def check_generated_sva(
    case: dict[str, object],
    prediction: dict[str, object],
    system: str,
    out_root: Path | None = None,
    dry_run: bool = False,
    design_manifest: Path | dict[str, object] | None = None,
) -> dict[str, object]:
    design_id = str(case["design_id"])
    config: DesignConfig
    manifest_path: Path | None = None
    if design_manifest is not None:
        manifest_data, manifest_path = load_manifest_input(design_manifest)
        config = DesignConfig.from_manifest(
            manifest_data,
            root=manifest_path.parent if manifest_path else ROOT,
            manifest_path=manifest_path,
        )
    elif design_id not in DESIGNS:
        raise ValueError(f"Unsupported design for generated SVA check: {design_id}")
    else:
        config = DESIGNS[design_id]
    case_id = str(case["case_id"])
    property_id = str(
        prediction.get("property_id") or case.get("property_id", "generated_property")
    )
    sva = str(prediction.get("sva", ""))

    out_root = out_root or ROOT / "jasper" / "reports" / "sva_generation"
    report_dir = resolve_repo_path(out_root) / system / case_id
    report_dir.mkdir(parents=True, exist_ok=True)

    generated_properties = report_dir / "generated_properties.sv"
    generated_harness = report_dir / "generated_harness.sv"
    candidate_json = report_dir / "candidate_sva.json"
    generated_properties.write_text(
        render_generated_properties(config, sva, property_id, case, prediction),
        encoding="utf-8",
    )
    generated_harness.write_text(render_generated_harness(config), encoding="utf-8")
    candidate_json.write_text(json.dumps(prediction, indent=2) + "\n", encoding="utf-8")
    formal_mode = infer_formal_mode(prediction)

    env = os.environ.copy()
    env["JASPERLOOP_ROOT"] = str(ROOT)
    rtl_files = resolved_config_files(config.rtl_files or (config.rtl,))
    assumption_files = resolved_config_files(config.assumption_files or ((config.assumptions,) if config.assumptions else ()))
    env["JASPERLOOP_RTL"] = rtl_files[0] if rtl_files else ""
    env["JASPERLOOP_RTL_FILES"] = "\n".join(rtl_files)
    env["JASPERLOOP_ASSUMPTIONS"] = assumption_files[0] if assumption_files else ""
    env["JASPERLOOP_ASSUMPTION_FILES"] = "\n".join(assumption_files)
    env["JASPERLOOP_INCLUDE_DIRS"] = "\n".join(config.include_dirs)
    env["JASPERLOOP_DEFINES"] = "\n".join(config.defines)
    env["JASPERLOOP_GENERATED_PROPERTIES"] = str(generated_properties)
    env["JASPERLOOP_GENERATED_HARNESS"] = str(generated_harness)
    env["JASPERLOOP_TOP"] = config.top
    env["JASPERLOOP_CLOCK"] = config.clock
    env["JASPERLOOP_RESET_CMD"] = config.reset_cmd
    env["JASPERLOOP_FORMAL_MODE"] = formal_mode
    env["JASPERLOOP_NATIVE_PROPERTIES"] = resolved_config_file(config.native_properties)
    env["JASPERLOOP_NATIVE_HARNESS"] = resolved_config_file(config.native_harness)
    env["JASPERLOOP_NATIVE_RUN_TCL"] = resolved_config_file(config.native_run_tcl)
    env["JASPERLOOP_PROPERTY_MODULE"] = config.property_module
    env["JASPERLOOP_PROPERTY_INSTANCE"] = config.property_instance
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
    run_command = report_dir / "run_command.txt"
    run_command.write_text(" ".join(cmd) + "\n", encoding="utf-8")

    artifact_paths = build_artifact_paths(
        report_dir=report_dir,
        generated_properties=generated_properties,
        generated_harness=generated_harness,
        candidate_json=candidate_json,
        run_command=run_command,
        tcl=tcl,
        rtl_project_manifest=manifest_path,
        dynamic_harness_strategy=config.harness_strategy if config.dynamic_manifest else None,
    )
    embedding_audit = build_embedding_audit(
        case=case,
        prediction=prediction,
        config=config,
        report_dir=report_dir,
        generated_properties=generated_properties,
        generated_harness=generated_harness,
        run_command=run_command,
        tcl=tcl,
        cmd=cmd,
        env=env,
        artifact_paths=artifact_paths,
    )
    write_debug_artifacts(
        artifact_paths=artifact_paths,
        generated_properties=generated_properties,
        generated_harness=generated_harness,
        candidate_json=candidate_json,
        run_command=run_command,
        tcl=tcl,
        cmd=cmd,
        env=env,
        audit=embedding_audit,
    )

    if dry_run:
        result = summarize_check(
            report_dir,
            property_id,
            syntax_pass=None,
            returncode=None,
            ignore_reports=True,
        )
        return attach_artifacts(result, artifact_paths, embedding_audit)

    clear_stale_reports(report_dir)

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
    expected_report = {
        "cover": report_dir / "cover.rpt",
        "vacuity": report_dir / "vacuity.rpt",
    }.get(formal_mode, report_dir / "properties.rpt")
    syntax_pass = completed.returncode == 0 and expected_report.exists()
    result = summarize_check(
        report_dir,
        property_id,
        syntax_pass=syntax_pass,
        returncode=completed.returncode,
    )
    return attach_artifacts(result, artifact_paths, embedding_audit)


def render_generated_properties(
    config: DesignConfig,
    sva: str,
    property_id: str,
    case: dict[str, object],
    prediction: dict[str, object],
) -> str:
    helper_code = str(prediction.get("helper_code") or "")
    helper_policy = case.get("helper_code_policy") if isinstance(case.get("helper_code_policy"), dict) else {}
    helper_allowed = bool(helper_policy.get("allowed")) if isinstance(helper_policy, dict) else False
    helper_block = f"\n\n  {helper_code.strip()}\n" if helper_allowed and helper_code.strip() else ""
    return (
        config.properties_header
        + helper_block
        + "\n\n  "
        + ensure_labeled_property(sva, property_id)
        + "\n\nendmodule\n"
    )


def ensure_labeled_property(sva: str, property_id: str) -> str:
    stripped = sva.strip()
    if re.match(
        r"^[A-Za-z_][A-Za-z0-9_$]*\s*:\s*(?:assert|cover)\s+property\b",
        stripped,
        flags=re.IGNORECASE,
    ):
        return stripped
    if re.match(r"^(?:assert|cover)\s+property\b", stripped, flags=re.IGNORECASE):
        label = sanitize_property_label(property_id)
        return f"{label}: {stripped}"
    return stripped


def sanitize_property_label(property_id: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_$]", "_", property_id.strip())
    if not label or not re.match(r"^[A-Za-z_]", label):
        label = f"p_{label or 'generated_property'}"
    return label


def render_generated_harness(config: DesignConfig) -> str:
    if config.native_harness:
        return (ROOT / config.native_harness).read_text(encoding="utf-8")
    return config.harness


def render_dynamic_properties_header(
    *,
    index: dict[str, Any],
    top_module: str,
    property_module: str,
    visible_signals: list[str],
) -> str:
    declarations = signal_declarations(index, top_module)
    ports = [
        f"  input {declarations.get(signal, 'logic')} {signal}"
        for signal in visible_signals
    ]
    return "module " + property_module + " (\n" + ",\n".join(ports) + "\n);"


def render_generic_harness(
    *,
    index: dict[str, Any],
    dut_module: str,
    harness_module: str,
    property_module: str,
    property_instance: str,
    visible_signals: list[str],
) -> str:
    module = index.get("modules", {}).get(dut_module, {})
    ports = [port for port in module.get("ports", []) if isinstance(port, dict)]
    declarations = signal_declarations(index, dut_module)
    lines = [f"module {harness_module};"]
    for port in ports:
        name = str(port.get("name") or "")
        if name:
            lines.append(f"  {declarations.get(name, 'logic')} {name};")
    lines.extend(["", f"  {dut_module} dut ("])
    dut_connections = [f"    .{port['name']}({port['name']})" for port in ports if port.get("name")]
    lines.append(",\n".join(dut_connections))
    lines.extend(["  );", "", f"  {property_module} {property_instance} ("])
    top_port_names = {str(port.get("name")) for port in ports if port.get("name")}
    property_connections = []
    for signal in visible_signals:
        expression = signal if signal in top_port_names else f"dut.{signal}"
        property_connections.append(f"    .{signal}({expression})")
    lines.append(",\n".join(property_connections))
    lines.extend(["  );", "endmodule", ""])
    return "\n".join(lines)


def signal_declarations(index: dict[str, Any], top_module: str) -> dict[str, str]:
    module = index.get("modules", {}).get(top_module, {})
    declarations: dict[str, str] = {}
    for port in module.get("ports", []):
        if isinstance(port, dict) and port.get("name"):
            declarations[str(port["name"])] = normalize_sv_type(str(port.get("type") or "logic"))
    for signal in module.get("signals", []):
        if isinstance(signal, dict) and signal.get("name"):
            kind = str(signal.get("kind") or "logic")
            width = str(signal.get("type") or "").strip()
            declarations[str(signal["name"])] = normalize_sv_type(f"{kind} {width}".strip())
    return declarations


def normalize_sv_type(value: str) -> str:
    text = " ".join(value.split())
    if not text:
        return "logic"
    if text.startswith("["):
        return f"logic {text}"
    if not re.search(r"\b(?:logic|wire|reg)\b", text):
        return f"logic {text}".strip()
    return text


def load_manifest_input(
    design_manifest: Path | dict[str, object],
) -> tuple[dict[str, object], Path | None]:
    if isinstance(design_manifest, dict):
        return design_manifest, None
    path = design_manifest.resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data, path


def list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def resolve_manifest_path(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    candidates = [ROOT / path, root / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (root / path).resolve()


def resolved_config_file(path_text: str) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    return str(path if path.is_absolute() else ROOT / path)


def resolved_config_files(paths: tuple[str, ...]) -> list[str]:
    return [resolved_config_file(path) for path in paths if path]


def reset_command_from_clock_reset(clock_reset: dict[str, object]) -> str:
    reset = str(clock_reset.get("reset") or "")
    if not reset:
        return ""
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    if polarity == "active_low":
        return f"reset -expression {{!{reset}}}"
    return f"reset {reset}"


def sanitize_sv_identifier(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_$]", "_", value.strip())
    if not sanitized or not re.match(r"^[A-Za-z_]", sanitized):
        sanitized = f"m_{sanitized or 'generated'}"
    return sanitized


def infer_formal_mode(prediction: dict[str, object]) -> str:
    explicit = str(
        prediction.get("formal_mode") or prediction.get("check_kind") or ""
    ).strip().lower()
    if explicit in {"cover", "vacuity", "prove"}:
        return explicit
    sva = str(prediction.get("sva") or "")
    if re.search(r"\bcover\s+property\b", sva, flags=re.IGNORECASE) and not re.search(
        r"\bassert\s+property\b",
        sva,
        flags=re.IGNORECASE,
    ):
        return "cover"
    return "prove"


def clear_stale_reports(report_dir: Path) -> None:
    for name in (
        "properties.rpt",
        "cover.rpt",
        "vacuity.rpt",
        "vacuity_error.txt",
        "jg.log",
    ):
        path = report_dir / name
        if path.exists():
            path.unlink()


def summarize_check(
    report_dir: Path,
    property_id: str,
    syntax_pass: bool | None,
    returncode: int | None,
    ignore_reports: bool = False,
) -> dict[str, object]:
    properties_path = report_dir / "properties.rpt"
    cover_path = report_dir / "cover.rpt"
    proof_path = properties_path if properties_path.exists() else cover_path
    properties = (
        []
        if ignore_reports
        else parse_report(proof_path)
        if proof_path.exists()
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
        "properties_report": str(properties_path) if properties_path.exists() else None,
        "cover_report": str(cover_path) if cover_path.exists() else None,
        "vacuity_report": str(report_dir / "vacuity.rpt")
        if (report_dir / "vacuity.rpt").exists()
        else None,
        "log": str(report_dir / "jg.log"),
    }


def attach_artifacts(
    result: dict[str, object],
    artifact_paths: dict[str, object],
    embedding_audit: dict[str, object],
) -> dict[str, object]:
    updated = dict(result)
    updated["artifact_paths"] = artifact_paths
    updated["embedding_audit"] = embedding_audit
    return updated


def build_artifact_paths(
    report_dir: Path,
    generated_properties: Path,
    generated_harness: Path,
    candidate_json: Path,
    run_command: Path,
    tcl: Path,
    rtl_project_manifest: Path | None = None,
    dynamic_harness_strategy: str | None = None,
) -> dict[str, object]:
    debug_dir = report_dir / "embedding_audit"
    debug_artifacts = {
        "generated_properties": str(debug_dir / generated_properties.name),
        "generated_harness": str(debug_dir / generated_harness.name),
        "candidate_json": str(debug_dir / candidate_json.name),
        "run_command": str(debug_dir / run_command.name),
        "run_metadata": str(debug_dir / "run_metadata.json"),
        "tcl_snapshot": str(debug_dir / tcl.name),
        "audit_json": str(debug_dir / "embedding_audit.json"),
        "audit_markdown": str(debug_dir / "embedding_audit.md"),
    }
    if rtl_project_manifest:
        debug_artifacts["rtl_project_manifest"] = str(debug_dir / rtl_project_manifest.name)
    artifact_paths: dict[str, object] = {
        "report_dir": str(report_dir),
        "generated_properties": str(generated_properties),
        "generated_harness": str(generated_harness),
        "candidate_json": str(candidate_json),
        "run_command": str(run_command),
        "tcl_path": str(tcl),
        "properties_report": str(report_dir / "properties.rpt"),
        "cover_report": str(report_dir / "cover.rpt"),
        "vacuity_report": str(report_dir / "vacuity.rpt"),
        "log": str(report_dir / "jg.log"),
        "debug_artifact_dir": str(debug_dir),
        "debug_generated_properties": debug_artifacts["generated_properties"],
        "debug_generated_harness": debug_artifacts["generated_harness"],
        "debug_candidate_json": debug_artifacts["candidate_json"],
        "debug_run_command": debug_artifacts["run_command"],
        "run_metadata_json": debug_artifacts["run_metadata"],
        "tcl_snapshot": debug_artifacts["tcl_snapshot"],
        "embedding_audit_json": debug_artifacts["audit_json"],
        "embedding_audit_markdown": debug_artifacts["audit_markdown"],
        "debug_artifacts": debug_artifacts,
    }
    if rtl_project_manifest:
        artifact_paths["rtl_project_manifest"] = str(rtl_project_manifest)
        artifact_paths["debug_rtl_project_manifest"] = debug_artifacts["rtl_project_manifest"]
    if dynamic_harness_strategy:
        artifact_paths["dynamic_harness_strategy"] = dynamic_harness_strategy
    return artifact_paths


def write_debug_artifacts(
    artifact_paths: dict[str, object],
    generated_properties: Path,
    generated_harness: Path,
    candidate_json: Path,
    run_command: Path,
    tcl: Path,
    cmd: list[str],
    env: dict[str, str],
    audit: dict[str, object],
) -> None:
    debug_dir = Path(str(artifact_paths["debug_artifact_dir"]))
    debug_dir.mkdir(parents=True, exist_ok=True)

    copies = {
        generated_properties: Path(str(artifact_paths["debug_generated_properties"])),
        generated_harness: Path(str(artifact_paths["debug_generated_harness"])),
        candidate_json: Path(str(artifact_paths["debug_candidate_json"])),
        run_command: Path(str(artifact_paths["debug_run_command"])),
    }
    if artifact_paths.get("rtl_project_manifest") and artifact_paths.get("debug_rtl_project_manifest"):
        copies[Path(str(artifact_paths["rtl_project_manifest"]))] = Path(
            str(artifact_paths["debug_rtl_project_manifest"])
        )
    for source, target in copies.items():
        if source.exists():
            shutil.copy2(source, target)
    if tcl.exists():
        shutil.copy2(tcl, Path(str(artifact_paths["tcl_snapshot"])))

    run_metadata = {
        "command": cmd,
        "command_text": " ".join(cmd),
        "tcl_path": str(tcl),
        "tcl_snapshot": artifact_paths["tcl_snapshot"],
        "report_dir": artifact_paths["report_dir"],
        "jasperloop_env": {
            key: env[key]
            for key in sorted(env)
            if key.startswith("JASPERLOOP_")
        },
    }
    Path(str(artifact_paths["run_metadata_json"])).write_text(
        json.dumps(run_metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(str(artifact_paths["embedding_audit_json"])).write_text(
        json.dumps(audit, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(str(artifact_paths["embedding_audit_markdown"])).write_text(
        render_embedding_audit_markdown(audit),
        encoding="utf-8",
    )


def build_embedding_audit(
    case: dict[str, object],
    prediction: dict[str, object],
    config: DesignConfig,
    report_dir: Path,
    generated_properties: Path,
    generated_harness: Path,
    run_command: Path,
    tcl: Path,
    cmd: list[str],
    env: dict[str, str],
    artifact_paths: dict[str, object],
) -> dict[str, object]:
    generated_properties_text = generated_properties.read_text(encoding="utf-8")
    generated_harness_text = generated_harness.read_text(encoding="utf-8")
    run_command_text = run_command.read_text(encoding="utf-8")
    tcl_text = tcl.read_text(encoding="utf-8") if tcl.exists() else ""

    candidate_sva = str(prediction.get("sva", ""))
    property_id = str(prediction.get("property_id") or case.get("property_id") or "")
    reference_sva = first_text_value(case, ("reference_sva",))
    native_expression = first_text_value(
        case,
        (
            "original_native_property_expression",
            "native_property_expression",
            "native_assertion",
            "native_property",
            "source_property_expression",
            "original_property_expression",
        ),
    )
    cover_sva = first_text_value(
        prediction,
        (
            "cover_before_assert_sva",
            "cover_before_assert_property",
            "antecedent_cover_sva",
            "cover_sva",
        ),
    )

    expected_clock_reset = expected_clock_reset_metadata(case, config)
    checks = {
        "label_collisions": audit_label_collisions(
            property_id=property_id,
            candidate_sva=candidate_sva,
            reference_sva=reference_sva,
            native_expression=native_expression,
            cover_sva=cover_sva,
        ),
        "wrong_top_module": audit_wrong_top_module(
            prediction=prediction,
            config=config,
            generated_harness_text=generated_harness_text,
            env=env,
        ),
        "missing_bind_or_instantiation": audit_missing_bind_or_instantiation(
            design_id=str(case.get("design_id") or ""),
            property_module=config.property_module,
            generated_harness_text=generated_harness_text,
        ),
        "wrong_include_or_path_metadata": audit_path_metadata(
            case=case,
            prediction=prediction,
            generated_properties=generated_properties,
            generated_harness=generated_harness,
            run_command=run_command,
            tcl=tcl,
            run_command_text=run_command_text,
            tcl_text=tcl_text,
            report_dir=report_dir,
        ),
        "clock_reset_mismatch": audit_clock_reset_mismatch(
            candidate_sva=candidate_sva,
            reference_sva=reference_sva,
            native_expression=native_expression,
            cover_sva=cover_sva,
            expected=expected_clock_reset,
        ),
        "disable_iff_mismatch": audit_disable_iff_mismatch(
            candidate_sva=candidate_sva,
            reference_sva=reference_sva,
            native_expression=native_expression,
            cover_sva=cover_sva,
            expected=expected_clock_reset,
        ),
        "helper_code_placement": audit_helper_code_placement(
            case=case,
            prediction=prediction,
            generated_properties_text=generated_properties_text,
        ),
    }
    issue_flags = {
        name: bool(check.get("has_issue"))
        for name, check in checks.items()
        if isinstance(check, dict)
    }
    native_flow = native_flow_metadata(config)
    wrapper_flow = wrapper_flow_metadata(
        config=config,
        generated_properties=generated_properties,
        generated_harness=generated_harness,
        tcl=tcl,
        env=env,
    )
    parity = wrapper_parity_checks(
        native_flow=native_flow,
        wrapper_flow=wrapper_flow,
        generated_properties_text=generated_properties_text,
        generated_harness_text=generated_harness_text,
    )
    return {
        "schema_version": "stage12_wrapper_parity_audit_v1",
        "case_id": str(case.get("case_id") or ""),
        "design_id": str(case.get("design_id") or ""),
        "property_id": property_id,
        "report_dir": str(report_dir),
        "comparison": {
            "original_native_property_expression": native_expression,
            "reference_sva": reference_sva,
            "embedded_candidate_sva": candidate_sva,
            "generated_cover_before_assert_sva": cover_sva,
            "candidate_matches_reference_text": normalized_sva(candidate_sva)
            == normalized_sva(reference_sva)
            if reference_sva
            else None,
            "candidate_matches_native_text": normalized_sva(candidate_sva)
            == normalized_sva(native_expression)
            if native_expression
            else None,
        },
        "embedding": {
            "generated_properties_contains_candidate_sva": candidate_sva.strip()
            in generated_properties_text,
            "generated_properties_module": extract_module_names(generated_properties_text),
            "generated_harness_modules": extract_module_names(generated_harness_text),
            "command": cmd,
            "command_text": " ".join(cmd),
            "tcl_path": str(tcl),
        },
        "native_flow": native_flow,
        "wrapper_flow": wrapper_flow,
        "wrapper_parity": parity,
        "expected_clock_reset": expected_clock_reset,
        "checks": checks,
        "issue_flags": issue_flags,
        "issues": [name for name, flagged in issue_flags.items() if flagged],
        "root_cause_candidate": "unknown" if parity["parity_pass"] else "design2sva_embedding_bug",
        "root_cause_detail": embedding_root_cause_detail(checks, parity),
        "artifact_paths": artifact_paths,
    }


def render_embedding_audit_markdown(audit: dict[str, object]) -> str:
    comparison = audit.get("comparison") if isinstance(audit.get("comparison"), dict) else {}
    issue_flags = audit.get("issue_flags") if isinstance(audit.get("issue_flags"), dict) else {}
    artifact_paths = (
        audit.get("artifact_paths") if isinstance(audit.get("artifact_paths"), dict) else {}
    )
    lines = [
        "# Candidate Embedding Audit",
        "",
        f"- Case: `{audit.get('case_id')}`",
        f"- Design: `{audit.get('design_id')}`",
        f"- Property: `{audit.get('property_id')}`",
        f"- Report directory: `{audit.get('report_dir')}`",
        "",
        "## Issue Flags",
        "",
    ]
    if issue_flags:
        for name, flagged in issue_flags.items():
            lines.append(f"- `{name}`: {'issue' if flagged else 'ok'}")
    else:
        lines.append("- No audit flags were produced.")
    lines.extend(
        [
            "",
            "## Wrapper Parity",
            "",
            f"- Parity pass: `{wrapper_parity_value(audit, 'parity_pass')}`",
            f"- Root-cause candidate: `{audit.get('root_cause_candidate')}`",
            f"- Root-cause detail: `{audit.get('root_cause_detail')}`",
            "",
        ]
    )
    for section in ("native_flow", "wrapper_flow"):
        value = audit.get(section)
        lines.extend([f"### {section}", ""])
        if isinstance(value, dict):
            lines.extend(["```json", json.dumps(value, indent=2), "```", ""])
        else:
            lines.extend(["not available", ""])
    lines.extend(["", "## Compared SVA", ""])
    for key in (
        "original_native_property_expression",
        "reference_sva",
        "embedded_candidate_sva",
        "generated_cover_before_assert_sva",
    ):
        value = comparison.get(key)
        lines.extend([f"### {key}", ""])
        if value:
            lines.extend(["```systemverilog", str(value).strip(), "```", ""])
        else:
            lines.extend(["not available", ""])
    lines.extend(["## Artifact Paths", ""])
    for key in (
        "generated_properties",
        "generated_harness",
        "candidate_json",
        "run_command",
        "tcl_path",
        "debug_artifact_dir",
        "embedding_audit_json",
        "embedding_audit_markdown",
    ):
        if key in artifact_paths:
            lines.append(f"- `{key}`: `{artifact_paths[key]}`")
    return "\n".join(lines) + "\n"


def wrapper_parity_value(audit: dict[str, object], key: str) -> object:
    parity = audit.get("wrapper_parity")
    if isinstance(parity, dict):
        return parity.get(key)
    return None


def native_flow_metadata(config: DesignConfig) -> dict[str, object]:
    rtl_files = list(config.rtl_files or (config.rtl,))
    assumption_files = list(config.assumption_files or ((config.assumptions,) if config.assumptions else ()))
    file_order = [
        *rtl_files,
        *assumption_files,
        *([config.native_properties] if config.native_properties else []),
        *([config.native_harness] if config.native_harness else []),
    ]
    return {
        "rtl": config.rtl,
        "rtl_files": rtl_files,
        "assumptions": config.assumptions,
        "assumption_files": assumption_files,
        "properties": config.native_properties,
        "harness": config.native_harness,
        "run_tcl": config.native_run_tcl,
        "file_order": file_order,
        "top_module": config.top,
        "design_top": config.design_top,
        "property_module": config.property_module,
        "property_instance": config.property_instance,
        "clock": config.clock,
        "reset_cmd": config.reset_cmd,
        "formal_modes": ["prove", "cover", "vacuity"],
        "include_paths": list(config.include_dirs),
        "defines": list(config.defines),
        "dynamic_manifest": config.dynamic_manifest,
        "harness_strategy": config.harness_strategy,
    }


def wrapper_flow_metadata(
    config: DesignConfig,
    generated_properties: Path,
    generated_harness: Path,
    tcl: Path,
    env: dict[str, str],
) -> dict[str, object]:
    formal_mode = env.get("JASPERLOOP_FORMAL_MODE", "prove")
    rtl_files = list(config.rtl_files or (config.rtl,))
    assumption_files = list(config.assumption_files or ((config.assumptions,) if config.assumptions else ()))
    return {
        "rtl": config.rtl,
        "rtl_files": rtl_files,
        "assumptions": config.assumptions,
        "assumption_files": assumption_files,
        "generated_properties": str(generated_properties),
        "generated_harness": str(generated_harness),
        "generated_harness_source": config.native_harness or config.harness_strategy,
        "tcl": str(tcl),
        "file_order": [
            *rtl_files,
            *assumption_files,
            str(generated_properties),
            str(generated_harness),
        ],
        "top_module": env.get("JASPERLOOP_TOP", ""),
        "design_top": config.design_top,
        "property_module": config.property_module,
        "property_instance": config.property_instance,
        "clock": env.get("JASPERLOOP_CLOCK", ""),
        "reset_cmd": env.get("JASPERLOOP_RESET_CMD", ""),
        "formal_mode": formal_mode,
        "include_paths": list(config.include_dirs),
        "defines": list(config.defines),
        "binding_style": "native_harness_instantiation",
        "dynamic_manifest": config.dynamic_manifest,
        "harness_strategy": config.harness_strategy,
    }


def wrapper_parity_checks(
    native_flow: dict[str, object],
    wrapper_flow: dict[str, object],
    generated_properties_text: str,
    generated_harness_text: str,
) -> dict[str, object]:
    property_module = str(native_flow.get("property_module") or "")
    top_module = str(native_flow.get("top_module") or "")
    assumption_path_match = native_flow.get("assumptions") == wrapper_flow.get("assumptions")
    rtl_path_match = native_flow.get("rtl") == wrapper_flow.get("rtl")
    top_match = native_flow.get("top_module") == wrapper_flow.get("top_module")
    clock_match = native_flow.get("clock") == wrapper_flow.get("clock")
    reset_match = native_flow.get("reset_cmd") == wrapper_flow.get("reset_cmd")
    property_module_match = property_module in extract_module_names(generated_properties_text)
    harness_reused = wrapper_flow.get("generated_harness_source") == native_flow.get("harness")
    dynamic_harness = not native_flow.get("harness")
    harness_relation_ok = (
        wrapper_flow.get("generated_harness_source") in {"render_generic", "reuse_existing"}
        if dynamic_harness
        else harness_reused
    )
    property_instance_connected = bool(
        property_module
        and re.search(
            rf"\b{re.escape(property_module)}\b(?:\s*#\s*\([^;]*?\))?\s+"
            rf"{re.escape(str(native_flow.get('property_instance') or ''))}\s*\(",
            generated_harness_text,
            flags=re.DOTALL,
        )
    )
    top_declared = top_module in extract_module_names(generated_harness_text)
    critical = {
        "rtl_path_match": rtl_path_match,
        "assumptions_path_match": assumption_path_match,
        "top_module_match": top_match,
        "top_declared_in_harness": top_declared,
        "property_module_replaces_native": property_module_match,
        "property_instance_connected": property_instance_connected,
        "native_harness_reused": harness_relation_ok,
        "clock_match": clock_match,
        "reset_command_match": reset_match,
    }
    return {
        "parity_pass": all(critical.values()),
        "critical_checks": critical,
        "file_order_relation": "dynamic_generated_harness_order"
        if dynamic_harness
        else "native_property_module_replaced_in_native_harness_order",
        "assumptions_applied": assumption_path_match
        and (not native_flow.get("assumptions") or "assumptions_i" in generated_harness_text),
        "reset_polarity_source": "native_reset_command",
        "formal_mode": wrapper_flow.get("formal_mode"),
    }


def embedding_root_cause_detail(
    checks: dict[str, object],
    parity: dict[str, object],
) -> str:
    if parity.get("parity_pass"):
        mode = str(parity.get("formal_mode") or "prove")
        return f"wrapper_reuses_native_harness_with_{mode}_mode"
    critical = parity.get("critical_checks")
    if isinstance(critical, dict):
        missing = [name for name, ok in critical.items() if not ok]
        if missing:
            return "wrapper_parity_mismatch:" + ",".join(sorted(missing))
    issue_names = [
        name
        for name, check in checks.items()
        if isinstance(check, dict) and bool(check.get("has_issue"))
    ]
    if issue_names:
        return "embedding_audit_issue:" + ",".join(sorted(issue_names))
    return "wrapper_parity_unknown"


def audit_label_collisions(
    property_id: str,
    candidate_sva: str,
    reference_sva: str | None,
    native_expression: str | None,
    cover_sva: str | None,
) -> dict[str, object]:
    candidate_labels = extract_property_labels(candidate_sva)
    cover_labels = extract_property_labels(cover_sva or "")
    embedded_labels = candidate_labels + cover_labels
    duplicate_embedded_labels = sorted(
        label for label, count in Counter(embedded_labels).items() if count > 1
    )
    property_id_label_mismatch = bool(
        property_id and candidate_labels and property_id not in candidate_labels
    )
    reference_labels = extract_property_labels(reference_sva or "")
    native_labels = extract_property_labels(native_expression or "")
    return {
        "has_issue": bool(duplicate_embedded_labels or property_id_label_mismatch),
        "candidate_labels": candidate_labels,
        "cover_labels": cover_labels,
        "reference_labels": reference_labels,
        "native_labels": native_labels,
        "duplicate_embedded_labels": duplicate_embedded_labels,
        "property_id_label_mismatch": property_id_label_mismatch,
        "candidate_reference_label_overlap": sorted(set(candidate_labels) & set(reference_labels)),
        "candidate_native_label_overlap": sorted(set(candidate_labels) & set(native_labels)),
    }


def audit_wrong_top_module(
    prediction: dict[str, object],
    config: DesignConfig,
    generated_harness_text: str,
    env: dict[str, str],
) -> dict[str, object]:
    harness_modules = extract_module_names(generated_harness_text)
    provided_top = first_text_value(
        prediction,
        ("generated_top_module", "jasper_top_module", "jasper_top", "jg_top", "top_module"),
    )
    env_top = env.get("JASPERLOOP_TOP", "")
    provided_top_mismatch = bool(provided_top and provided_top != config.top)
    return {
        "has_issue": bool(
            env_top != config.top or config.top not in harness_modules or provided_top_mismatch
        ),
        "expected_top": config.top,
        "env_top": env_top,
        "provided_top_metadata": provided_top,
        "provided_top_mismatch": provided_top_mismatch,
        "harness_modules": harness_modules,
        "expected_top_declared_in_harness": config.top in harness_modules,
    }


def audit_missing_bind_or_instantiation(
    design_id: str,
    property_module: str,
    generated_harness_text: str,
) -> dict[str, object]:
    properties_instantiated = bool(
        re.search(
            rf"\b{re.escape(property_module)}\b(?:\s*#\s*\([^;]*?\))?\s+"
            r"[A-Za-z_][A-Za-z0-9_$]*\s*\(",
            generated_harness_text,
            flags=re.DOTALL,
        )
    )
    properties_bound = bool(
        re.search(
            rf"\bbind\b[^\n;]*\b{re.escape(property_module)}\b",
            generated_harness_text,
        )
    )
    dut_instantiated = bool(
        design_id
        and re.search(
            rf"\b{re.escape(design_id)}\b(?:\s*#\s*\([^;]*?\))?\s+"
            r"[A-Za-z_][A-Za-z0-9_$]*\s*\(",
            generated_harness_text,
            flags=re.DOTALL,
        )
    )
    return {
        "has_issue": not (properties_instantiated or properties_bound),
        "property_module": property_module,
        "generated_properties_instantiated": properties_instantiated,
        "generated_properties_bound": properties_bound,
        "dut_instantiated": dut_instantiated,
    }


def audit_path_metadata(
    case: dict[str, object],
    prediction: dict[str, object],
    generated_properties: Path,
    generated_harness: Path,
    run_command: Path,
    tcl: Path,
    run_command_text: str,
    tcl_text: str,
    report_dir: Path,
) -> dict[str, object]:
    expected_paths = {
        "generated_properties": str(generated_properties),
        "generated_harness": str(generated_harness),
        "run_command": str(run_command),
        "tcl_path": str(tcl),
        "report_dir": str(report_dir),
    }
    provided = collect_path_metadata(case, prediction)
    wrong_paths = []
    for key, provided_value in provided.items():
        expected = expected_paths.get(key)
        if expected and not paths_equivalent(provided_value, expected):
            wrong_paths.append(
                {
                    "kind": key,
                    "provided": provided_value,
                    "expected": expected,
                }
            )
    missing_files = [
        key
        for key, value in expected_paths.items()
        if key != "report_dir" and not Path(value).exists()
    ]
    tcl_uses_generated_env = all(
        token in tcl_text
        for token in ("JASPERLOOP_GENERATED_PROPERTIES", "JASPERLOOP_GENERATED_HARNESS")
    )
    run_command_mentions_tcl = str(tcl) in run_command_text
    return {
        "has_issue": bool(
            wrong_paths
            or missing_files
            or not tcl_uses_generated_env
            or not run_command_mentions_tcl
        ),
        "expected_paths": expected_paths,
        "provided_path_metadata": provided,
        "wrong_paths": wrong_paths,
        "missing_files": missing_files,
        "tcl_uses_generated_artifact_env": tcl_uses_generated_env,
        "run_command_mentions_tcl": run_command_mentions_tcl,
    }


def audit_clock_reset_mismatch(
    candidate_sva: str,
    reference_sva: str | None,
    native_expression: str | None,
    cover_sva: str | None,
    expected: dict[str, object],
) -> dict[str, object]:
    candidate_event = extract_clock_event(candidate_sva)
    reference_event = extract_clock_event(reference_sva or "")
    native_event = extract_clock_event(native_expression or "")
    cover_event = extract_clock_event(cover_sva or "")
    expected_clock = str(expected.get("clock") or "")
    expected_edge = str(expected.get("clock_edge") or "")
    candidate_clock_matches = bool(
        candidate_event
        and candidate_event.get("clock") == expected_clock
        and candidate_event.get("edge") == expected_edge
    )
    candidate_disable = extract_disable_iff(candidate_sva)
    expected_reset = normalize_expression(str(expected.get("reset_condition") or ""))
    candidate_reset = normalize_expression(
        str(candidate_disable.get("condition") or "") if candidate_disable else ""
    )
    candidate_reset_matches = (
        candidate_reset == expected_reset if expected_reset else not candidate_reset
    )
    return {
        "has_issue": not (candidate_clock_matches and candidate_reset_matches),
        "expected_clock": expected_clock,
        "expected_clock_edge": expected_edge,
        "expected_reset_condition": expected.get("reset_condition"),
        "candidate_event_control": candidate_event,
        "reference_event_control": reference_event,
        "native_event_control": native_event,
        "cover_event_control": cover_event,
        "candidate_clock_matches_expected": candidate_clock_matches,
        "candidate_disable_condition": candidate_disable.get("condition")
        if candidate_disable
        else None,
        "candidate_reset_matches_expected": candidate_reset_matches,
    }


def audit_disable_iff_mismatch(
    candidate_sva: str,
    reference_sva: str | None,
    native_expression: str | None,
    cover_sva: str | None,
    expected: dict[str, object],
) -> dict[str, object]:
    candidate_disable = extract_disable_iff(candidate_sva)
    reference_disable = extract_disable_iff(reference_sva or "")
    native_disable = extract_disable_iff(native_expression or "")
    cover_disable = extract_disable_iff(cover_sva or "")
    expected_reset = str(expected.get("reset_condition") or "")
    candidate_condition = str(candidate_disable.get("condition") or "") if candidate_disable else ""
    reference_condition = str(reference_disable.get("condition") or "") if reference_disable else ""
    native_condition = str(native_disable.get("condition") or "") if native_disable else ""
    normalized_candidate = normalize_expression(candidate_condition)
    expected_mismatch = bool(
        normalize_expression(expected_reset)
        and normalized_candidate != normalize_expression(expected_reset)
    )
    reference_mismatch = bool(
        normalize_expression(reference_condition)
        and normalized_candidate != normalize_expression(reference_condition)
    )
    native_mismatch = bool(
        normalize_expression(native_condition)
        and normalized_candidate != normalize_expression(native_condition)
    )
    return {
        "has_issue": expected_mismatch or reference_mismatch or native_mismatch,
        "expected_disable_condition": expected_reset or None,
        "candidate_disable_iff": candidate_disable,
        "reference_disable_iff": reference_disable,
        "native_disable_iff": native_disable,
        "cover_disable_iff": cover_disable,
        "candidate_matches_expected": not expected_mismatch,
        "candidate_matches_reference": None
        if not reference_condition
        else not reference_mismatch,
        "candidate_matches_native": None if not native_condition else not native_mismatch,
    }


def audit_helper_code_placement(
    case: dict[str, object],
    prediction: dict[str, object],
    generated_properties_text: str,
) -> dict[str, object]:
    helper_code = str(prediction.get("helper_code") or "")
    policy = case.get("helper_code_policy")
    helper_allowed = bool(policy.get("allowed")) if isinstance(policy, dict) else False
    helper_constructs_in_candidate = helper_constructs(str(prediction.get("sva") or ""))
    helper_constructs_in_helper_code = helper_constructs(helper_code)
    helper_not_embedded = bool(
        helper_code.strip()
        and normalize_whitespace(helper_code) not in normalize_whitespace(generated_properties_text)
    )
    return {
        "has_issue": bool(
            (helper_code.strip() and not helper_allowed)
            or helper_not_embedded
            or helper_constructs_in_candidate
        ),
        "helper_code_present": bool(helper_code.strip()),
        "helper_code_allowed_by_case": helper_allowed,
        "helper_code_not_embedded_in_generated_properties": helper_not_embedded,
        "helper_constructs_in_candidate_sva": helper_constructs_in_candidate,
        "helper_constructs_in_helper_code": helper_constructs_in_helper_code,
    }


def collect_path_metadata(
    case: dict[str, object],
    prediction: dict[str, object],
) -> dict[str, str]:
    key_map = {
        "generated_properties": (
            "generated_properties_path",
            "generated_properties_file",
            "jasper_generated_properties_path",
        ),
        "generated_harness": (
            "generated_harness_path",
            "generated_harness_file",
            "jasper_generated_harness_path",
        ),
        "run_command": ("run_command_path", "jasper_run_command_path"),
        "tcl_path": ("tcl_path", "jasper_tcl_path", "check_tcl_path"),
        "report_dir": ("report_dir", "jasper_report_dir"),
    }
    result: dict[str, str] = {}
    for metadata_name, keys in key_map.items():
        for source in (prediction, case):
            value = first_text_value(source, keys)
            if value:
                result[metadata_name] = value
                break
    return result


def expected_clock_reset_metadata(
    case: dict[str, object],
    config: DesignConfig,
) -> dict[str, object]:
    clock_reset = case.get("clock_reset")
    clock_reset = clock_reset if isinstance(clock_reset, dict) else {}
    clock = str(clock_reset.get("clock") or config.clock)
    edge = str(clock_reset.get("clock_edge") or "posedge")
    reset = str(clock_reset.get("reset") or "")
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    reset_condition = ""
    if reset:
        reset_condition = f"!{reset}" if polarity == "active_low" else reset
    if not reset_condition:
        reset_condition = reset_condition_from_config(config.reset_cmd)
    return {
        "clock": clock,
        "clock_edge": edge,
        "reset": reset or reset_signal_from_condition(reset_condition),
        "reset_polarity": polarity,
        "reset_condition": reset_condition,
        "jasper_reset_command": config.reset_cmd,
    }


def reset_condition_from_config(reset_cmd: str) -> str:
    text = reset_cmd.strip()
    if not text:
        return ""
    if "-expression" in text:
        expression = text.split("-expression", 1)[1].strip()
        if expression.startswith("{") and expression.endswith("}"):
            expression = expression[1:-1].strip()
        return expression
    parts = text.split()
    if len(parts) >= 2 and parts[0] == "reset":
        return parts[1]
    return ""


def reset_signal_from_condition(condition: str) -> str:
    stripped = condition.strip()
    stripped = stripped[1:].strip() if stripped.startswith("!") else stripped
    return re.sub(r"[^A-Za-z0-9_$].*$", "", stripped)


def first_text_value(data: object, keys: tuple[str, ...]) -> str | None:
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if value is not None and not isinstance(value, (dict, list, tuple)):
                text = str(value).strip()
                if text:
                    return text
        for value in data.values():
            found = first_text_value(value, keys)
            if found:
                return found
    elif isinstance(data, (list, tuple)):
        for value in data:
            found = first_text_value(value, keys)
            if found:
                return found
    return None


def extract_property_labels(text: str) -> list[str]:
    return re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_$]*)\s*:\s*(?=(?:assert|cover|assume)\s+property\b)",
        text,
        flags=re.IGNORECASE,
    )


def extract_module_names(text: str) -> list[str]:
    return re.findall(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b", text)


def extract_clock_event(text: str) -> dict[str, str] | None:
    match = re.search(
        r"@\s*\(\s*(posedge|negedge)\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return {"raw": match.group(0), "edge": match.group(1).lower(), "clock": match.group(2)}


def extract_disable_iff(text: str) -> dict[str, str] | None:
    match = re.search(r"\bdisable\s+iff\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    open_index = text.find("(", match.end())
    if open_index < 0:
        return {"raw": text[match.start() :].strip(), "condition": ""}
    close_index = find_matching_paren(text, open_index)
    if close_index is None:
        return {"raw": text[match.start() :].strip(), "condition": ""}
    return {
        "raw": text[match.start() : close_index + 1].strip(),
        "condition": text[open_index + 1 : close_index].strip(),
    }


def find_matching_paren(text: str, open_index: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def normalized_sva(text: str | None) -> str:
    return normalize_whitespace(text or "").rstrip(";").lower()


def normalize_expression(text: str) -> str:
    stripped = strip_enclosing_parens(text.strip())
    return re.sub(r"\s+", "", stripped).lower()


def strip_enclosing_parens(text: str) -> str:
    stripped = text.strip()
    while stripped.startswith("("):
        close_index = find_matching_paren(stripped, 0)
        if close_index != len(stripped) - 1:
            break
        stripped = stripped[1:-1].strip()
    return stripped


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def helper_constructs(text: str) -> list[str]:
    tokens = (
        "module",
        "endmodule",
        "always",
        "always_ff",
        "always_comb",
        "assign",
        "function",
        "endfunction",
        "task",
        "endtask",
        "logic",
        "wire",
        "reg",
        "typedef",
        "localparam",
        "parameter",
    )
    found = []
    for token in tokens:
        if re.search(rf"\b{re.escape(token)}\b", text):
            found.append(token)
    return found


def paths_equivalent(left: str, right: str) -> bool:
    return normalize_path_text(left) == normalize_path_text(right)


def normalize_path_text(path_text: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(path_text))
    path = Path(expanded)
    if not path.is_absolute():
        path = ROOT / path
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = path.absolute()
    return os.path.normcase(str(resolved))


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
    selected = [
        line.strip()
        for line in lines
        if any(keyword in line.lower() for keyword in keywords)
    ]
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
    parser.add_argument("--design-manifest", type=Path)
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
        design_manifest=args.design_manifest,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
