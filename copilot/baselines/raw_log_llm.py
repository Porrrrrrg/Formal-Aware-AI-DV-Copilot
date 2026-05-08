#!/usr/bin/env python3
"""Raw JasperGold log LLM baseline.

The baseline deliberately withholds manifests, signal role maps, structured
counterexample summaries, and coverage-plan metadata. It can call the same
command-based LLM backend as the main agent, or fall back to weak text rules so
the evaluation runner remains executable without an API key.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from copilot.json_utils import coerce_string_list
from copilot.llm_client import call_llm_json, llm_configured

ACTION_BY_ISSUE = {
    "rtl_design_bug": "fix_rtl",
    "assertion_property_bug": "fix_assertion_property",
    "assumption_constraint_bug": "fix_assumption_constraint",
    "testbench_stimulus_bug": "fix_testbench_or_stimulus",
    "reachable_coverage_gap": "add_directed_test_or_sequence",
    "unreachable_or_invalid_coverage_goal": "prove_unreachable_or_waive_coverage_goal",
}

ALLOWED_ISSUES = set(ACTION_BY_ISSUE)


def diagnose_from_raw_log(
    packet: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    raw_context = collect_raw_context(packet)
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(build_prompt(packet, raw_context), llm_command)
            return normalize_output(packet, response.json_object, raw_context)
        except Exception as exc:  # noqa: BLE001 - deterministic fallback is intentional.
            fallback = raw_log_fallback(packet, raw_context)
            fallback["llm_error"] = str(exc)
            return fallback
    return raw_log_fallback(packet, raw_context)


def collect_raw_context(packet: dict[str, object]) -> str:
    chunks = []
    jasper = packet.get("jasper_result", {})
    if isinstance(jasper, dict):
        source_report = jasper.get("source_report")
        if source_report:
            chunks.append(render_file_excerpt(Path(str(source_report)), "JasperGold report"))
        trace_files = jasper.get("trace_files", [])
        if isinstance(trace_files, list):
            for trace_file in trace_files[:2]:
                chunks.append(render_file_excerpt(Path(str(trace_file)), "JasperGold trace", max_chars=12000))
        if not chunks:
            properties = jasper.get("properties", [])
            chunks.append("Parsed report rows:\n" + json.dumps(properties, indent=2))

    if not chunks:
        chunks.append("No raw JasperGold report or trace text is available for this packet.")
    return "\n\n".join(chunks)


def render_file_excerpt(path: Path, title: str, max_chars: int = 20000) -> str:
    if not path.exists():
        return f"{title}: missing file {path}"
    text = read_text_maybe_gzip(path)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]..."
    return f"{title}: {path}\n{text}"


def read_text_maybe_gzip(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\x1f\x8b") or path.suffix == ".gz":
        return gzip.decompress(raw).decode(errors="ignore")
    return raw.decode(errors="ignore")


def build_prompt(packet: dict[str, object], raw_context: str | None = None) -> str:
    failing_property = packet.get("failing_property", {})
    property_id = ""
    if isinstance(failing_property, dict):
        property_id = str(failing_property.get("property_id", ""))
    metadata = {
        "case_id": packet.get("case_id"),
        "design_id": packet.get("design_id"),
        "task_type": packet.get("task_type"),
        "property_id": property_id,
    }
    return (
        "You are evaluating a JasperGold failure using raw logs only. "
        "Classify the most likely issue type and next action. "
        "Do not assume access to manifests, signal-role maps, or coverage plans. "
        "Return JSON matching diagnosis_output.schema.json.\n\n"
        "Metadata:\n"
        + json.dumps(metadata, indent=2)
        + "\n\nRaw JasperGold text:\n"
        + (raw_context if raw_context is not None else collect_raw_context(packet))
    )


def raw_log_fallback(packet: dict[str, object], raw_context: str | None = None) -> dict[str, object]:
    raw_context = raw_context if raw_context is not None else collect_raw_context(packet)
    issue = infer_issue_type_from_raw(packet, raw_context)
    return {
        "case_id": str(packet.get("case_id", "unknown")),
        "predicted_issue_type": issue,
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": "Raw-log baseline prediction from JasperGold text only.",
                "evidence": collect_raw_evidence(raw_context),
            }
        ],
        "suspect_rtl_signals": [],
        "suspect_assertions_or_assumptions": [],
        "recommended_next_action": ACTION_BY_ISSUE[issue],
        "debug_checklist": ["Inspect the full JasperGold report and trace."],
    }


def infer_issue_type_from_raw(packet: dict[str, object], raw_context: str) -> str:
    text = raw_context.lower()
    failing_property = packet.get("failing_property", {})
    property_id = ""
    if isinstance(failing_property, dict):
        property_id = str(failing_property.get("property_id", "")).lower()
    task_type = str(packet.get("task_type", ""))
    property_blob = "\n".join(line for line in text.splitlines() if property_id and property_id in line)

    if "vacuous" in property_blob:
        return "assumption_constraint_bug"
    if task_type == "coverage_closure" or property_id.startswith("cov_"):
        if "unreachable" in property_blob and "covered" not in property_blob:
            return "unreachable_or_invalid_coverage_goal"
        if "covered" in property_blob or "reachable" in property_blob:
            return "reachable_coverage_gap"
        return "reachable_coverage_gap"
    if property_id.endswith("_bad") or "_bad" in property_id:
        return "assertion_property_bug"
    if "falsified" in property_blob or "cex" in property_blob or "failed" in property_blob:
        return "rtl_design_bug"
    return "assertion_property_bug"


def collect_raw_evidence(raw_context: str) -> list[str]:
    evidence = []
    for line in raw_context.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in ["falsified", "failed", "vacuous", "covered", "unreachable"]):
            evidence.append(line.strip())
        if len(evidence) >= 4:
            break
    return evidence or ["No strong status line found in raw log excerpt."]


def normalize_output(
    packet: dict[str, object],
    output: dict[str, object],
    raw_context: str,
) -> dict[str, object]:
    issue = str(output.get("predicted_issue_type", ""))
    if issue not in ALLOWED_ISSUES:
        issue = infer_issue_type_from_raw(packet, raw_context)
    action = str(output.get("recommended_next_action", ""))
    if action not in set(ACTION_BY_ISSUE.values()):
        action = ACTION_BY_ISSUE[issue]
    roots = output.get("root_cause_ranked")
    if not isinstance(roots, list) or not roots:
        roots = raw_log_fallback(packet, raw_context)["root_cause_ranked"]
    return {
        "case_id": str(output.get("case_id", packet.get("case_id", "unknown"))),
        "predicted_issue_type": issue,
        "root_cause_ranked": roots,
        "suspect_rtl_signals": coerce_string_list(output.get("suspect_rtl_signals")),
        "suspect_assertions_or_assumptions": coerce_string_list(
            output.get("suspect_assertions_or_assumptions")
        ),
        "recommended_next_action": action,
        "debug_checklist": coerce_string_list(output.get("debug_checklist"))
        or ["Inspect the full JasperGold report and trace."],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text())
    raw_context = collect_raw_context(packet)
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(packet, raw_context) + "\n")
    print(
        json.dumps(
            diagnose_from_raw_log(packet, use_llm=args.llm, llm_command=args.llm_command),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
