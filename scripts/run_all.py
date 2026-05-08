#!/usr/bin/env python3
"""Convenience entry point for scaffold checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    commands = [
        [
            sys.executable,
            "evaluation/run_eval.py",
            "--cases",
            "benchmarks/arbiter_rr2/cases",
            "benchmarks/rv_buffer/cases",
            "benchmarks/apb_regblock/cases",
        ],
        [sys.executable, "scripts/build_all_evidence_packets.py"],
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
