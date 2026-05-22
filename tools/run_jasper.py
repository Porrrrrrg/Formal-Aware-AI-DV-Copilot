#!/usr/bin/env python3
"""Run JasperGold for a benchmark variant.

This wrapper stages a benchmark-specific run into `jasper/reports/<case>/` and
invokes the benchmark TCL script. It is intentionally thin because JasperGold
command-line details can vary by installation.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_variant_rtl(design_dir: Path, variant: str) -> Path:
    rtl_dir = design_dir / "rtl"
    candidates = [
        rtl_dir / f"{design_dir.name}_{variant}.sv",
        rtl_dir / f"{variant}.sv",
        rtl_dir / f"{design_dir.name}_correct.sv" if variant == "correct" else rtl_dir / "",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(rtl_dir.glob(f"*{variant}*.sv"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No RTL variant found for design={design_dir.name} variant={variant}")


def run_jasper(design: str, variant: str, mode: str, dry_run: bool = False) -> Path:
    design_dir = ROOT / "benchmarks" / design
    if not design_dir.exists():
        raise FileNotFoundError(f"Unknown design: {design}")

    run_tcl = design_dir / "formal" / "run_jg.tcl"
    if not run_tcl.exists():
        raise FileNotFoundError(f"Missing TCL script: {run_tcl}")

    rtl_file = find_variant_rtl(design_dir, variant)
    report_dir = ROOT / "jasper" / "reports" / f"{design}_{variant}_{mode}"
    report_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["JASPERLOOP_ROOT"] = str(ROOT)
    env["JASPERLOOP_DESIGN"] = design
    env["JASPERLOOP_VARIANT"] = variant
    env["JASPERLOOP_MODE"] = mode
    env["JASPERLOOP_RTL"] = str(rtl_file)
    env["JASPERLOOP_REPORT_DIR"] = str(report_dir)

    jasper_bin = env.get("JASPER_BIN", "jg")
    project_dir = report_dir / "jgproject"
    cmd = [
        jasper_bin,
        "-batch",
        "-allow_unsupported_OS",
        "-proj",
        str(project_dir),
        "-tcl",
        str(run_tcl),
    ]
    (report_dir / "run_command.txt").write_text(" ".join(cmd) + "\n")

    if dry_run:
        return report_dir

    if shutil.which(jasper_bin) is None:
        raise RuntimeError(
            f"Cannot find JasperGold executable '{jasper_bin}'. "
            "Set JASPER_BIN or source the Cadence environment for this host."
        )

    with (report_dir / "jg.log").open("w") as log:
        subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    return report_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True)
    parser.add_argument("--variant", default="correct")
    parser.add_argument("--mode", choices=["prove", "cover", "vacuity"], default="prove")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report_dir = run_jasper(args.design, args.variant, args.mode, args.dry_run)
    print(report_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
