#!/usr/bin/env python3
"""Opt-in Codex CLI runner for JasperLoop LLM experiments.

The health check sends only a synthetic prompt. Benchmark tasks send local
evidence packets, property intents, or SVA snippets to Codex and therefore
require an explicit acknowledgement flag.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXTERNAL_SEND_WARNING = """\
This command will send local JasperLoop benchmark content to Codex/OpenAI:
- SVA repair: broken assertions, allowed signals, and property intents.
- Triage: evidence packets, JasperGold summaries, RTL excerpts, and manifests.
- Coverage: coverage goals, reachability context, and directed sequences.

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
    completed = subprocess.run(cmd, input=prompt, text=True, cwd=ROOT, check=False)
    return completed.returncode


def run_eval_task(args: argparse.Namespace) -> int:
    if args.task == "sva_repair":
        schema = ROOT / "copilot" / "schemas" / "sva_repair_candidate.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_sva_repair_eval.py"),
            "--llm",
            "--limit",
            str(args.limit),
            "--prompt-version",
            args.prompt_version,
        ]
        default_out = ROOT / "evaluation" / "results" / "sva_repair_codex_subset.json"
    elif args.task == "triage":
        schema = ROOT / "copilot" / "schemas" / "diagnosis_output.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_agent_eval.py"),
            "--systems",
            "structured",
            "--llm",
            "--limit",
            str(args.limit),
            "--packet-source",
            args.packet_source,
        ]
        default_out = ROOT / "evaluation" / "results" / "agent_eval_codex_subset.json"
    elif args.task == "coverage":
        schema = ROOT / "copilot" / "schemas" / "coverage_closure_output.schema.json"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "run_coverage_eval.py"),
            "--systems",
            "structured",
            "--llm",
            "--limit",
            str(args.limit),
            "--packet-source",
            args.packet_source,
        ]
        default_out = ROOT / "evaluation" / "results" / "coverage_eval_codex_subset.json"
    else:
        raise ValueError(f"Unsupported task: {args.task}")

    out_path = Path(args.out) if args.out else default_out
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
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["healthcheck", "sva_repair", "triage", "coverage"], default="healthcheck")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--model")
    parser.add_argument("--out")
    parser.add_argument("--prompt-version", choices=["baseline", "cex_aware"], default="baseline")
    parser.add_argument("--packet-source", choices=["minimal", "actual"], default="minimal")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--acknowledge-external-send", action="store_true")
    args = parser.parse_args()

    if args.task == "healthcheck":
        return run_healthcheck(args)
    return run_eval_task(args)


if __name__ == "__main__":
    raise SystemExit(main())
