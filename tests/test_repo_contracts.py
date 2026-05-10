from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_all_evidence_packets import iter_case_files  # noqa: E402
from tools.build_evidence_packet import build_packet  # noqa: E402

CASE_DIRS = [
    Path("benchmarks/arbiter_rr2/cases"),
    Path("benchmarks/rv_buffer/cases"),
    Path("benchmarks/apb_regblock/cases"),
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
    assert len(case_paths) == 30

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
        "apb_regblock": 10,
        "arbiter_rr2": 10,
        "rv_buffer": 10,
    }
    assert coverage_cases == 9


@pytest.mark.parametrize("case_path", iter_case_files(CASE_DIRS))
def test_generated_evidence_packet_validates_without_gold_label(case_path: Path) -> None:
    schema = load_json(repo_path(Path("copilot/schemas/evidence_packet.schema.json")))
    assert isinstance(schema, dict)
    validator = Draft202012Validator(schema)

    packet = build_packet(case_path=case_path)
    errors = sorted(validator.iter_errors(packet), key=lambda err: list(err.path))
    assert errors == []
    assert "gold_label" not in packet
