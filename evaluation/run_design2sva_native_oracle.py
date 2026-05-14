#!/usr/bin/env python3
"""Run Design2SVA fixture properties through native benchmark Jasper flows.

This oracle maps each Design2SVA fixture to the benchmark's checked-in RTL,
assumptions, property module, harness, and ``formal/run_jg.tcl`` script. It
does not embed generated candidate SVA.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.run_jasper import run_jasper as legacy_run_jasper  # noqa: E402

DEFAULT_CASES = Path("benchmarks/design2sva_cases.json")
DEFAULT_OUT = Path("evaluation/results/design2sva_native_reference_oracle_jasper.json")

TOP_RE = re.compile(r"^\s*elaborate\s+-top\s+(?P<top>[A-Za-z_][A-Za-z0-9_$]*)\b", re.MULTILINE)
PROPERTY_INSTANCE_TEMPLATE = (
    r"\b{module}\b(?:\s*#\s*\([^;]*?\))?\s+"
    r"(?P<instance>[A-Za-z_][A-Za-z0-9_$]*)\s*\("
)


@dataclass(frozen=True)
class NativeMapping:
    case_id: str
    design_id: str
    property_id: str
    design_rtl: Path
    formal_harness: Path
    properties: Path
    assumptions: Path
    run_jg_tcl: Path
    top_harness: str
    property_instance: str

    @property
    def native_property_path(self) -> str:
        return f"{self.top_harness}.{self.property_instance}.{self.property_id}"


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def repo_relative(path: Path | str | None) -> str | None:
    if path is None:
        return None
    resolved = resolve_repo_path(Path(path)).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(resolve_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    cases: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path} entry {index} is not an object")
        for key in ("case_id", "design_id", "property_id"):
            if not item.get(key):
                raise ValueError(f"{path} entry {index} is missing {key}")
        cases.append(item)
    return cases


def map_case_to_native_flow(case: dict[str, Any]) -> NativeMapping:
    design_id = str(case["design_id"])
    property_id = str(case["property_id"])
    case_id = str(case["case_id"])
    benchmark_dir = ROOT / "benchmarks" / design_id
    formal_dir = benchmark_dir / "formal"
    mapping = NativeMapping(
        case_id=case_id,
        design_id=design_id,
        property_id=property_id,
        design_rtl=benchmark_dir / "rtl" / f"{design_id}_correct.sv",
        formal_harness=formal_dir / f"{design_id}_harness.sv",
        properties=formal_dir / f"{design_id}_properties.sv",
        assumptions=formal_dir / f"{design_id}_assumptions.sv",
        run_jg_tcl=formal_dir / "run_jg.tcl",
        top_harness=parse_top_harness(formal_dir / "run_jg.tcl"),
        property_instance=parse_property_instance(
            formal_dir / f"{design_id}_harness.sv",
            design_id,
        ),
    )
    validate_mapping_files(mapping)
    validate_property_label(mapping)
    validate_fixture_rtl(case, mapping)
    return mapping


def parse_top_harness(run_jg_tcl: Path) -> str:
    text = run_jg_tcl.read_text(encoding="utf-8")
    match = TOP_RE.search(text)
    if not match:
        raise ValueError(f"Could not find 'elaborate -top' in {repo_relative(run_jg_tcl)}")
    return match.group("top")


def parse_property_instance(harness_path: Path, design_id: str) -> str:
    text = harness_path.read_text(encoding="utf-8")
    module_name = re.escape(f"{design_id}_properties")
    pattern = re.compile(PROPERTY_INSTANCE_TEMPLATE.format(module=module_name), re.DOTALL)
    match = pattern.search(text)
    if not match:
        raise ValueError(
            f"Could not find native properties instance in {repo_relative(harness_path)}"
        )
    return match.group("instance")


def validate_mapping_files(mapping: NativeMapping) -> None:
    missing = [
        path
        for path in (
            mapping.design_rtl,
            mapping.formal_harness,
            mapping.properties,
            mapping.assumptions,
            mapping.run_jg_tcl,
        )
        if not path.exists()
    ]
    if missing:
        joined = ", ".join(str(repo_relative(path)) for path in missing)
        raise FileNotFoundError(f"Missing native benchmark path(s): {joined}")


def validate_property_label(mapping: NativeMapping) -> None:
    text = mapping.properties.read_text(encoding="utf-8")
    property_re = re.compile(
        rf"^\s*{re.escape(mapping.property_id)}\s*:\s*assert\s+property\b",
        re.MULTILINE,
    )
    if not property_re.search(text):
        raise ValueError(
            f"{mapping.case_id} property {mapping.property_id!r} is not an assert label in "
            f"{repo_relative(mapping.properties)}"
        )


def validate_fixture_rtl(case: dict[str, Any], mapping: NativeMapping) -> None:
    fixture_rtl = case.get("design_rtl_path")
    if not fixture_rtl:
        return
    if resolve_repo_path(Path(str(fixture_rtl))).resolve() != mapping.design_rtl.resolve():
        raise ValueError(
            f"{mapping.case_id} fixture RTL {fixture_rtl!r} does not match native RTL "
            f"{repo_relative(mapping.design_rtl)}"
        )


def mapping_paths(mapping: NativeMapping) -> dict[str, str]:
    return {
        "design_rtl": str(repo_relative(mapping.design_rtl)),
        "formal_harness": str(repo_relative(mapping.formal_harness)),
        "properties": str(repo_relative(mapping.properties)),
        "assumptions": str(repo_relative(mapping.assumptions)),
        "run_jg_tcl": str(repo_relative(mapping.run_jg_tcl)),
    }


def expected_report_dir(design_id: str, variant: str, mode: str) -> Path:
    return ROOT / "jasper" / "reports" / f"{design_id}_{variant}_{mode}"


def dry_run_result(mapping: NativeMapping, variant: str) -> dict[str, Any]:
    proof_dir = expected_report_dir(mapping.design_id, variant, "prove")
    vacuity_dir = expected_report_dir(mapping.design_id, variant, "vacuity")
    return base_result(mapping, variant) | {
        "native_proof_status": "not_run",
        "native_vacuity_status": "not_run",
        "native_report_dir": repo_relative(proof_dir),
        "native_report_dirs": {
            "prove": repo_relative(proof_dir),
            "vacuity": repo_relative(vacuity_dir),
        },
        "native_reference_proves": None,
        "root_cause_candidate": "unknown",
        "backend_status": "dry_run",
        "backend_feedback": "Dry run only; JasperGold was not invoked.",
    }


def base_result(mapping: NativeMapping, variant: str) -> dict[str, Any]:
    return {
        "case_id": mapping.case_id,
        "design_id": mapping.design_id,
        "property_id": mapping.property_id,
        "variant": variant,
        "mapping_status": "mapped",
        "native_paths": mapping_paths(mapping),
        "native_top_harness": mapping.top_harness,
        "native_property_id": mapping.property_id,
        "native_property_path": mapping.native_property_path,
        "candidate_embedding": False,
    }


def blocked_result(
    case: dict[str, Any],
    variant: str,
    message: str,
    mapping: NativeMapping | None = None,
) -> dict[str, Any]:
    design_id = str(case.get("design_id", "unknown_design"))
    property_id = str(case.get("property_id", "unknown_property"))
    proof_dir = expected_report_dir(design_id, variant, "prove")
    base = (
        base_result(mapping, variant)
        if mapping is not None
        else {
            "case_id": str(case.get("case_id", "unknown_case")),
            "design_id": design_id,
            "property_id": property_id,
            "variant": variant,
            "mapping_status": "blocked",
            "native_paths": {},
            "native_top_harness": None,
            "native_property_id": property_id,
            "native_property_path": None,
            "candidate_embedding": False,
        }
    )
    return base | {
        "native_proof_status": "blocked",
        "native_vacuity_status": "not_run",
        "native_report_dir": repo_relative(proof_dir),
        "native_report_dirs": {"prove": repo_relative(proof_dir), "vacuity": None},
        "native_reference_proves": None,
        "root_cause_candidate": "unknown",
        "backend_status": "blocked",
        "backend_feedback": message,
    }


def run_native_case(case: dict[str, Any], variant: str, dry_run: bool) -> dict[str, Any]:
    try:
        mapping = map_case_to_native_flow(case)
    except Exception as exc:  # noqa: BLE001 - returned as structured oracle status.
        return blocked_result(case, variant, str(exc), mapping=None)

    if dry_run:
        return dry_run_result(mapping, variant)

    from copilot.backends.jasper_backend import JasperBackend

    backend = JasperBackend()
    try:
        proof_dir = legacy_run_jasper(mapping.design_id, variant, "prove", dry_run=False)
    except RuntimeError as exc:
        return blocked_result(case, variant, str(exc), mapping=mapping)
    except subprocess.CalledProcessError as exc:
        proof_dir = expected_report_dir(mapping.design_id, variant, "prove")
        parsed = backend.parse_report_dir(
            proof_dir,
            property_id=mapping.property_id,
            returncode=exc.returncode,
            dry_run=False,
        )
        return run_result_from_backend(mapping, variant, parsed, None)

    proof = backend.parse_report_dir(proof_dir, property_id=mapping.property_id, dry_run=False)

    try:
        vacuity_dir = legacy_run_jasper(mapping.design_id, variant, "vacuity", dry_run=False)
    except RuntimeError as exc:
        result = run_result_from_backend(mapping, variant, proof, None)
        result["native_vacuity_status"] = "blocked"
        result["backend_status"] = "blocked"
        result["backend_feedback"] = str(exc)
        result["root_cause_candidate"] = "unknown"
        result["native_reference_proves"] = reference_proves(result["native_proof_status"])
        return result
    except subprocess.CalledProcessError as exc:
        vacuity_dir = expected_report_dir(mapping.design_id, variant, "vacuity")
        vacuity = backend.parse_report_dir(
            vacuity_dir,
            property_id=mapping.property_id,
            returncode=exc.returncode,
            dry_run=False,
        )
    else:
        vacuity = backend.parse_report_dir(
            vacuity_dir,
            property_id=mapping.property_id,
            dry_run=False,
        )

    return run_result_from_backend(mapping, variant, proof, vacuity)


def run_result_from_backend(
    mapping: NativeMapping,
    variant: str,
    proof: Any,
    vacuity: Any | None,
) -> dict[str, Any]:
    proof_status = proof.proof_result.status.value
    vacuity_status = (
        vacuity.vacuity_result.status.value
        if vacuity is not None
        else proof.vacuity_result.status.value
    )
    report_dirs = {
        "prove": repo_relative(proof.report_dir),
        "vacuity": repo_relative(vacuity.report_dir) if vacuity is not None else None,
    }
    result = base_result(mapping, variant) | {
        "native_proof_status": proof_status,
        "native_vacuity_status": vacuity_status,
        "native_report_dir": report_dirs["prove"],
        "native_report_dirs": report_dirs,
        "native_reference_proves": reference_proves(proof_status),
        "root_cause_candidate": classify_root_cause_candidate(proof_status, vacuity_status),
        "backend_status": proof.status.value,
        "backend_feedback": proof.feedback,
        "raw_report_paths": {
            "prove": {
                key: repo_relative(path)
                for key, path in proof.raw_report_paths.items()
                if path is not None
            },
            "vacuity": {
                key: repo_relative(path)
                for key, path in vacuity.raw_report_paths.items()
                if path is not None
            }
            if vacuity is not None
            else {},
        },
    }
    return result


def reference_proves(proof_status: str) -> bool | None:
    if proof_status == "proven":
        return True
    if proof_status in {"falsified", "undetermined", "syntax_error", "error", "unreachable"}:
        return False
    return None


def classify_root_cause_candidate(proof_status: str, vacuity_status: str) -> str:
    if proof_status == "not_run" or vacuity_status == "not_run":
        return "unknown"
    if proof_status == "blocked" or vacuity_blocked(vacuity_status):
        return "unknown"
    if vacuity_status == "vacuous":
        return "native_harness_unreachable"
    if proof_status == "proven":
        return "unknown"
    if proof_status == "unreachable":
        return "native_harness_unreachable"
    if proof_status in {"falsified", "syntax_error", "error"}:
        return "reference_task_invalid"
    return "unknown"


def vacuity_blocked(vacuity_status: str) -> bool:
    return vacuity_status == "blocked"


def build_payload(
    cases: list[dict[str, Any]],
    cases_path: Path,
    variant: str,
    dry_run: bool,
) -> dict[str, Any]:
    results = [run_native_case(case, variant=variant, dry_run=dry_run) for case in cases]
    return {
        "schema_version": "v1",
        "mode": "native_reference_oracle",
        "backend": "jaspergold",
        "dry_run": dry_run,
        "variant": variant,
        "cases_path": repo_relative(cases_path),
        "summary": summarize_results(results, dry_run=dry_run),
        "results": results,
    }


def summarize_results(results: list[dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    proof_counts = collections.Counter(str(row.get("native_proof_status")) for row in results)
    vacuity_counts = collections.Counter(str(row.get("native_vacuity_status")) for row in results)
    root_counts = collections.Counter(str(row.get("root_cause_candidate")) for row in results)
    mapped = sum(1 for row in results if row.get("mapping_status") == "mapped")
    proves = sum(1 for row in results if row.get("native_reference_proves") is True)
    disproves = sum(1 for row in results if row.get("native_reference_proves") is False)
    unknown = sum(1 for row in results if row.get("native_reference_proves") is None)
    return {
        "num_cases": len(results),
        "dry_run": dry_run,
        "mapped_cases": mapped,
        "all_cases_mapped": mapped == len(results),
        "candidate_embedding": False,
        "native_reference_proves_count": proves,
        "native_reference_does_not_prove_count": disproves,
        "native_reference_unknown_count": unknown,
        "native_proof_status_counts": dict(sorted(proof_counts.items())),
        "native_vacuity_status_counts": dict(sorted(vacuity_counts.items())),
        "root_cause_candidate_counts": dict(sorted(root_counts.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--variant", default="correct")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    payload = build_payload(
        cases,
        cases_path=args.cases,
        variant=args.variant,
        dry_run=args.dry_run,
    )
    out = resolve_repo_path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
