#!/usr/bin/env python3
"""Export or summarize Codex prompts without sending them to Codex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.design2sva_agent import (  # noqa: E402
    allowed_signal_set as design2sva_allowed_signal_set,
)
from copilot.agents.design2sva_agent import build_prompt as build_design2sva_prompt  # noqa: E402
from copilot.agents.coverage_closure_agent import build_prompt as build_coverage_prompt  # noqa: E402
from copilot.agents.dv_triage_agent import build_prompt as build_triage_prompt  # noqa: E402
from copilot.agents.sva_repair_agent import build_prompt as build_repair_prompt  # noqa: E402
from copilot.retrieval import Design2SVAContextOptions, build_design2sva_context  # noqa: E402
from scripts.build_all_evidence_packets import iter_case_files, resolve_repo_path  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402

TASKS = ["sva_repair", "triage", "coverage"]
PROMPT_TASKS = [*TASKS, "design2sva"]
GOLD_PROMPT_MARKERS = {
    "gold_label",
    "expected_issue_type",
    "expected_next_action",
    "reference_sva",
    "expected_proof_status",
}


def load_repair_cases(path: Path, limit: int | None) -> list[dict[str, object]]:
    data = json.loads(resolve_repo_path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    cases = [case for case in data if isinstance(case, dict)]
    return cases[:limit] if limit is not None else cases


def load_design2sva_cases(path: Path, limit: int | None) -> list[dict[str, Any]]:
    data = json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    cases = [case for case in data if isinstance(case, dict)]
    return cases[:limit] if limit is not None else cases


def build_design2sva_context_for_case(
    case: dict[str, Any],
    context_budget: int,
) -> dict[str, Any]:
    return build_design2sva_context(
        [resolve_repo_path(Path(str(case["design_rtl_path"])))],
        Design2SVAContextOptions(
            module_name=str(case.get("module_name") or case.get("design_id") or ""),
            focus_signals=tuple(str(signal) for signal in case.get("visible_signals", [])),
            property_intent=str(case.get("intent") or ""),
            visible_signal_budget=context_budget,
        ),
    )


def packet_path_for(case: dict[str, object], packet_root: Path) -> Path:
    return packet_root / str(case["design_id"]) / str(case["case_id"]) / "evidence_packet.json"


def load_or_build_packet(case_path: Path, packet_root: Path, packet_source: str) -> dict[str, object]:
    case = json.loads(case_path.read_text())
    packet_path = packet_path_for(case, packet_root)
    if packet_source == "actual" and packet_path.exists():
        return json.loads(packet_path.read_text())
    return build_packet(case_path=case_path)


def iter_prompts(args: argparse.Namespace) -> list[dict[str, object]]:
    tasks = TASKS if args.task == "all" else [args.task]
    rows: list[dict[str, object]] = []
    for task in tasks:
        if task == "design2sva":
            for index, case in enumerate(
                load_design2sva_cases(args.design2sva_cases, args.limit),
                start=1,
            ):
                context = build_design2sva_context_for_case(case, args.context_budget)
                prompt = build_design2sva_prompt(case, context)
                visible_signal_count = len(design2sva_allowed_signal_set(case, context))
                retrieved_visible_signals = {
                    str(signal) for signal in context.get("visible_signals", [])
                }
                rows.append(
                    build_row(
                        task,
                        index,
                        case,
                        prompt,
                        extra={
                            "task_visible_signal_count": len(case.get("visible_signals", [])),
                            "retrieved_visible_signal_count": len(retrieved_visible_signals),
                            "visible_signal_set_size": visible_signal_count,
                            "signal_budget": args.context_budget,
                        },
                    )
                )
        elif task == "sva_repair":
            for index, case in enumerate(load_repair_cases(args.repair_cases, args.limit), start=1):
                prompt = build_repair_prompt(
                    case,
                    failed_sva=str(case.get("broken_sva", "")),
                    feedback="Prompt preview: no JasperGold run was executed.",
                    round_index=1,
                )
                rows.append(build_row(task, index, case, prompt))
        else:
            case_paths = iter_case_files(args.cases)
            if task == "coverage":
                case_paths = [
                    path
                    for path in case_paths
                    if json.loads(path.read_text()).get("task_type") == "coverage_closure"
                ]
            if args.limit is not None:
                case_paths = case_paths[: args.limit]
            for index, case_path in enumerate(case_paths, start=1):
                case = json.loads(case_path.read_text())
                packet = load_or_build_packet(case_path, resolve_repo_path(args.packet_root), args.packet_source)
                packet = redact_packet(packet) if args.redact_evidence else packet
                prompt = build_coverage_prompt(packet) if task == "coverage" else build_triage_prompt(packet)
                rows.append(build_row(task, index, case, prompt))
    return rows


def redact_packet(packet: dict[str, object]) -> dict[str, object]:
    redacted = dict(packet)
    redacted["rtl_context"] = {"redacted": True}
    redacted["trace_summaries"] = []
    cex = redacted.get("counterexample_summary")
    if isinstance(cex, dict):
        cex = dict(cex)
        cex.pop("events", None)
        cex.pop("semantic_events", None)
        redacted["counterexample_summary"] = cex
    jasper = redacted.get("jasper_result")
    if isinstance(jasper, dict):
        jasper = dict(jasper)
        jasper["trace_files"] = []
        redacted["jasper_result"] = jasper
    return redacted


def build_row(
    task: str,
    index: int,
    case: dict[str, object],
    prompt: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    prompt_id = f"{task}_{index:03d}_{case.get('case_id', 'unknown')}"
    metadata = case.get("evaluation_metadata")
    reference_sva = ""
    if isinstance(metadata, dict):
        reference_sva = str(metadata.get("reference_sva") or "")
    contains_reference_sva_value = bool(reference_sva and reference_sva in prompt)
    contains_gold_marker = any(marker in prompt for marker in GOLD_PROMPT_MARKERS)
    row = {
        "prompt_id": prompt_id,
        "task": task,
        "case_id": case.get("case_id"),
        "design_id": case.get("design_id"),
        "property_id": case.get("property_id"),
        "chars": len(prompt),
        "approx_tokens": max(1, len(prompt) // 4),
        "contains_gold_label": contains_gold_marker or contains_reference_sva_value,
        "contains_reference_sva_key": "reference_sva" in prompt,
        "contains_reference_sva_value": contains_reference_sva_value,
        "contains_expected_proof_status": "expected_proof_status" in prompt,
        "contains_expected_proof_status_key": "expected_proof_status" in prompt,
        "contains_rtl_context": "rtl_context" in prompt or "source_excerpts" in prompt,
        "contains_jasper_evidence": "jasper_result" in prompt or "JASPER_FEEDBACK" in prompt,
        "prompt": prompt,
    }
    if extra:
        row.update(extra)
    return row


def audit_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    summary_rows = [{key: value for key, value in row.items() if key != "prompt"} for row in rows]
    visible_sizes = [
        int(row["visible_signal_set_size"])
        for row in summary_rows
        if "visible_signal_set_size" in row
    ]
    return {
        "num_prompts": len(summary_rows),
        "num_cases": len({str(row.get("case_id")) for row in summary_rows}),
        "max_chars": max((int(row["chars"]) for row in summary_rows), default=0),
        "total_approx_tokens": sum(int(row["approx_tokens"]) for row in summary_rows),
        "num_with_gold_label": sum(1 for row in summary_rows if row["contains_gold_label"]),
        "num_with_reference_sva_key": sum(
            1 for row in summary_rows if row.get("contains_reference_sva_key")
        ),
        "num_with_reference_sva_value": sum(
            1 for row in summary_rows if row.get("contains_reference_sva_value")
        ),
        "num_with_expected_proof_status": sum(
            1 for row in summary_rows if row.get("contains_expected_proof_status")
        ),
        "num_with_rtl_context": sum(1 for row in summary_rows if row["contains_rtl_context"]),
        "num_with_jasper_evidence": sum(
            1 for row in summary_rows if row["contains_jasper_evidence"]
        ),
        "visible_signal_set_size": {
            "min": min(visible_sizes) if visible_sizes else None,
            "max": max(visible_sizes) if visible_sizes else None,
            "average": (
                sum(visible_sizes) / len(visible_sizes) if visible_sizes else None
            ),
        },
        "prompts": summary_rows,
    }


def render_audit_markdown(payload: dict[str, object], command: str) -> str:
    prompts = payload.get("prompts", [])
    prompt_rows = prompts if isinstance(prompts, list) else []
    visible = payload.get("visible_signal_set_size", {})
    visible_text = "N/A"
    if isinstance(visible, dict) and visible.get("min") is not None:
        visible_text = (
            f"min={visible.get('min')}, max={visible.get('max')}, "
            f"avg={float(visible.get('average', 0.0)):.2f}"
        )
    lines = [
        "# Expanded Design2SVA Prompt Audit",
        "",
        "This audit is generated locally and does not send prompts to an external LLM.",
        "",
        f"Command: `{command}`",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Prompts | {payload.get('num_prompts')} |",
        f"| Cases | {payload.get('num_cases')} |",
        f"| Gold labels absent | {payload.get('num_with_gold_label') == 0} |",
        f"| `reference_sva` key present | {payload.get('num_with_reference_sva_key')} |",
        f"| `reference_sva` value present | {payload.get('num_with_reference_sva_value')} |",
        f"| `expected_proof_status` present | {payload.get('num_with_expected_proof_status')} |",
        f"| Jasper evidence included | {payload.get('num_with_jasper_evidence', 0) > 0} |",
        f"| Visible signal set size | {visible_text} |",
        f"| Total approximate tokens | {payload.get('total_approx_tokens')} |",
        f"| Max prompt characters | {payload.get('max_chars')} |",
        "",
        "## Prompt Rows",
        "",
        "| Prompt | Case | Design | Property | Chars | Approx tokens | Visible signals | Gold absent | Jasper evidence |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in prompt_rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("prompt_id")),
                    str(row.get("case_id")),
                    str(row.get("design_id")),
                    str(row.get("property_id")),
                    str(row.get("chars")),
                    str(row.get("approx_tokens")),
                    str(row.get("visible_signal_set_size", "N/A")),
                    str(not bool(row.get("contains_gold_label"))),
                    str(bool(row.get("contains_jasper_evidence"))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Gold-label checks treat `reference_sva`, `expected_proof_status`, "
            "`gold_label`, `expected_issue_type`, and exact reference SVA text as "
            "forbidden prompt content.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    rows: list[dict[str, object]],
    out_dir: Path,
    summary_only: bool,
    audit_md: Path | None = None,
    command: str = "",
) -> dict[str, object]:
    out_dir = resolve_repo_path(out_dir)
    summary_rows = []
    if not summary_only:
        out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        row_for_summary = {key: value for key, value in row.items() if key != "prompt"}
        if not summary_only:
            prompt_path = out_dir / f"{row['prompt_id']}.txt"
            prompt_path.write_text(str(row["prompt"]) + "\n")
            row_for_summary["prompt_file"] = display_path(prompt_path)
        summary_rows.append(row_for_summary)

    payload = audit_summary(summary_rows)
    print(json.dumps(payload, indent=2))
    if not summary_only:
        (out_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")
    if audit_md:
        audit_path = resolve_repo_path(audit_md)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(render_audit_markdown(payload, command), encoding="utf-8")
    return payload


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["all", *PROMPT_TASKS], default="all")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--repair-cases", type=Path, default=Path("benchmarks/sva_repair_cases.json"))
    parser.add_argument(
        "--design2sva-cases",
        type=Path,
        default=Path("benchmarks/design2sva_cases.json"),
    )
    parser.add_argument("--context-budget", "--design2sva-context-budget", type=int, default=24)
    parser.add_argument(
        "--cases",
        nargs="+",
        type=Path,
        default=[
            Path("benchmarks/arbiter_rr2/cases"),
            Path("benchmarks/rv_buffer/cases"),
            Path("benchmarks/apb_regblock/cases"),
        ],
    )
    parser.add_argument("--packet-root", type=Path, default=Path("jasper/reports/case_packets"))
    parser.add_argument("--packet-source", choices=["actual", "minimal"], default="actual")
    parser.add_argument("--redact-evidence", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation/prompt_previews"))
    parser.add_argument("--audit-md", "--audit-markdown", type=Path)
    parser.add_argument("--require-no-gold-labels", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    payload = write_outputs(
        iter_prompts(args),
        args.out_dir,
        args.summary_only,
        audit_md=args.audit_md,
        command="python " + " ".join(sys.argv),
    )
    if args.require_no_gold_labels and payload["num_with_gold_label"] != 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
