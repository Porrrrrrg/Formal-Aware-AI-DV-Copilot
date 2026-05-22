#!/usr/bin/env python3
"""Export or summarize Codex prompts without sending them to Codex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.coverage_closure_agent import build_prompt as build_coverage_prompt  # noqa: E402
from copilot.agents.dv_triage_agent import build_prompt as build_triage_prompt  # noqa: E402
from copilot.agents.sva_repair_agent import build_prompt as build_repair_prompt  # noqa: E402
from scripts.build_all_evidence_packets import iter_case_files, resolve_repo_path  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402

TASKS = ["sva_repair", "triage", "coverage"]


def load_repair_cases(path: Path, limit: int | None) -> list[dict[str, object]]:
    data = json.loads(resolve_repo_path(path).read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    cases = [case for case in data if isinstance(case, dict)]
    return cases[:limit] if limit is not None else cases


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
        if task == "sva_repair":
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


def build_row(task: str, index: int, case: dict[str, object], prompt: str) -> dict[str, object]:
    prompt_id = f"{task}_{index:03d}_{case.get('case_id', 'unknown')}"
    return {
        "prompt_id": prompt_id,
        "task": task,
        "case_id": case.get("case_id"),
        "design_id": case.get("design_id"),
        "property_id": case.get("property_id"),
        "chars": len(prompt),
        "approx_tokens": max(1, len(prompt) // 4),
        "contains_gold_label": "gold_label" in prompt or "expected_issue_type" in prompt,
        "contains_rtl_context": "rtl_context" in prompt and "source_excerpts" in prompt,
        "contains_jasper_evidence": "jasper_result" in prompt or "JASPER_FEEDBACK" in prompt,
        "prompt": prompt,
    }


def write_outputs(rows: list[dict[str, object]], out_dir: Path, summary_only: bool) -> None:
    out_dir = resolve_repo_path(out_dir)
    summary_rows = []
    if not summary_only:
        out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        row_for_summary = {key: value for key, value in row.items() if key != "prompt"}
        if not summary_only:
            prompt_path = out_dir / f"{row['prompt_id']}.txt"
            prompt_path.write_text(str(row["prompt"]) + "\n")
            row_for_summary["prompt_file"] = str(prompt_path.relative_to(ROOT))
        summary_rows.append(row_for_summary)

    payload = {
        "num_prompts": len(summary_rows),
        "max_chars": max((int(row["chars"]) for row in summary_rows), default=0),
        "total_approx_tokens": sum(int(row["approx_tokens"]) for row in summary_rows),
        "num_with_gold_label": sum(1 for row in summary_rows if row["contains_gold_label"]),
        "num_with_rtl_context": sum(1 for row in summary_rows if row["contains_rtl_context"]),
        "num_with_jasper_evidence": sum(1 for row in summary_rows if row["contains_jasper_evidence"]),
        "prompts": summary_rows,
    }
    print(json.dumps(payload, indent=2))
    if not summary_only:
        (out_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["all", *TASKS], default="all")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--repair-cases", type=Path, default=Path("benchmarks/sva_repair_cases.json"))
    parser.add_argument(
        "--cases",
        nargs="+",
        type=Path,
        default=[
            Path("benchmarks/arbiter_rr2/cases"),
            Path("benchmarks/rv_buffer/cases"),
            Path("benchmarks/apb_regblock/cases"),
            Path("benchmarks/fifo_1r1w/cases"),
        ],
    )
    parser.add_argument("--packet-root", type=Path, default=Path("jasper/reports/case_packets"))
    parser.add_argument("--packet-source", choices=["actual", "minimal"], default="actual")
    parser.add_argument("--redact-evidence", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation/prompt_previews"))
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    write_outputs(iter_prompts(args), args.out_dir, args.summary_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
