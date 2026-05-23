#!/usr/bin/env python3
"""Opt-in Codex CLI runner for JasperLoop LLM experiments.

The health check sends only a synthetic prompt. Benchmark tasks send local
evidence packets, property intents, or SVA snippets to Codex and therefore
require an explicit acknowledgement flag.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.agents.sva_repair_agent import PROMPT_VERSIONS  # noqa: E402

EXTERNAL_SEND_WARNING = """\
This command will send local JasperLoop benchmark content to Codex/OpenAI:
- SVA repair: broken assertions, allowed signals, and property intents.
- Triage: evidence packets, JasperGold summaries, RTL excerpts, and manifests.
- Coverage: coverage goals, reachability context, and directed sequences.
- Design2SVA: natural-language property intents, visible signals, and bounded
  RTL/harness retrieval context.

Rerun with --acknowledge-external-send if you approve that data export.
"""


def build_adapter_command(schema: Path, timeout: int, model: str | None) -> str:
    cmd = [
        sys.executable,
        str(ROOT / "copilot" / "llm_adapters" / "codex_json.py"),
        "--schema",
        str(schema),
        "--cd",
        str(ROOT),
        "--timeout",
        str(timeout),
    ]
    if model:
        cmd.extend(["--model", model])
    return subprocess.list2cmdline(cmd)


def run_healthcheck(args: argparse.Namespace) -> int:
    prompt = (
        "Return JSON for an SVA repair candidate with property_id p_mutex, "
        "sva 'p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));', "
        "and a short explanation."
    )
    cmd = [
        sys.executable,
        str(ROOT / "copilot" / "llm_adapters" / "codex_json.py"),
        "--schema",
        str(ROOT / "copilot" / "schemas" / "sva_repair_candidate.schema.json"),
        "--cd",
        str(ROOT),
        "--timeout",
        str(args.timeout),
    ]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.dry_run:
        print(subprocess.list2cmdline(cmd))
        print(prompt)
        return 0
    completed = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        sys.stderr.write(completed.stderr)
    print(json.dumps({"codex_healthcheck_summary": healthcheck_summary(completed)}, indent=2))
    return completed.returncode


def run_eval_task(args: argparse.Namespace) -> int:
    if args.task == "sva_repair":
        schema = ROOT / "copilot" / "schemas" / "sva_repair_candidate.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_sva_repair_eval.py"),
            "--llm",
            "--prompt-version",
            args.prompt_version,
        ]
        subset_out = ROOT / "evaluation" / "results" / "sva_repair_codex_subset.json"
        full_out = ROOT / "evaluation" / "results" / "sva_repair_codex_full.json"
    elif args.task == "triage":
        schema = ROOT / "copilot" / "schemas" / "diagnosis_output.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_agent_eval.py"),
            "--systems",
            "structured",
            "--llm",
            "--packet-source",
            args.packet_source,
        ]
        subset_out = ROOT / "evaluation" / "results" / "agent_eval_codex_subset.json"
        full_out = ROOT / "evaluation" / "results" / "agent_eval_codex_full.json"
    elif args.task == "coverage":
        schema = ROOT / "copilot" / "schemas" / "coverage_closure_output.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_coverage_eval.py"),
            "--systems",
            "structured",
            "--llm",
            "--packet-source",
            args.packet_source,
        ]
        subset_out = ROOT / "evaluation" / "results" / "coverage_eval_codex_subset.json"
        full_out = ROOT / "evaluation" / "results" / "coverage_eval_codex_full.json"
    elif args.task == "design2sva":
        schema = ROOT / "copilot" / "schemas" / "design2sva_candidate.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_design2sva_eval.py"),
            "--llm",
            "--k",
            str(args.k),
            "--max-repair-rounds",
            str(args.max_repair_rounds),
            "--context-budget",
            str(args.context_budget),
        ]
        if args.cases:
            cmd.extend(["--cases", args.cases])
        markdown_path = (
            ROOT / "evaluation" / "results" / "design2sva_eval_codex_expanded_subset.md"
        )
        if args.markdown:
            markdown_path = ROOT / args.markdown
        cmd.extend(["--markdown", str(markdown_path)])
        subset_out = (
            ROOT / "evaluation" / "results" / "design2sva_eval_codex_expanded_subset.json"
        )
        full_out = subset_out
    else:
        raise ValueError(f"Unsupported task: {args.task}")

    default_out = subset_out if args.limit is not None else full_out
    out_path = Path(args.out) if args.out else default_out
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])
    cmd.extend(["--out", str(out_path)])

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["JASPERLOOP_LLM_CMD"] = build_adapter_command(schema, args.timeout, args.model)
    if args.dry_run:
        print("JASPERLOOP_LLM_CMD=" + env["JASPERLOOP_LLM_CMD"])
        print(subprocess.list2cmdline(cmd))
        return 0
    if not args.acknowledge_external_send:
        sys.stderr.write(EXTERNAL_SEND_WARNING)
        return 2
    if args.task == "design2sva" and not prompt_audit_exists(args.prompt_audit):
        sys.stderr.write(
            "Design2SVA external runs require a generated prompt audit. "
            f"Missing: {args.prompt_audit}\n"
        )
        return 2
    completed = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    if completed.returncode == 0:
        print_codex_eval_summary(out_path, args.task)
    return completed.returncode


def healthcheck_summary(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    valid_json = False
    if completed.returncode == 0 and completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
            valid_json = isinstance(parsed, dict)
        except json.JSONDecodeError:
            valid_json = False
    return {
        "task": "healthcheck",
        "llm_attempted_count": 1,
        "valid_json_count": 1 if valid_json else 0,
        "valid_json_rate": 1.0 if valid_json else 0.0,
        "fallback_rate": 0.0,
        "hallucinated_signal_rate": 0.0,
        "source_counts": {"llm": 1} if valid_json else {"llm_error": 1},
        "deterministic_scaffold_count": 0,
        "real_llm_count": 1 if valid_json else 0,
        "returncode": completed.returncode,
    }


READINESS_KEYS = (
    "num_outputs",
    "llm_attempted_count",
    "valid_json_count",
    "valid_json_rate",
    "fallback_rate",
    "hallucinated_signal_rate",
    "hallucinated_signal_checked_count",
    "source_counts",
    "syntax@1",
    "syntax@k",
    "proven@1",
    "proven@k",
    "proven_non_vacuous@k",
    "candidate_count_by_case",
    "output_family_counts",
    "deterministic_scaffold_count",
    "deterministic_scaffold_rate",
    "real_llm_count",
    "real_llm_rate",
    "llm_error_count",
    "llm_error_rate",
)


def print_codex_eval_summary(out_path: Path, task: str) -> None:
    summary = load_codex_eval_summary(out_path, task)
    print(json.dumps({"codex_eval_readiness_summary": summary}, indent=2))


def load_codex_eval_summary(out_path: Path, task: str) -> dict[str, object]:
    if not out_path.exists():
        return {"task": task, "result_file": display_path(out_path), "error": "result file not found"}
    payload = json.loads(out_path.read_text())
    result_file = display_path(out_path)
    if task in {"sva_repair", "design2sva"}:
        return {
            "task": task,
            "result_file": result_file,
            "metrics": metric_subset(payload.get("summary", {})),
        }
    systems = payload.get("systems", {})
    if isinstance(systems, dict):
        return {
            "task": task,
            "result_file": result_file,
            "systems": {
                str(system): metric_subset(summary)
                for system, summary in systems.items()
                if isinstance(summary, dict)
            },
        }
    return {"task": task, "result_file": result_file, "error": "unrecognized result payload"}


def metric_subset(summary: dict[str, object]) -> dict[str, object]:
    metrics = {key: summary[key] for key in READINESS_KEYS if key in summary}
    metrics.setdefault("hallucinated_signal_rate", None)
    return metrics


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def prompt_audit_exists(path_text: str | None) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return path.exists()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task",
        choices=["healthcheck", "sva_repair", "triage", "coverage", "design2sva"],
        default="healthcheck",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--model")
    parser.add_argument("--out")
    parser.add_argument("--markdown")
    parser.add_argument("--cases")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--max-repair-rounds", type=int, default=0)
    parser.add_argument("--context-budget", type=int, default=24)
    parser.add_argument(
        "--prompt-audit",
        default="evaluation/prompt_previews/design2sva_expanded_prompt_audit.md",
    )
    parser.add_argument("--prompt-version", choices=PROMPT_VERSIONS, default="baseline")
    parser.add_argument("--packet-source", choices=["minimal", "actual"], default="minimal")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--acknowledge-external-send", action="store_true")
    args = parser.parse_args()

    if args.task == "healthcheck":
        return run_healthcheck(args)
    return run_eval_task(args)


if __name__ == "__main__":
    raise SystemExit(main())
