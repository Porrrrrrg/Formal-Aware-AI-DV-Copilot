#!/usr/bin/env python3
"""Prepare and run Moore JasperGold checks for restored Codex repair candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.check_generated_sva import check_generated_sva  # noqa: E402

DEFAULT_ARTIFACT = Path("reports/repair/artifacts/codex_repair_outputs_20260511T035613Z.jsonl")
DEFAULT_EXPECTED_SHA256 = "DB469CDAAAECF06953260CFFB1BD6EAA24A7B76E66F2CD56A4CAE44F8DBDBD9B"
DEFAULT_JASPER_OUT_ROOT = Path("jasper/reports/codex_repair_final_proof")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        rows.append(row)
    return rows


def normalized_sha256(path: Path) -> str:
    """Return a platform-stable hash for the JSONL artifact.

    The committed artifact hash was computed with LF line endings. Windows checkouts may
    materialize CRLF, so normalize newlines before hashing.
    """

    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest().upper()


def require_artifact_hash(path: Path, expected: str | None) -> str:
    actual = normalized_sha256(path)
    if expected and actual.upper() != expected.upper():
        raise RuntimeError(f"{path} SHA256 mismatch: expected {expected.upper()}, got {actual}")
    return actual


def candidate_id(row: dict[str, Any], index: int) -> str:
    case_id = str(row.get("case_id") or f"row_{index:03d}")
    attempt = row.get("attempt_index")
    if isinstance(attempt, int):
        return f"{case_id}__attempt_{attempt:02d}"
    return f"{case_id}__row_{index:03d}"


def make_case_and_prediction(row: dict[str, Any], index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    for key in ("case_id", "design", "property_id", "codex_repaired_sva"):
        if not row.get(key):
            raise ValueError(f"JSONL row {index} is missing required field {key!r}")

    case = {
        "case_id": candidate_id(row, index),
        "design_id": row["design"],
        "property_id": row["property_id"],
    }
    prediction = {
        "property_id": row["property_id"],
        "sva": row["codex_repaired_sva"],
        "source": row.get("source", "llm"),
        "source_run_id": row.get("source_run_id"),
        "attempt_index": row.get("attempt_index"),
    }
    return case, prediction


def summarize_candidate(
    row: dict[str, Any],
    check: dict[str, Any],
    index: int,
    dry_run: bool,
) -> dict[str, Any]:
    status = "pending_moore_execution" if dry_run else "jasper_checked"
    if not dry_run and check.get("syntax_pass") is False:
        status = "jasper_syntax_failed"
    return {
        "candidate_id": candidate_id(row, index),
        "case_id": row.get("case_id"),
        "design": row.get("design"),
        "property_id": row.get("property_id"),
        "attempt_index": row.get("attempt_index"),
        "candidate_status_from_restore": row.get("candidate_status"),
        "scaffold_success_from_restore": row.get("scaffold_success"),
        "exact_match_from_restore": row.get("exact_match"),
        "has_hallucinated_signal_from_restore": row.get("has_hallucinated_signal"),
        "status": status,
        "jasper_syntax_pass": check.get("syntax_pass"),
        "jasper_proof_status": check.get("proof_status"),
        "jasper_vacuity_status": check.get("vacuity_status"),
        "jasper_returncode": check.get("jasper_returncode"),
        "report_dir": repo_relative(check.get("report_dir")),
        "properties_report": repo_relative(check.get("properties_report")),
        "vacuity_report": repo_relative(check.get("vacuity_report")),
    }


def repo_relative(value: object) -> str | None:
    if value is None:
        return None
    path = Path(str(value))
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(value)


def ensure_moore_ready(jasper_bin: str | None) -> None:
    host = platform.node().lower()
    if "moore" not in host:
        raise RuntimeError(
            f"Refusing to run JasperGold on non-Moore host {platform.node()!r}. "
            "Run this command on moore.wot.ece.northwestern.edu."
        )
    if not jasper_bin:
        raise RuntimeError(
            "JASPER_BIN is not set. Source the Cadence environment and set JASPER_BIN "
            "before running final proof."
        )
    if shutil.which(jasper_bin) is None:
        raise RuntimeError(
            f"Cannot execute JASPER_BIN={jasper_bin!r}. Source cadence.env and verify "
            "the JasperGold path before running final proof."
        )


def build_manifest(
    rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    artifact_path: Path,
    artifact_sha256: str,
    dry_run: bool,
    jasper_out_root: Path,
) -> dict[str, Any]:
    cases = sorted({str(row.get("case_id")) for row in rows if row.get("case_id")})
    checked = not dry_run
    return {
        "run_id": "codex_repair_final_proof_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "host": platform.node(),
        "artifact": {
            "path": artifact_path.as_posix(),
            "sha256_lf_normalized": artifact_sha256,
            "rows": len(rows),
            "case_count": len(cases),
        },
        "jasper": {
            "checked": checked,
            "dry_run": dry_run,
            "jasper_bin": os.environ.get("JASPER_BIN"),
            "out_root": jasper_out_root.as_posix(),
            "raw_artifact_policy": (
                "Raw Jasper logs, traces, jgproject directories, and generated report files "
                "remain under ignored jasper/reports/ paths and are not committed."
            ),
        },
        "summary": {
            "candidate_count": len(candidate_rows),
            "case_count": len(cases),
            "pending_moore_cases": 0 if checked else len(cases),
            "pending_moore_candidates": 0 if checked else len(candidate_rows),
            "jasper_syntax_pass_count": count_value(candidate_rows, "jasper_syntax_pass", True),
            "jasper_syntax_fail_count": count_value(candidate_rows, "jasper_syntax_pass", False),
            "jasper_proven_count": count_value(candidate_rows, "jasper_proof_status", "proven"),
            "jasper_vacuous_count": count_value(candidate_rows, "jasper_vacuity_status", "vacuous"),
        },
        "cases": cases,
        "candidates": candidate_rows,
    }


def count_value(rows: list[dict[str, Any]], key: str, value: object) -> int:
    return sum(1 for row in rows if row.get(key) == value)


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Consume restored Codex SVA repair JSONL and prepare/run final JasperGold "
            "syntax/proof/vacuity checks."
        )
    )
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--expected-sha256", default=DEFAULT_EXPECTED_SHA256)
    parser.add_argument("--no-hash-check", action="store_true")
    parser.add_argument("--jasper-check", action="store_true", help="Run JasperGold; requires Moore.")
    parser.add_argument("--dry-run", action="store_true", help="Render harnesses without JasperGold.")
    parser.add_argument("--out-root", type=Path, default=DEFAULT_JASPER_OUT_ROOT)
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=Path("reports/jasper/codex_repair_final_proof_manifest.json"),
    )
    args = parser.parse_args()

    if args.jasper_check == args.dry_run:
        parser.error("choose exactly one of --jasper-check or --dry-run")

    artifact_path = resolve_repo_path(args.artifact)
    jasper_out_root = resolve_repo_path(args.out_root)
    manifest_out = resolve_repo_path(args.manifest_out)

    expected = None if args.no_hash_check else args.expected_sha256
    artifact_sha256 = require_artifact_hash(artifact_path, expected)
    rows = load_jsonl(artifact_path)

    if args.jasper_check:
        ensure_moore_ready(os.environ.get("JASPER_BIN"))

    candidate_rows = []
    for index, row in enumerate(rows, start=1):
        case, prediction = make_case_and_prediction(row, index)
        check = check_generated_sva(
            case=case,
            prediction=prediction,
            system="codex_repair_final_proof",
            out_root=jasper_out_root,
            dry_run=args.dry_run,
        )
        candidate_rows.append(summarize_candidate(row, check, index, dry_run=args.dry_run))

    manifest = build_manifest(
        rows=rows,
        candidate_rows=candidate_rows,
        artifact_path=args.artifact,
        artifact_sha256=artifact_sha256,
        dry_run=args.dry_run,
        jasper_out_root=args.out_root,
    )
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2))
    print(f"Wrote manifest: {manifest_out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
