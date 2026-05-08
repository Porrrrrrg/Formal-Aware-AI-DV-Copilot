#!/usr/bin/env python3
"""Convenience entry point for scaffold checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    commands = [
        [sys.executable, "evaluation/run_eval.py", "--cases", "benchmarks/arbiter_rr2/cases"],
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
