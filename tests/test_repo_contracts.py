from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_all_evidence_packets import iter_case_files  # noqa: E402
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
    assert case.get("expected_issue_type")
    assert case.get("expected_next_action")


@pytest.mark.parametrize("case_path", iter_case_files(CASE_DIRS))
def test_case_related_signals_exist_in_signal_role_map(case_path: Path) -> None:
    case = load_json(case_path)
    assert isinstance(case, dict)
    design = str(case["design_id"])
    signal_map_path = repo_path(Path("benchmarks") / design / "manifests" / "signal_role_map.yaml")
    signal_map = yaml.safe_load(signal_map_path.read_text())
    known_signals = set(signal_map["signals"])

    related_signals = case.get("coverage_context", {}).get("related_signals", [])
    assert set(related_signals) <= known_signals


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
    assert "gold_label" not in packet
