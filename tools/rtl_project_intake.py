"""Build a dynamic RTL project manifest for RTL2Repair flows."""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copilot.retrieval.design2sva_context import (
    Design2SVAContextOptions,
    build_design2sva_context,
)
from copilot.retrieval.rtl_index import build_rtl_index, get_clock_reset_candidates

RTL_EXTENSIONS = {".sv", ".v", ".svh", ".vh"}
SCHEMA_VERSION = "rtl_project_manifest_v1"
TASK_SCHEMA_VERSION = "rtl2sva_task_v1"


class IntakeError(ValueError):
    """Raised when RTL intake cannot produce a safe manifest."""


@dataclass(frozen=True)
class IntakeOutputs:
    manifest: dict[str, Any]
    tasks: dict[str, Any]
    report_path: Path
    tasks_path: Path
    rtl_index_path: Path


def parse_define(value: str) -> tuple[str, str]:
    if "=" not in value:
        return value, "1"
    name, raw = value.split("=", 1)
    if not name:
        raise IntakeError("Define names must be non-empty.")
    return name, raw


def expand_rtl_inputs(inputs: list[str], cwd: Path | None = None) -> list[Path]:
    cwd = cwd or Path.cwd()
    paths: list[Path] = []
    for item in inputs:
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        if candidate.exists():
            paths.extend(paths_from_existing(candidate))
            continue
        matches = [
            Path(match)
            for match in glob.glob(str(candidate), recursive=True)
            if Path(match).exists()
        ]
        for match in matches:
            paths.extend(paths_from_existing(match))
    unique = sorted({path.resolve() for path in paths if path.suffix.lower() in RTL_EXTENSIONS})
    if not unique:
        joined = ", ".join(inputs)
        raise IntakeError(f"No RTL files found for inputs: {joined}")
    return unique


def paths_from_existing(path: Path) -> list[Path]:
    if path.is_dir():
        return [
            child
            for child in path.rglob("*")
            if child.is_file() and child.suffix.lower() in RTL_EXTENSIONS
        ]
    return [path] if path.is_file() and path.suffix.lower() in RTL_EXTENSIONS else []


def infer_top_module(index: dict[str, Any], requested: str | None = None) -> str:
    modules = index.get("modules", {})
    if requested:
        if requested not in modules:
            choices = ", ".join(sorted(modules)) or "<none>"
            raise IntakeError(f"Requested top module {requested!r} was not found. Choices: {choices}")
        return requested
    if len(modules) == 1:
        return str(next(iter(modules)))
    if not modules:
        raise IntakeError("No modules were parsed from RTL files.")

    instantiated = {
        str(instance.get("module"))
        for module in modules.values()
        for instance in module.get("instances", [])
        if instance.get("module")
    }
    candidates = sorted(set(modules) - instantiated)
    if len(candidates) == 1:
        return candidates[0]
    choices = ", ".join(sorted(modules))
    if candidates:
        candidate_text = ", ".join(candidates)
        raise IntakeError(
            "Ambiguous top module; pass --top. "
            f"Top-level candidates: {candidate_text}. All parsed modules: {choices}"
        )
    raise IntakeError(f"Ambiguous top module; pass --top. Parsed modules: {choices}")


def infer_clock_reset(
    index: dict[str, Any],
    top_module: str,
    clock: str | None,
    reset: str | None,
    reset_polarity: str,
) -> dict[str, str | None]:
    module = index.get("modules", {}).get(top_module, {})
    known = module_signal_names(module)
    candidates = get_clock_reset_candidates(index)
    clocks = [name for name in candidates.get("clocks", []) if name in known]
    resets = [name for name in candidates.get("resets", []) if name in known]
    selected_clock = select_signal(
        requested=clock,
        candidates=clocks,
        known=known,
        kind="clock",
        required=True,
    )
    selected_reset = select_signal(
        requested=reset,
        candidates=resets,
        known=known,
        kind="reset",
        required=False,
    )
    return {
        "clock": selected_clock,
        "clock_edge": "posedge",
        "reset": selected_reset,
        "reset_polarity": reset_polarity,
    }


def select_signal(
    *,
    requested: str | None,
    candidates: list[str],
    known: set[str],
    kind: str,
    required: bool,
) -> str | None:
    if requested:
        if requested not in known:
            choices = ", ".join(sorted(known)) or "<none>"
            raise IntakeError(f"Requested {kind} {requested!r} is not a signal on the top module. Choices: {choices}")
        return requested
    unique = sorted(set(candidates))
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        choices = ", ".join(unique)
        raise IntakeError(f"Ambiguous {kind} candidates; pass --{kind}. Candidates: {choices}")
    if required:
        raise IntakeError(f"Could not infer {kind}; pass --{kind}.")
    return None


def module_signal_names(module: dict[str, Any]) -> set[str]:
    names = {str(port.get("name")) for port in module.get("ports", []) if port.get("name")}
    names.update(str(signal.get("name")) for signal in module.get("signals", []) if signal.get("name"))
    return names


def rank_visible_signals(
    index: dict[str, Any],
    rtl_paths: list[Path],
    top_module: str,
    clock_reset: dict[str, str | None],
) -> list[str]:
    module = index.get("modules", {}).get(top_module, {})
    top_ports = [str(port.get("name")) for port in module.get("ports", []) if port.get("name")]
    focus = tuple(str(value) for value in clock_reset.values() if isinstance(value, str) and value)
    context = build_design2sva_context(
        rtl_paths,
        Design2SVAContextOptions(module_name=top_module, focus_signals=focus),
    )
    return dedupe([*top_ports, *context.get("visible_signals", [])])


def signal_roles(visible_signals: list[str], clock_reset: dict[str, str | None]) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    clock = clock_reset.get("clock")
    reset = clock_reset.get("reset")
    if isinstance(clock, str):
        roles[clock] = ["clock"]
    if isinstance(reset, str):
        roles.setdefault(reset, []).append("reset")
    for signal in visible_signals:
        lowered = signal.lower()
        if signal in roles:
            continue
        inferred: list[str] = []
        if "valid" in lowered:
            inferred.append("valid")
        if "ready" in lowered:
            inferred.append("ready")
        if lowered.startswith(("gnt", "grant")) or "grant" in lowered:
            inferred.append("grant")
        if lowered.startswith(("req", "request")) or "request" in lowered:
            inferred.append("request")
        if lowered in {"full", "empty"}:
            inferred.append(lowered)
        if "state" in lowered:
            inferred.append("state")
        if inferred:
            roles[signal] = inferred
    return roles


def build_auto_intents(visible_signals: list[str], clock_reset: dict[str, str | None]) -> list[str]:
    signals = set(visible_signals)
    lowered = {signal.lower(): signal for signal in visible_signals}
    intents: list[str] = []
    if clock_reset.get("reset"):
        intents.append("After reset, observable state and control outputs remain in legal reset-consistent values.")

    for valid in sorted(signal for signal in signals if signal.endswith("_valid")):
        prefix = valid[: -len("_valid")]
        ready = f"{prefix}_ready"
        if ready in signals:
            intents.append(f"When {valid} is asserted and {ready} is deasserted, transferred data and valid state remain stable.")

    if {"full", "empty"} <= signals or {"wr_en", "rd_en"} & signals:
        intents.append("The FIFO control logic must not allow underflow or overflow conditions.")

    grant_signals = sorted(signal for signal in signals if signal.lower().startswith(("gnt", "grant")))
    if len(grant_signals) >= 2:
        joined = " and ".join(grant_signals[:2])
        intents.append(f"The arbiter must not assert mutually exclusive grants such as {joined} in the same cycle.")

    if {"psel", "penable"} <= set(lowered):
        intents.append("APB setup and access phases must follow the legal PSEL/PENABLE sequencing.")

    if any("state" in signal.lower() for signal in signals):
        intents.append("FSM state updates must remain within legal state encodings and transitions.")

    if not intents:
        intents.append("Observable control outputs should not enter illegal simultaneous states.")
    return dedupe(intents)


def build_tasks(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    spec_path: Path | None,
) -> dict[str, Any]:
    if spec_path:
        spec_text = spec_path.read_text(encoding="utf-8")
        intents = spec_intents(spec_text)
        source = "spec"
    else:
        intents = build_auto_intents(
            list(manifest["visible_signals"]),
            dict(manifest["clock_reset"]),
        )
        source = "auto_intent"

    tasks = []
    for index, intent in enumerate(intents, start=1):
        property_id = f"p_auto_{index:02d}"
        tasks.append(
            {
                "schema_version": TASK_SCHEMA_VERSION,
                "task_id": f"{manifest['project_id']}::{property_id}",
                "task_type": "rtl2sva",
                "project_id": manifest["project_id"],
                "design_id": manifest["design_id"],
                "property_id": property_id,
                "module_name": manifest["top_module"],
                "intent": intent,
                "rtl_project_manifest_path": portable_path(manifest_path),
                "design_rtl_paths": manifest["rtl_files"],
                "visible_signals": manifest["visible_signals"],
                "clock_reset": manifest["clock_reset"],
                "helper_code_policy": {
                    "allowed": False,
                    "allowed_kinds": [],
                    "max_lines": 0,
                    "rationale": "RTL2SVA intake tasks default to pure assertions until a later policy allows helper code.",
                },
                "source": source,
            }
        )
    return {"schema_version": "rtl2sva_tasks_v1", "project_id": manifest["project_id"], "tasks": tasks}


def spec_intents(text: str) -> list[str]:
    candidates = [
        normalize_sentence(line)
        for line in text.splitlines()
        if normalize_sentence(line) and not line.strip().startswith("#")
    ]
    return candidates[:8] or ["Candidate assertion intent derived from the provided specification."]


def normalize_sentence(value: str) -> str:
    value = re.sub(r"^[*\-\d.)\s]+", "", value.strip())
    return " ".join(value.split())


def write_report(
    *,
    manifest: dict[str, Any],
    tasks: dict[str, Any],
    report_path: Path,
    rtl_index_path: Path,
) -> None:
    lines = [
        "# RTL Project Intake Report",
        "",
        f"- project_id: {manifest['project_id']}",
        f"- design_id: {manifest['design_id']}",
        f"- top_module: {manifest['top_module']}",
        f"- rtl_files: {len(manifest['rtl_files'])}",
        f"- clock: {manifest['clock_reset']['clock']}",
        f"- reset: {manifest['clock_reset']['reset']}",
        f"- reset_polarity: {manifest['clock_reset']['reset_polarity']}",
        f"- visible_signals: {len(manifest['visible_signals'])}",
        f"- generated_tasks: {len(tasks['tasks'])}",
        f"- rtl_index: {portable_path(rtl_index_path)}",
        "",
        "## Candidate Intents",
        "",
    ]
    for task in tasks["tasks"]:
        lines.append(f"- {task['property_id']}: {task['intent']}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_rtl_project(
    *,
    rtl_inputs: list[str],
    out_path: Path,
    top: str | None = None,
    clock: str | None = None,
    reset: str | None = None,
    reset_polarity: str = "unknown",
    spec: Path | None = None,
    include_dirs: list[str] | None = None,
    defines: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> IntakeOutputs:
    cwd = cwd or Path.cwd()
    rtl_paths = expand_rtl_inputs(rtl_inputs, cwd=cwd)
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rtl_index_path = out_path.parent / "rtl_index.json"
    index = build_rtl_index(rtl_paths, out_path=rtl_index_path)
    top_module = infer_top_module(index, top)
    clock_reset = infer_clock_reset(index, top_module, clock, reset, reset_polarity)
    visible_signals = rank_visible_signals(index, rtl_paths, top_module, clock_reset)

    project_id = sanitize_id(top_module)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "design_id": top_module,
        "rtl_files": [portable_path(path) for path in rtl_paths],
        "top_module": top_module,
        "clock_reset": clock_reset,
        "include_dirs": [portable_path(Path(path)) for path in include_dirs or []],
        "defines": defines or {},
        "assumption_files": [],
        "property_module": "generated_sva_properties",
        "property_instance": "generated_properties_i",
        "visible_signals": visible_signals,
        "signal_roles": signal_roles(visible_signals, clock_reset),
        "harness": {"strategy": "render_generic", "harness_path": None},
    }
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    tasks_path = out_path.parent / "rtl2sva_tasks.json"
    tasks = build_tasks(manifest=manifest, manifest_path=out_path, spec_path=spec)
    tasks_path.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")

    report_path = out_path.parent / "intake_report.md"
    write_report(manifest=manifest, tasks=tasks, report_path=report_path, rtl_index_path=rtl_index_path)
    return IntakeOutputs(
        manifest=manifest,
        tasks=tasks,
        report_path=report_path,
        tasks_path=tasks_path,
        rtl_index_path=rtl_index_path,
    )


def portable_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_id(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return sanitized or "rtl_project"


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", action="append", required=True, help="RTL file, directory, or glob. Repeatable.")
    parser.add_argument("--top", help="Top module name.")
    parser.add_argument("--clock", help="Top-level clock signal.")
    parser.add_argument("--reset", help="Top-level reset signal.")
    parser.add_argument(
        "--reset-polarity",
        choices=["active_high", "active_low", "unknown"],
        default="unknown",
    )
    parser.add_argument("--spec", type=Path, help="Optional spec text/Markdown file.")
    parser.add_argument("--include-dir", action="append", default=[], help="RTL include directory. Repeatable.")
    parser.add_argument("--define", action="append", default=[], help="Verilog define NAME or NAME=VALUE. Repeatable.")
    parser.add_argument("--out", type=Path, required=True, help="Output rtl_project_manifest.json path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        defines = dict(parse_define(item) for item in args.define)
        outputs = create_rtl_project(
            rtl_inputs=args.rtl,
            out_path=args.out,
            top=args.top,
            clock=args.clock,
            reset=args.reset,
            reset_polarity=args.reset_polarity,
            spec=args.spec,
            include_dirs=args.include_dir,
            defines=defines,
        )
    except IntakeError as exc:
        print(f"rtl_project_intake: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"manifest": portable_path(args.out), "tasks": portable_path(outputs.tasks_path), "report": portable_path(outputs.report_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
