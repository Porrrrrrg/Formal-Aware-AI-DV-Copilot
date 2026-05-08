#!/usr/bin/env python3
"""Build evidence packets for all labeled benchmark cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_evidence_packet import build_packet  # noqa: E402


def iter_case_files(case_roots: list[Path]) -> list[Path]:
    case_files: list[Path] = []
    for root in case_roots:
        root = resolve_repo_path(root)
        if root.is_file() and root.suffix == ".json":
            case_files.append(root)
        elif root.is_dir():
            case_files.extend(sorted(root.glob("*.json")))
    return sorted(case_files)


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def find_variant_rtl(design: str, variant: str | None) -> list[Path]:
    if not variant:
        return []
    rtl_dir = ROOT / "benchmarks" / design / "rtl"
    candidates = [
        rtl_dir / f"{design}_{variant}.sv",
        rtl_dir / f"{variant}.sv",
    ]
    if variant == "correct":
        candidates.append(rtl_dir / f"{design}_correct.sv")
    for candidate in candidates:
        if candidate.exists():
            return [candidate]
    matches = sorted(rtl_dir.glob(f"*{variant}*.sv"))
    return matches[:1]


def find_report_and_trace_dir(design: str, variant: str | None) -> tuple[Path | None, Path | None]:
    if not variant:
        return None, None
    report_root = ROOT / "jasper" / "reports"
    candidates = [
        (report_root / f"{design}_{variant}_prove" / "properties.rpt"),
        (report_root / f"{design}_{variant}_cover" / "cover.rpt"),
        (report_root / f"{design}_{variant}_vacuity" / "vacuity.rpt"),
    ]
    for report in candidates:
        if report.exists():
            trace_dir = report.parent / "traces"
            return report, trace_dir if trace_dir.exists() else None
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("--out-dir", type=Path, default=Path("jasper/reports/case_packets"))
    parser.add_argument("--strict-reports", action="store_true")
    args = parser.parse_args()

    out_dir = resolve_repo_path(args.out_dir)
    rows = []
    for case_path in iter_case_files(args.cases):
        case = json.loads(case_path.read_text())
        design = str(case["design_id"])
        variant = case.get("variant")
        variant_str = str(variant) if variant else None
        report, trace_dir = find_report_and_trace_dir(design, variant_str)
        if args.strict_reports and report is None:
            raise FileNotFoundError(f"Missing Jasper report for {case_path}")

        packet = build_packet(
            case_path=case_path,
            report_path=report,
            trace_dir=trace_dir,
            rtl_paths=find_variant_rtl(design, variant_str),
        )
        packet_path = out_dir / design / str(case["case_id"]) / "evidence_packet.json"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(json.dumps(packet, indent=2) + "\n")
        rows.append(
            {
                "case_id": case["case_id"],
                "design_id": design,
                "variant": variant,
                "report_found": report is not None,
                "trace_dir_found": trace_dir is not None,
                "packet": str(packet_path.relative_to(ROOT)),
            }
        )

    summary = {
        "num_cases": len(rows),
        "num_with_reports": sum(1 for row in rows if row["report_found"]),
        "num_with_trace_dirs": sum(1 for row in rows if row["trace_dir_found"]),
        "packets": rows,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
