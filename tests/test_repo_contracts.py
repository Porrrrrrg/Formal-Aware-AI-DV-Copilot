from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_all_evidence_packets import iter_case_files  # noqa: E402
from copilot.agents.coverage_closure_agent import build_prompt as build_coverage_prompt  # noqa: E402
from copilot.agents.dv_triage_agent import build_prompt as build_triage_prompt  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402

CASE_DIRS = [
    Path("benchmarks/arbiter_rr2/cases"),
    Path("benchmarks/rv_buffer/cases"),
    Path("benchmarks/apb_regblock/cases"),
    Path("benchmarks/fifo_1r1w/cases"),
]


def repo_path(path: Path) -> Path:
    return ROOT / path


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def collect_signal_fields(value: object) -> set[str]:
    signals: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.endswith("signals") and isinstance(nested, list):
                signals.update(str(item) for item in nested)
            signals.update(collect_signal_fields(nested))
    elif isinstance(value, list):
        for item in value:
            signals.update(collect_signal_fields(item))
    return signals


def collect_evidence_like_fields(value: object) -> list[str]:
    fields: list[str] = []
    reserved_evidence_names = {
        "jasper_cover_result",
        "witness_trace",
        "proof_status",
        "cover_status",
        "vacuity_status",
        "jasper_status",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.startswith(("observed_", "jasper_")) or key in reserved_evidence_names:
                fields.append(key)
            fields.extend(collect_evidence_like_fields(nested))
    elif isinstance(value, list):
        for item in value:
            fields.extend(collect_evidence_like_fields(item))
    return fields


def has_evidence_reference(case: dict[str, object]) -> bool:
    return any(key in case for key in ("run_manifest", "run_manifest_path", "evidence_packet", "evidence_packet_path"))


def rtl_interface_signals(design: str) -> set[str]:
    rtl_dir = ROOT / "benchmarks" / design / "rtl"
    interface_signals: set[str] = set()
    for rtl_path in sorted(rtl_dir.glob("*.sv")):
        text = rtl_path.read_text()
        interface_pattern = (
            r"\b(?:input|output|inout)\b\s+(?:logic|wire|reg)?\s*"
            r"(?:\[[^\]]+\]\s*)?([A-Za-z_][A-Za-z0-9_]*)"
        )
        for match in re.finditer(interface_pattern, text):
            interface_signals.add(match.group(1))
    return interface_signals


def test_core_schemas_are_valid_json_schema() -> None:
    schema_paths = sorted(repo_path(Path("copilot/schemas")).glob("*.schema.json"))
    assert schema_paths

    for schema_path in schema_paths:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)


def test_benchmark_case_census_matches_expected_design_split() -> None:
    case_paths = iter_case_files(CASE_DIRS)
    assert len(case_paths) >= 50

    cases = [load_json(path) for path in case_paths]
    design_counts: dict[str, int] = {}
    coverage_cases = 0
    for case in cases:
        assert isinstance(case, dict)
        design = str(case["design_id"])
        design_counts[design] = design_counts.get(design, 0) + 1
        if case.get("task_type") == "coverage_closure":
            coverage_cases += 1

    assert design_counts == {
        "apb_regblock": 12,
        "arbiter_rr2": 12,
        "fifo_1r1w": 17,
        "rv_buffer": 12,
    }
    assert coverage_cases == 14


@pytest.mark.parametrize("case_path", iter_case_files(CASE_DIRS))
def test_every_case_has_expected_label_and_action(case_path: Path) -> None:
    case = load_json(case_path)
    assert isinstance(case, dict)
    assert case.get("label_source") == "author_expected"
    assert case.get("expected_issue_type")
    assert case.get("expected_next_action")


@pytest.mark.parametrize("case_path", iter_case_files(CASE_DIRS))
def test_case_signal_fields_exist_in_signal_role_map_or_rtl_interface(case_path: Path) -> None:
    case = load_json(case_path)
    assert isinstance(case, dict)
    design = str(case["design_id"])
    signal_map_path = repo_path(Path("benchmarks") / design / "manifests" / "signal_role_map.yaml")
    signal_map = yaml.safe_load(signal_map_path.read_text())
    known_signals = set(signal_map["signals"]) | rtl_interface_signals(design)

    assert collect_signal_fields(case) <= known_signals


@pytest.mark.parametrize("case_path", iter_case_files(CASE_DIRS))
def test_case_metadata_separates_expected_labels_from_observed_evidence(case_path: Path) -> None:
    case = load_json(case_path)
    assert isinstance(case, dict)

    evidence_like_fields = collect_evidence_like_fields(case)
    assert not evidence_like_fields or has_evidence_reference(case), (
        f"{case_path} has evidence-like fields without run_manifest/evidence_packet reference: "
        f"{sorted(set(evidence_like_fields))}"
    )


@pytest.mark.parametrize(
    "manifest_path",
    sorted((ROOT / "benchmarks").glob("*/manifests/assertion_manifest.yaml")),
)
def test_manifest_assertion_signals_exist_in_signal_role_map(manifest_path: Path) -> None:
    design = manifest_path.parents[1].name
    signal_map_path = ROOT / "benchmarks" / design / "manifests" / "signal_role_map.yaml"
    signal_map = yaml.safe_load(signal_map_path.read_text())
    assertion_manifest = yaml.safe_load(manifest_path.read_text())
    known_signals = set(signal_map["signals"])

    for assertion in assertion_manifest.get("assertions", []):
        assert set(assertion.get("signals", [])) <= known_signals


@pytest.mark.parametrize(
    "sva_case_path",
    [ROOT / "benchmarks" / "sva_generation_cases.json", ROOT / "benchmarks" / "sva_repair_cases.json"],
)
def test_sva_case_signals_exist_in_signal_role_map(sva_case_path: Path) -> None:
    cases = load_json(sva_case_path)
    assert isinstance(cases, list)

    signal_maps: dict[str, set[str]] = {}
    for case in cases:
        design = str(case["design_id"])
        if design not in signal_maps:
            signal_map_path = ROOT / "benchmarks" / design / "manifests" / "signal_role_map.yaml"
            signal_map = yaml.safe_load(signal_map_path.read_text())
            signal_maps[design] = set(signal_map["signals"])
        assert set(case.get("signals", [])) <= signal_maps[design]


@pytest.mark.parametrize("case_path", iter_case_files(CASE_DIRS))
def test_generated_evidence_packet_validates_without_gold_label(case_path: Path) -> None:
    schema = load_json(repo_path(Path("copilot/schemas/evidence_packet.schema.json")))
    assert isinstance(schema, dict)
    validator = Draft202012Validator(schema)

    packet = build_packet(case_path=case_path)
    errors = sorted(validator.iter_errors(packet), key=lambda err: list(err.path))
    assert errors == []
    packet_text = json.dumps(packet)
    assert "gold_label" not in packet
    assert "gold_label" not in packet_text
    assert "expected_issue_type" not in packet_text
    assert "expected_next_action" not in packet_text
    assert "label_source" not in packet_text
    assert "root_cause" not in packet_text

    triage_prompt = build_triage_prompt(packet)
    coverage_prompt = build_coverage_prompt(packet)
    for prompt in [triage_prompt, coverage_prompt]:
        assert "gold_label" not in prompt
        assert "expected_issue_type" not in prompt
        assert "expected_next_action" not in prompt
        assert "label_source" not in prompt
        assert "root_cause" not in prompt
