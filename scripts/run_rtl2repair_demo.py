#!/usr/bin/env python3
"""Run the local RTL2Repair dry-run demo."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "evaluation" / "run_rtl2repair_eval.py"),
        "--rtl",
        str(ROOT / "benchmarks" / "arbiter_rr2" / "rtl" / "arbiter_rr2_correct.sv"),
        "--top",
        "arbiter_rr2",
        "--clock",
        "clk",
        "--reset",
        "rst",
        "--reset-polarity",
        "active_high",
        "--intent",
        "The arbiter must never grant both clients in the same cycle.",
        "--k",
        "2",
        "--max-sva-rounds",
        "1",
        "--max-rtl-rounds",
        "0",
        "--dry-run",
        "--out",
        str(ROOT / "artifacts" / "rtl2repair" / "arbiter_dry_run" / "rtl2repair_eval.json"),
    ]
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
