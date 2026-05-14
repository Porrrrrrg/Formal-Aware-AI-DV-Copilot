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
DEFAULT_EXPANDED_LOCAL_OUT = Path(
    "evaluation/results/design2sva_reference_oracle_expanded_local.json"
)
DEFAULT_EXPANDED_JASPER_OUT = Path(
    "evaluation/results/design2sva_reference_oracle_expanded_jasper.json"
)
DEFAULT_REFERENCE_ORACLE_REPLAY = Path(
    "evaluation/fixtures/design2sva_reference_oracle_replay.jsonl"
)
DEFAULT_WRAPPER_OUT_ROOT = Path("jasper/reports/design2sva_reference_oracle_expanded")
NATIVE_REFERENCE_MODE = "native_reference_oracle"
EXPANDED_REFERENCE_MODE = "design2sva_reference_oracle_expanded"
EXPANDED_REFERENCE_MODE_ALIASES = {
    "expanded",
    "reference-oracle-expanded",
    "reference_oracle_expanded",
    "design2sva-reference-oracle-expanded",
    EXPANDED_REFERENCE_MODE,
}
NATIVE_REFERENCE_MODE_ALIASES = {
    "native-reference-oracle",
    "native_reference_oracle",
    NATIVE_REFERENCE_MODE,
}

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
        "root_cause_summary": "Dry run only; native benchmark proof was not executed.",
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
        "root_cause_summary": message,
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
        "root_cause_summary": summarize_native_root_cause(proof_status, vacuity_status),
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


def summarize_native_root_cause(proof_status: str, vacuity_status: str) -> str:
    label = classify_root_cause_candidate(proof_status, vacuity_status)
    if label == "native_harness_unreachable":
        return "Native benchmark harness or reference antecedent was unreachable."
    if label == "reference_task_invalid":
        return "Native benchmark proof indicates the checked-in reference property is invalid."
    if proof_status == "proven" and not vacuity_blocked(vacuity_status):
        return "Native benchmark reference property proved without a fixture-level failure."
    if proof_status == "not_run" or vacuity_status == "not_run":
        return "Native benchmark proof was not run."
    if proof_status == "blocked" or vacuity_blocked(vacuity_status):
        return "Native benchmark validation was blocked before proof classification."
    return f"Native benchmark proof={proof_status}, vacuity={vacuity_status}."


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


def build_expanded_reference_oracle_payload(
    cases: list[dict[str, Any]],
    cases_path: Path,
    variant: str,
    dry_run: bool,
    jasper_check: bool = False,
    jasper_replay_path: Path | None = None,
    native_oracle_results_path: Path | None = None,
    jasper_out_root: Path = DEFAULT_WRAPPER_OUT_ROOT,
    context_budget: int = 24,
    run_harness_diagnostics: bool = False,
) -> dict[str, Any]:
    """Validate expanded Design2SVA reference-oracle fixtures without LLM calls."""

    from copilot.agents.design2sva_agent import load_replay_records  # noqa: E402
    from evaluation.run_design2sva_eval import (  # noqa: E402
        run_case as run_design2sva_wrapper_case,
        summarize as summarize_design2sva_wrapper,
    )

    wrapper_replay_records = (
        load_replay_records(resolve_repo_path(jasper_replay_path))
        if jasper_replay_path is not None
        else None
    )
    effective_dry_run = bool(dry_run or (not jasper_check and wrapper_replay_records is None))
    wrapper_dry_run = bool(effective_dry_run and wrapper_replay_records is None)
    wrapper_jasper_check = bool(jasper_check or wrapper_dry_run or wrapper_replay_records)
    native_dry_run = bool(effective_dry_run or wrapper_replay_records is not None)
    native_results_path = resolved_native_oracle_results_path(
        native_oracle_results_path,
        use_replay=wrapper_replay_records is not None,
    )
    loaded_native_results = load_native_oracle_index(native_results_path)
    formal_mode = expanded_formal_check_mode(
        wrapper_replay_records=wrapper_replay_records,
        jasper_check=jasper_check,
        wrapper_dry_run=wrapper_dry_run,
    )

    wrapper_results: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for case in cases:
        native_result = run_native_case(case, variant=variant, dry_run=native_dry_run)
        native_for_wrapper, native_source = select_native_oracle_for_wrapper(
            native_result,
            loaded_native_results.get(str(case["case_id"])),
        )
        wrapper_result = run_design2sva_wrapper_case(
            case=case,
            k=1,
            max_repair_rounds=0,
            reference_oracle=True,
            use_llm=False,
            llm_command=None,
            replay_records=None,
            jasper_check=wrapper_jasper_check,
            jasper_dry_run=wrapper_dry_run,
            jasper_replay_records=wrapper_replay_records,
            jasper_out_root=resolve_repo_path(jasper_out_root),
            context_budget=context_budget,
            native_oracle=native_for_wrapper,
            run_harness_diagnostics=run_harness_diagnostics,
        )
        wrapper_results.append(wrapper_result)
        results.append(
            build_expanded_case_result(
                case=case,
                native_result=native_result,
                native_for_wrapper=native_for_wrapper,
                native_oracle_source=native_source,
                wrapper_result=wrapper_result,
                formal_mode=formal_mode,
            )
        )

    wrapper_summary = summarize_design2sva_wrapper(
        wrapper_results,
        k=1,
        jasper_check=wrapper_jasper_check,
        jasper_dry_run=wrapper_dry_run,
        jasper_replay=wrapper_replay_records is not None,
    )
    public_wrapper_summary = {
        key: value for key, value in wrapper_summary.items() if key != "rows"
    }

    return {
        "schema_version": "v1",
        "mode": EXPANDED_REFERENCE_MODE,
        "backend": "jaspergold",
        "dry_run": effective_dry_run,
        "native_dry_run": native_dry_run,
        "wrapper_dry_run": wrapper_dry_run,
        "formal_check_mode": formal_mode,
        "variant": variant,
        "cases_path": repo_relative(cases_path),
        "default_output_paths": {
            "local": repo_relative(DEFAULT_EXPANDED_LOCAL_OUT),
            "jasper": repo_relative(DEFAULT_EXPANDED_JASPER_OUT),
        },
        "native_oracle_results": repo_relative(native_results_path),
        "jasper_replay": repo_relative(jasper_replay_path),
        "jasper_out_root": repo_relative(jasper_out_root),
        "summary": summarize_expanded_results(
            results,
            wrapper_summary=public_wrapper_summary,
            dry_run=effective_dry_run,
            native_dry_run=native_dry_run,
            wrapper_dry_run=wrapper_dry_run,
            formal_mode=formal_mode,
        ),
        "wrapper_summary": public_wrapper_summary,
        "results": results,
    }


def resolved_native_oracle_results_path(
    native_oracle_results_path: Path | None,
    *,
    use_replay: bool,
) -> Path | None:
    if native_oracle_results_path is not None:
        return native_oracle_results_path
    default = resolve_repo_path(DEFAULT_OUT)
    if use_replay and default.exists():
        return DEFAULT_OUT
    return None


def load_native_oracle_index(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    resolved = resolve_repo_path(path)
    if not resolved.exists():
        return {}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    rows = payload.get("results", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("case_id") or "")
        if case_id:
            indexed[case_id] = row
    return indexed


def select_native_oracle_for_wrapper(
    native_result: dict[str, Any],
    loaded_native_result: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    if loaded_native_result is not None and native_result.get("native_reference_proves") is None:
        return loaded_native_result, "loaded_native_oracle_results"
    return native_result, "current_native_mapping_validation"


def expanded_formal_check_mode(
    *,
    wrapper_replay_records: list[dict[str, Any]] | None,
    jasper_check: bool,
    wrapper_dry_run: bool,
) -> str:
    if wrapper_replay_records is not None:
        return "replay"
    if wrapper_dry_run:
        return "dry_run"
    if jasper_check:
        return "jasper"
    return "not_run"


def build_expanded_case_result(
    case: dict[str, Any],
    native_result: dict[str, Any],
    native_for_wrapper: dict[str, Any],
    native_oracle_source: str,
    wrapper_result: dict[str, Any],
    formal_mode: str,
) -> dict[str, Any]:
    round_record = first_wrapper_round(wrapper_result)
    candidate = dict(round_record.get("candidate") or {})
    metrics = dict(round_record.get("metrics") or {})
    audit = dict(wrapper_result.get("harness_reachability_audit") or {})
    native_validation = validate_native_mapping_result(native_result)
    wrapper_validation = validate_wrapper_reference_behavior(
        case,
        candidate=candidate,
        metrics=metrics,
        audit=audit,
        native_oracle=native_for_wrapper,
        formal_mode=formal_mode,
    )
    clock_reset_validation = validate_clock_reset_metadata(case, metrics=metrics, audit=audit)
    cover_validation = validate_cover_handling(metrics=metrics, audit=audit)
    validations = {
        "native_mapping": native_validation,
        "wrapper_reference": wrapper_validation,
        "clock_reset_metadata": clock_reset_validation,
        "cover_handling": cover_validation,
    }
    status = "passed" if all(item["passed"] for item in validations.values()) else "failed"
    root_cause_summary = build_expanded_root_cause_summary(
        status=status,
        validations=validations,
        metrics=metrics,
        native_result=native_result,
        native_for_wrapper=native_for_wrapper,
    )
    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "property_id": case["property_id"],
        "validation_status": status,
        "native_oracle_source": native_oracle_source,
        "native_mapping": native_result,
        "native_reference_oracle": native_for_wrapper,
        "design2sva_wrapper_reference": wrapper_result,
        "wrapper_reference_behavior": wrapper_validation,
        "clock_reset_metadata": audit.get("clock_reset_metadata") or metrics.get(
            "clock_reset_metadata"
        ),
        "clock_reset_validation": clock_reset_validation,
        "cover_handling": cover_validation,
        "validations": validations,
        "root_cause_summary": root_cause_summary,
    }


def first_wrapper_round(wrapper_result: dict[str, Any]) -> dict[str, Any]:
    for candidate_path in wrapper_result.get("candidate_paths", []):
        if not isinstance(candidate_path, dict):
            continue
        rounds = candidate_path.get("rounds", [])
        if isinstance(rounds, list) and rounds:
            first = rounds[0]
            return first if isinstance(first, dict) else {}
    return {}


def validate_native_mapping_result(native_result: dict[str, Any]) -> dict[str, Any]:
    required_paths = {"design_rtl", "formal_harness", "properties", "assumptions", "run_jg_tcl"}
    native_paths = native_result.get("native_paths")
    path_keys = set(native_paths) if isinstance(native_paths, dict) else set()
    failures = []
    if native_result.get("mapping_status") != "mapped":
        failures.append("native mapping did not resolve")
    if native_result.get("candidate_embedding") is not False:
        failures.append("native validation must not embed generated candidates")
    if not native_result.get("native_property_path"):
        failures.append("native property path is missing")
    if not required_paths <= path_keys:
        failures.append("native benchmark paths are incomplete")
    return validation_result(
        passed=not failures,
        detail="; ".join(failures) if failures else "native mapping resolved",
        root_cause_candidate="reference_task_invalid" if failures else "unknown",
        root_cause_detail="native_mapping_invalid" if failures else "native_mapping_valid",
    )


def validate_wrapper_reference_behavior(
    case: dict[str, Any],
    *,
    candidate: dict[str, Any],
    metrics: dict[str, Any],
    audit: dict[str, Any],
    native_oracle: dict[str, Any],
    formal_mode: str,
) -> dict[str, Any]:
    reference = case_reference_sva(case).strip()
    proof = metrics.get("proof_metadata") if isinstance(metrics.get("proof_metadata"), dict) else {}
    failures = []
    if candidate.get("source") != "reference_oracle" or metrics.get("source") != "reference_oracle":
        failures.append("wrapper did not use the fixture reference oracle source")
    if str(candidate.get("sva") or "").strip() != reference:
        failures.append("wrapper candidate SVA differs from fixture reference_sva")
    if audit.get("reference_sva") != reference:
        failures.append("wrapper audit reference_sva differs from fixture reference_sva")
    if metrics.get("valid_json") is not True or metrics.get("syntax_ok") is not True:
        failures.append("wrapper reference candidate failed local syntax/schema checks")
    if metrics.get("has_hallucinated_signal") is True:
        failures.append("wrapper reference candidate reports hallucinated signals")
    if metrics.get("unsupported_helper_code_issue") is True:
        failures.append("wrapper reference candidate used disallowed helper code")

    proof_status = str(proof.get("proof_status") or "").lower()
    root_detail = str(metrics.get("root_cause_detail") or "")
    if formal_mode == "dry_run":
        if proof_status not in {"", "none", "not_run"}:
            failures.append("dry-run wrapper unexpectedly reported a proof result")
        if root_detail != "formal_check_not_run":
            failures.append("dry-run wrapper did not preserve formal_check_not_run detail")
    elif formal_mode == "replay":
        if proof_status != "proven":
            failures.append("replay wrapper did not replay a proven reference assertion")
        if native_oracle.get("native_reference_proves") is True and not metrics.get(
            "wrapper_parity_pass"
        ):
            failures.append("replay wrapper did not match native reference behavior")
    elif formal_mode == "jasper":
        if native_oracle.get("native_reference_proves") is True and not metrics.get(
            "wrapper_parity_pass"
        ):
            failures.append("Jasper wrapper did not match native reference behavior")

    return validation_result(
        passed=not failures,
        detail="; ".join(failures) if failures else f"wrapper reference behavior valid ({formal_mode})",
        root_cause_candidate=str(metrics.get("root_cause_candidate") or "unknown")
        if failures
        else "unknown",
        root_cause_detail=str(metrics.get("root_cause_detail") or "wrapper_reference_valid")
        if failures
        else "wrapper_reference_valid",
    )


def validate_clock_reset_metadata(
    case: dict[str, Any],
    *,
    metrics: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    expected = case.get("clock_reset", {})
    if not isinstance(expected, dict):
        expected = {}
    metadata = audit.get("clock_reset_metadata") or metrics.get("clock_reset_metadata") or {}
    diagnostics = metrics.get("clock_reset_diagnostics")
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(diagnostics, dict):
        diagnostics = {}

    failures = []
    for key in ("clock", "clock_edge", "reset", "reset_polarity"):
        if str(metadata.get(key) or "") != str(expected.get(key) or ""):
            failures.append(f"{key} metadata mismatch")
    if metrics.get("reset_clock_mismatch") is True or audit.get("reference_reset_clock_mismatch"):
        failures.append("reference SVA clock/reset does not match fixture metadata")
    if diagnostics.get("clock") and str(diagnostics.get("clock")) != str(expected.get("clock")):
        failures.append("diagnostic clock differs from fixture metadata")
    if diagnostics.get("reset") and str(diagnostics.get("reset")) != str(expected.get("reset")):
        failures.append("diagnostic reset differs from fixture metadata")

    return validation_result(
        passed=not failures,
        detail="; ".join(failures) if failures else "clock/reset metadata matches fixture",
        root_cause_candidate="reset_clock_mismatch" if failures else "unknown",
        root_cause_detail="clock_or_reset_contract_differs_from_native"
        if failures
        else "clock_reset_metadata_valid",
    )


def validate_cover_handling(*, metrics: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    antecedent = audit.get("reference_antecedent_metadata") or metrics.get(
        "antecedent_metadata"
    )
    if not isinstance(antecedent, dict):
        antecedent = {}
    requires_cover = antecedent_requires_cover(antecedent)
    cover_sva = str(audit.get("cover_sva") or antecedent.get("cover_sva") or "")
    cover_status = str(audit.get("cover_status") or antecedent.get("cover_status") or "")
    trigger_kind = str(
        antecedent.get("trigger_kind")
        or antecedent.get("condition_kind")
        or antecedent.get("antecedent_kind")
        or ""
    ).lower()
    has_cover = bool(cover_sva.strip())
    failures = []
    if requires_cover:
        if trigger_kind != "antecedent":
            failures.append("implication assertion was not classified as antecedent-triggered")
        if not has_cover:
            failures.append("implication assertion did not generate an antecedent cover")
        if not antecedent.get("cover_property_id"):
            failures.append("implication assertion is missing a cover property id")
    else:
        if trigger_kind not in {"invariant", "no_antecedent", "invariant/no_antecedent"}:
            failures.append("invariant assertion was not classified as invariant")
        if has_cover:
            failures.append("invariant assertion generated an unnecessary antecedent cover")
        if cover_status.lower() not in {"", "not_run", "none", "unknown", "no_antecedent"}:
            failures.append("invariant assertion reported an antecedent cover result")

    kind = "implication" if requires_cover else "invariant"
    return validation_result(
        passed=not failures,
        detail="; ".join(failures) if failures else f"{kind} cover handling valid",
        root_cause_candidate="cover_generation_bug" if failures else "unknown",
        root_cause_detail="invariant_vs_implication_cover_handling_invalid"
        if failures
        else "cover_handling_valid",
        extra={
            "kind": kind,
            "requires_antecedent_cover": requires_cover,
            "trigger_kind": trigger_kind,
            "cover_property_id": antecedent.get("cover_property_id") or "",
            "cover_sva": cover_sva,
            "cover_status": cover_status,
        },
    )


def antecedent_requires_cover(antecedent: dict[str, Any]) -> bool:
    if antecedent.get("requires_antecedent_cover") is True:
        return True
    trigger_kind = str(
        antecedent.get("trigger_kind")
        or antecedent.get("condition_kind")
        or antecedent.get("antecedent_kind")
        or ""
    ).lower()
    extraction_status = str(antecedent.get("extraction_status") or "").lower()
    if trigger_kind in {"invariant", "no_antecedent", "invariant/no_antecedent"}:
        return False
    if extraction_status in {"invariant", "no_antecedent", "invariant/no_antecedent"}:
        return False
    return bool(antecedent.get("cover_sva")) or extraction_status == "extracted"


def validation_result(
    *,
    passed: bool,
    detail: str,
    root_cause_candidate: str,
    root_cause_detail: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "passed": passed,
        "detail": detail,
        "root_cause_candidate": root_cause_candidate,
        "root_cause_detail": root_cause_detail,
    }
    if extra:
        result.update(extra)
    return result


def build_expanded_root_cause_summary(
    *,
    status: str,
    validations: dict[str, dict[str, Any]],
    metrics: dict[str, Any],
    native_result: dict[str, Any],
    native_for_wrapper: dict[str, Any],
) -> dict[str, Any]:
    failed = {
        name: validation
        for name, validation in validations.items()
        if not validation.get("passed")
    }
    candidates = [
        str(metrics.get("root_cause_candidate") or "unknown"),
        str(native_result.get("root_cause_candidate") or "unknown"),
        str(native_for_wrapper.get("root_cause_candidate") or "unknown"),
    ]
    details = [
        str(metrics.get("root_cause_detail") or "unknown"),
        str(native_result.get("root_cause_summary") or "unknown"),
    ]
    candidates.extend(
        str(validation.get("root_cause_candidate") or "unknown")
        for validation in failed.values()
    )
    details.extend(
        str(validation.get("root_cause_detail") or "unknown") for validation in failed.values()
    )
    candidates = sorted({candidate for candidate in candidates if candidate and candidate != "unknown"})
    details = sorted({detail for detail in details if detail and detail != "unknown"})

    if status == "passed":
        summary = "Expanded reference-oracle fixture validation passed."
    else:
        failed_names = ", ".join(sorted(failed))
        summary = f"Expanded reference-oracle fixture validation failed: {failed_names}."

    return {
        "status": status,
        "summary": summary,
        "failed_validations": sorted(failed),
        "root_cause_candidates": candidates or ["unknown"],
        "root_cause_details": details or ["unknown"],
    }


def summarize_expanded_results(
    results: list[dict[str, Any]],
    *,
    wrapper_summary: dict[str, Any],
    dry_run: bool,
    native_dry_run: bool,
    wrapper_dry_run: bool,
    formal_mode: str,
) -> dict[str, Any]:
    validation_status_counts = collections.Counter(
        str(row.get("validation_status") or "unknown") for row in results
    )
    validation_failure_counts: collections.Counter[str] = collections.Counter()
    validation_root_counts: collections.Counter[str] = collections.Counter()
    validation_detail_counts: collections.Counter[str] = collections.Counter()
    cover_kind_counts: collections.Counter[str] = collections.Counter()
    for row in results:
        validations = row.get("validations") if isinstance(row.get("validations"), dict) else {}
        for name, validation in validations.items():
            if not isinstance(validation, dict):
                continue
            if not validation.get("passed"):
                validation_failure_counts[str(name)] += 1
                validation_root_counts[str(validation.get("root_cause_candidate") or "unknown")] += 1
                validation_detail_counts[str(validation.get("root_cause_detail") or "unknown")] += 1
        cover = row.get("cover_handling") if isinstance(row.get("cover_handling"), dict) else {}
        if cover:
            cover_kind_counts[str(cover.get("kind") or "unknown")] += 1

    root_summary_counts: collections.Counter[str] = collections.Counter()
    root_detail_counts: collections.Counter[str] = collections.Counter()
    for row in results:
        summary = row.get("root_cause_summary")
        if not isinstance(summary, dict):
            continue
        for candidate in summary.get("root_cause_candidates", []):
            root_summary_counts[str(candidate)] += 1
        for detail in summary.get("root_cause_details", []):
            root_detail_counts[str(detail)] += 1

    mapped = sum(
        1
        for row in results
        if (row.get("native_mapping") or {}).get("mapping_status") == "mapped"
    )
    return {
        "num_cases": len(results),
        "dry_run": dry_run,
        "native_dry_run": native_dry_run,
        "wrapper_dry_run": wrapper_dry_run,
        "formal_check_mode": formal_mode,
        "mapped_cases": mapped,
        "all_cases_mapped": mapped == len(results),
        "candidate_embedding": False,
        "validation_status_counts": dict(sorted(validation_status_counts.items())),
        "validation_failure_counts": dict(sorted(validation_failure_counts.items())),
        "validation_root_cause_counts": dict(sorted(validation_root_counts.items())),
        "validation_root_cause_detail_counts": dict(sorted(validation_detail_counts.items())),
        "fixture_failures": validation_status_counts.get("failed", 0),
        "all_fixture_validations_passed": validation_status_counts.get("failed", 0) == 0,
        "cover_handling_kind_counts": dict(sorted(cover_kind_counts.items())),
        "root_cause_candidate_counts": dict(sorted(root_summary_counts.items())),
        "root_cause_detail_counts": dict(sorted(root_detail_counts.items())),
        "wrapper_reference_summary": wrapper_summary,
    }


def case_reference_sva(case: dict[str, Any]) -> str:
    metadata = case.get("evaluation_metadata", {})
    if isinstance(metadata, dict):
        return str(metadata.get("reference_sva") or "")
    return ""


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


def public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key != "rows"}


def run_wrapper_reference_cases(
    cases: list[dict[str, Any]],
    *,
    dry_run: bool,
    jasper_out_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from evaluation.run_design2sva_eval import run_case, summarize

    results = [
        run_case(
            case=case,
            k=1,
            max_repair_rounds=0,
            reference_oracle=True,
            use_llm=False,
            llm_command=None,
            replay_records=None,
            jasper_check=True,
            jasper_dry_run=dry_run,
            jasper_replay_records=None,
            jasper_out_root=resolve_repo_path(jasper_out_root),
            context_budget=24,
            native_oracle=None,
            run_harness_diagnostics=True,
        )
        for case in cases
    ]
    summary = summarize(
        results,
        k=1,
        jasper_check=True,
        jasper_dry_run=dry_run,
        jasper_replay=False,
    )
    return results, public_summary(summary)


def first_wrapper_metrics(result: dict[str, Any]) -> dict[str, Any]:
    paths = result.get("candidate_paths")
    if not isinstance(paths, list) or not paths:
        return {}
    rounds = paths[0].get("rounds") if isinstance(paths[0], dict) else None
    if not isinstance(rounds, list) or not rounds:
        return {}
    metrics = rounds[0].get("metrics") if isinstance(rounds[0], dict) else {}
    return metrics if isinstance(metrics, dict) else {}


def compact_wrapper_reference_result(result: dict[str, Any]) -> dict[str, Any]:
    metrics = first_wrapper_metrics(result)
    antecedent = metrics.get("antecedent_metadata")
    clock_reset = metrics.get("clock_reset_metadata")
    proof = metrics.get("proof_metadata")
    return {
        "case_id": result.get("case_id"),
        "design_id": result.get("design_id"),
        "property_id": result.get("property_id"),
        "failure_category": metrics.get("failure_category"),
        "root_cause_candidate": metrics.get("root_cause_candidate"),
        "root_cause_detail": metrics.get("root_cause_detail"),
        "reset_clock_mismatch": metrics.get("reset_clock_mismatch"),
        "unsupported_helper_code_issue": metrics.get("unsupported_helper_code_issue"),
        "has_hallucinated_signal": metrics.get("has_hallucinated_signal"),
        "syntax_ok": metrics.get("syntax_ok"),
        "wrapper_parity_pass": metrics.get("wrapper_parity_pass"),
        "clock_reset_metadata": clock_reset if isinstance(clock_reset, dict) else {},
        "antecedent_metadata": compact_antecedent_metadata(
            antecedent if isinstance(antecedent, dict) else {}
        ),
        "proof_metadata": compact_proof_metadata(proof if isinstance(proof, dict) else {}),
        "harness_reachability_audit": compact_harness_audit(
            result.get("harness_reachability_audit", {})
        ),
    }


def compact_antecedent_metadata(antecedent: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "extraction_status",
        "antecedent",
        "antecedent_kind",
        "trigger_kind",
        "requires_antecedent_cover",
        "cover_property_id",
        "cover_sva",
        "cover_status",
        "antecedent_reachability",
    ]
    return {key: antecedent.get(key) for key in keys if key in antecedent}


def compact_proof_metadata(proof: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "backend",
        "status",
        "syntax_status",
        "proof_status",
        "vacuity_status",
        "report_dir",
    ]
    return {key: proof.get(key) for key in keys if key in proof}


def compact_harness_audit(audit: Any) -> dict[str, Any]:
    if not isinstance(audit, dict):
        return {}
    keys = [
        "case_id",
        "design_id",
        "property_id",
        "reference_available",
        "reference_syntax_ok",
        "reference_reset_clock_mismatch",
        "harness_reachability_status",
        "cover_property_id",
        "cover_status",
    ]
    return {key: audit.get(key) for key in keys if key in audit}


def expanded_failure_summary(
    native_results: list[dict[str, Any]],
    wrapper_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failures = []
    wrapper_by_case = {
        str(result.get("case_id")): first_wrapper_metrics(result) for result in wrapper_results
    }
    for native in native_results:
        case_id = str(native.get("case_id") or "")
        wrapper = wrapper_by_case.get(case_id, {})
        native_failed = native.get("mapping_status") != "mapped"
        wrapper_failed = bool(
            wrapper.get("reset_clock_mismatch")
            or wrapper.get("has_hallucinated_signal")
            or wrapper.get("unsupported_helper_code_issue")
            or wrapper.get("syntax_ok") is False
        )
        if not native_failed and not wrapper_failed:
            continue
        failures.append(
            {
                "case_id": case_id,
                "design_id": native.get("design_id"),
                "property_id": native.get("property_id"),
                "native_root_cause_candidate": native.get("root_cause_candidate"),
                "native_root_cause_summary": native.get("root_cause_summary"),
                "wrapper_failure_category": wrapper.get("failure_category"),
                "wrapper_root_cause_candidate": wrapper.get("root_cause_candidate"),
                "wrapper_root_cause_detail": wrapper.get("root_cause_detail"),
            }
        )
    return failures


def summarize_expanded_reference_validation(
    native_payload: dict[str, Any],
    wrapper_results: list[dict[str, Any]],
    wrapper_summary: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    native_summary = native_payload["summary"]
    wrapper_metrics = [first_wrapper_metrics(result) for result in wrapper_results]
    antecedent_rows = [
        metrics.get("antecedent_metadata")
        for metrics in wrapper_metrics
        if isinstance(metrics.get("antecedent_metadata"), dict)
    ]
    invariant_count = sum(
        1
        for antecedent in antecedent_rows
        if str(antecedent.get("trigger_kind") or "") == "invariant"
    )
    implication_count = sum(
        1
        for antecedent in antecedent_rows
        if bool(antecedent.get("requires_antecedent_cover"))
    )
    cover_generated_count = sum(1 for antecedent in antecedent_rows if antecedent.get("cover_sva"))
    reset_clock_mismatch_count = sum(
        1 for metrics in wrapper_metrics if metrics.get("reset_clock_mismatch")
    )
    root_cause_summaries = expanded_failure_summary(
        native_payload["results"],
        wrapper_results,
    )
    return {
        "num_cases": int(native_summary["num_cases"]),
        "k": 1,
        "dry_run": dry_run,
        "formal_metrics_status": "not_run" if dry_run else "measured",
        "source_counts": wrapper_summary.get("source_counts", {}),
        "fallback_rate": wrapper_summary.get("fallback_rate", 0.0),
        "valid_json_rate": wrapper_summary.get("valid_json_rate", 0.0),
        "native_mapped_cases": native_summary["mapped_cases"],
        "native_all_cases_mapped": native_summary["all_cases_mapped"],
        "wrapper_cases": wrapper_summary.get("num_cases"),
        "wrapper_formal_metrics_status": wrapper_summary.get("formal_metrics_status"),
        "wrapper_source_counts": wrapper_summary.get("source_counts", {}),
        "wrapper_failure_categories": wrapper_summary.get("failure_categories", {}),
        "wrapper_root_cause_details": wrapper_summary.get("root_cause_detail_counts", {}),
        "clock_reset_metadata_checked": len(wrapper_metrics),
        "reset_clock_mismatch_count": reset_clock_mismatch_count,
        "invariant_reference_count": invariant_count,
        "implication_reference_count": implication_count,
        "cover_required_count": implication_count,
        "cover_generated_count": cover_generated_count,
        "native_proof_status_counts": native_summary["native_proof_status_counts"],
        "native_vacuity_status_counts": native_summary["native_vacuity_status_counts"],
        "native_root_cause_candidate_counts": native_summary["root_cause_candidate_counts"],
        "root_cause_summaries": root_cause_summaries,
    }


def build_expanded_reference_payload(
    cases: list[dict[str, Any]],
    cases_path: Path,
    variant: str,
    dry_run: bool,
    jasper_out_root: Path,
) -> dict[str, Any]:
    native_payload = build_payload(
        cases,
        cases_path=cases_path,
        variant=variant,
        dry_run=dry_run,
    )
    wrapper_results, wrapper_summary = run_wrapper_reference_cases(
        cases,
        dry_run=dry_run,
        jasper_out_root=jasper_out_root,
    )
    return {
        "schema_version": "stage14_reference_oracle_expanded_v1",
        "mode": EXPANDED_REFERENCE_MODE,
        "backend": "jaspergold",
        "dry_run": dry_run,
        "variant": variant,
        "cases_path": repo_relative(cases_path),
        "llm_prompts_sent": False,
        "result_artifact_paths": {
            "local": repo_relative(DEFAULT_EXPANDED_LOCAL_OUT),
            "jasper": repo_relative(DEFAULT_EXPANDED_JASPER_OUT),
        },
        "summary": summarize_expanded_reference_validation(
            native_payload,
            wrapper_results,
            wrapper_summary,
            dry_run=dry_run,
        ),
        "native_oracle": native_payload,
        "wrapper_reference_oracle_summary": wrapper_summary,
        "results": [
            {
                "case_id": native.get("case_id"),
                "design_id": native.get("design_id"),
                "property_id": native.get("property_id"),
                "native": native,
                "wrapper_reference": compact_wrapper_reference_result(wrapper),
            }
            for native, wrapper in zip(native_payload["results"], wrapper_results, strict=True)
        ],
        "claim_boundary": {
            "supported": (
                "Expanded local reference/native oracle and wrapper metadata validation "
                "ran without sending prompts."
            ),
            "unsupported": (
                "This artifact does not measure generated-candidate quality or production signoff."
            ),
        },
    }


def normalize_mode(args: argparse.Namespace) -> str:
    if args.expanded_local or args.expanded_jasper:
        return EXPANDED_REFERENCE_MODE
    mode = str(args.mode or NATIVE_REFERENCE_MODE)
    if mode in EXPANDED_REFERENCE_MODE_ALIASES:
        return EXPANDED_REFERENCE_MODE
    if mode in NATIVE_REFERENCE_MODE_ALIASES:
        return NATIVE_REFERENCE_MODE
    raise ValueError(f"Unsupported oracle mode: {mode}")


def default_out_for_mode(args: argparse.Namespace, mode: str) -> Path:
    if args.out != DEFAULT_OUT:
        return args.out
    if mode == EXPANDED_REFERENCE_MODE:
        return DEFAULT_EXPANDED_JASPER_OUT if args.expanded_jasper else DEFAULT_EXPANDED_LOCAL_OUT
    return DEFAULT_OUT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--variant", default="correct")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        default=NATIVE_REFERENCE_MODE,
        help=(
            "Oracle mode. Use 'native_reference_oracle' for the existing native flow "
            "or 'expanded' for Stage 14 native+wrapper reference validation."
        ),
    )
    parser.add_argument(
        "--expanded-local",
        action="store_true",
        help=(
            "Shortcut for Stage 14 expanded native+wrapper reference validation in "
            "local dry-run mode."
        ),
    )
    parser.add_argument(
        "--expanded-jasper",
        action="store_true",
        help=(
            "Shortcut for Stage 14 expanded native+wrapper reference validation with "
            "JasperGold expected."
        ),
    )
    parser.add_argument("--jasper-out-root", type=Path, default=DEFAULT_WRAPPER_OUT_ROOT)
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    mode = normalize_mode(args)
    dry_run = True if args.expanded_local else bool(args.dry_run)

    if mode == EXPANDED_REFERENCE_MODE:
        payload = build_expanded_reference_payload(
            cases,
            cases_path=args.cases,
            variant=args.variant,
            dry_run=dry_run,
            jasper_out_root=args.jasper_out_root,
        )
    else:
        payload = build_payload(
            cases,
            cases_path=args.cases,
            variant=args.variant,
            dry_run=dry_run,
        )

    out = resolve_repo_path(default_out_for_mode(args, mode))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
