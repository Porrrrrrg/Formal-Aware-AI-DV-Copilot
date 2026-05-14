from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

STRICT_RESPONSE_SCHEMAS = [
    ROOT / "copilot" / "schemas" / "coverage_closure_output.schema.json",
    ROOT / "copilot" / "schemas" / "diagnosis_output.schema.json",
    ROOT / "copilot" / "schemas" / "design2sva_candidate.schema.json",
    ROOT / "copilot" / "schemas" / "sva_generation_output.schema.json",
    ROOT / "copilot" / "schemas" / "sva_repair_candidate.schema.json",
    ROOT / "copilot" / "schemas" / "sva_repair_output.schema.json",
]


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def iter_object_schemas(schema: object, path: str = "$") -> Iterator[tuple[str, dict[str, object]]]:
    if isinstance(schema, dict):
        schema_type = schema.get("type")
        is_object = schema_type == "object" or (
            isinstance(schema_type, list) and "object" in schema_type
        )
        if is_object:
            yield path, schema
        for key, value in schema.items():
            child_path = f"{path}.{key}"
            if key == "properties" and isinstance(value, dict):
                for property_name, property_schema in value.items():
                    yield from iter_object_schemas(property_schema, f"{child_path}.{property_name}")
            elif key == "items":
                yield from iter_object_schemas(value, f"{path}.items")
            elif isinstance(value, dict | list):
                yield from iter_object_schemas(value, child_path)
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            yield from iter_object_schemas(item, f"{path}[{index}]")


def test_response_schemas_are_strict_for_structured_outputs() -> None:
    failures: list[str] = []
    for schema_path in STRICT_RESPONSE_SCHEMAS:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        for object_path, object_schema in iter_object_schemas(schema):
            if object_schema.get("additionalProperties") is not False:
                failures.append(f"{schema_path.name}:{object_path} lacks additionalProperties:false")

            properties = object_schema.get("properties")
            if not isinstance(properties, dict):
                continue
            required = object_schema.get("required")
            required_set = set(required) if isinstance(required, list) else set()
            missing_required = sorted(set(properties) - required_set)
            if missing_required:
                missing = ", ".join(missing_required)
                failures.append(f"{schema_path.name}:{object_path} omits required properties: {missing}")

    assert failures == []


def test_minimal_response_fixtures_validate() -> None:
    fixtures = {
        "diagnosis_output.schema.json": {
            "case_id": "arbiter_rr2_bug_grant_overlap",
            "predicted_issue_type": "rtl_design_bug",
            "root_cause_ranked": [
                {
                    "rank": 1,
                    "hypothesis": "The RTL can assert two grants in the same cycle.",
                    "evidence": ["JasperGold falsified the mutual exclusion property."],
                }
            ],
            "suspect_rtl_signals": ["gnt0", "gnt1"],
            "suspect_assertions_or_assumptions": ["p_mutex"],
            "recommended_next_action": "fix_rtl",
            "debug_checklist": ["Inspect the grant priority logic."],
        },
        "coverage_closure_output.schema.json": {
            "case_id": "rv_buffer_cov_valid_ready",
            "coverage_gap_type": "reachable_coverage_gap",
            "recommended_next_action": "add_directed_test_or_sequence",
            "directed_sequence": ["Drive valid high while ready is low, then release ready."],
            "evidence": ["JasperGold cover result: reachable"],
        },
        "sva_repair_candidate.schema.json": {
            "property_id": "p_mutex",
            "sva": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
            "explanation": "Use mutual exclusion over the two grant signals.",
        },
        "design2sva_candidate.schema.json": {
            "property_id": "p_mutex",
            "sva": "p_mutex: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));",
            "helper_code": "",
            "referenced_signals": ["clk", "rst", "gnt0", "gnt1"],
            "intent_summary": "The arbiter grants must be mutually exclusive.",
            "source": "structured_fallback",
            "repair_metadata": {
                "round": 0,
                "failure_category": "not_run",
                "feedback": "",
                "changed_by_repair": False,
            },
            "proof_metadata": {
                "backend": "jaspergold",
                "status": "not_run",
                "syntax_status": "not_run",
                "proof_status": None,
                "vacuity_status": None,
                "report_dir": None,
            },
        },
    }

    for schema_name, fixture in fixtures.items():
        schema = load_json(ROOT / "copilot" / "schemas" / schema_name)
        Draft202012Validator(schema).validate(fixture)
