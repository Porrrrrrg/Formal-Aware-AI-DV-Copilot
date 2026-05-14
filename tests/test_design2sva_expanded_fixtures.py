from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from copilot.agents.design2sva_agent import build_prompt


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "benchmarks" / "design2sva_cases.json"
TASK_SCHEMA_PATH = ROOT / "copilot" / "schemas" / "design2sva_task.schema.json"


def load_cases() -> list[dict[str, object]]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def native_properties_path(case: dict[str, object]) -> Path:
    design_id = str(case["design_id"])
    return ROOT / "benchmarks" / design_id / "formal" / f"{design_id}_properties.sv"


def reference_label(case: dict[str, object]) -> str:
    metadata = case["evaluation_metadata"]
    assert isinstance(metadata, dict)
    reference = metadata["reference_sva"]
    assert isinstance(reference, str)
    match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_$]*)\s*:\s*assert\s+property\b", reference)
    assert match, f"{case['case_id']} reference_sva has no assertion label"
    return match.group(1)


def test_design2sva_expanded_cases_are_schema_valid() -> None:
    schema = json.loads(TASK_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    cases = load_cases()
    assert len(cases) >= 10
    for case in cases:
        validator.validate(case)
        metadata = case["evaluation_metadata"]
        assert isinstance(metadata, dict)
        assert metadata["reference_available"] is True
        assert isinstance(metadata["reference_sva"], str)
        assert metadata["reference_sva"]


def test_design2sva_expanded_cases_have_valid_paths() -> None:
    for case in load_cases():
        for key in ("design_rtl_path", "harness_header_path"):
            relative_path = Path(str(case[key]))
            assert not relative_path.is_absolute()
            assert (ROOT / relative_path).is_file(), f"{case['case_id']} missing {key}"
        assert native_properties_path(case).is_file()


def test_design2sva_expanded_cases_have_unique_case_property_pairs() -> None:
    cases = load_cases()
    pairs = {(str(case["case_id"]), str(case["property_id"])) for case in cases}
    assert len(pairs) == len(cases)


def test_design2sva_reference_labels_exist_in_native_properties() -> None:
    for case in load_cases():
        label = reference_label(case)
        assert label == case["property_id"]
        native_properties = native_properties_path(case).read_text(encoding="utf-8")
        label_pattern = rf"^\s*{re.escape(label)}\s*:\s*assert\s+property\b"
        assert re.search(label_pattern, native_properties, flags=re.MULTILINE), (
            f"{case['case_id']} label {label} is missing from {native_properties_path(case)}"
        )


def test_design2sva_expanded_references_stay_out_of_prompts() -> None:
    for case in load_cases():
        metadata = case["evaluation_metadata"]
        assert isinstance(metadata, dict)
        prompt = build_prompt(
            case,
            {"visible_signals": case["visible_signals"], "interface": {"ports": []}},
        )

        assert str(metadata["reference_sva"]) not in prompt
        assert '"reference_sva"' not in prompt
        assert "expected_proof_status" not in prompt
