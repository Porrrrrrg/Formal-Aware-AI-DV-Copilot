from __future__ import annotations

import json
from pathlib import Path

from evaluation.run_design2sva_native_oracle import (
    build_payload,
    load_cases,
    main,
    map_case_to_native_flow,
)


def test_design2sva_cases_map_to_native_benchmark_flow() -> None:
    cases = load_cases(Path("benchmarks/design2sva_cases.json"))

    mappings = [map_case_to_native_flow(case) for case in cases]

    assert {mapping.design_id for mapping in mappings} == {
        "apb_regblock",
        "arbiter_rr2",
        "fifo_1r1w",
        "rv_buffer",
    }
    assert {mapping.property_id for mapping in mappings} == {
        "p_in_ready_when_full_and_out_ready",
        "p_mutex",
        "p_no_underflow",
        "p_setup_then_enable",
    }
    for mapping in mappings:
        assert mapping.design_rtl.exists()
        assert mapping.formal_harness.exists()
        assert mapping.properties.exists()
        assert mapping.assumptions.exists()
        assert mapping.run_jg_tcl.exists()
        assert mapping.top_harness == f"{mapping.design_id}_harness"
        assert mapping.native_property_path.endswith(f".properties_i.{mapping.property_id}")


def test_design2sva_native_oracle_dry_run_output(tmp_path, monkeypatch) -> None:
    out = tmp_path / "native_oracle.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_design2sva_native_oracle.py",
            "--dry-run",
            "--limit",
            "2",
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["mode"] == "native_reference_oracle"
    assert payload["backend"] == "jaspergold"
    assert payload["dry_run"] is True
    assert payload["summary"]["num_cases"] == 2
    assert payload["summary"]["mapped_cases"] == 2
    assert payload["summary"]["candidate_embedding"] is False
    assert payload["summary"]["native_proof_status_counts"] == {"not_run": 2}
    assert payload["summary"]["native_vacuity_status_counts"] == {"not_run": 2}
    assert payload["summary"]["native_reference_unknown_count"] == 2

    for result in payload["results"]:
        assert result["mapping_status"] == "mapped"
        assert result["candidate_embedding"] is False
        assert result["native_proof_status"] == "not_run"
        assert result["native_vacuity_status"] == "not_run"
        assert result["native_reference_proves"] is None
        assert result["root_cause_candidate"] == "unknown"
        assert result["native_report_dir"].startswith("jasper/reports/")
        assert set(result["native_paths"]) == {
            "design_rtl",
            "formal_harness",
            "properties",
            "assumptions",
            "run_jg_tcl",
        }


def test_dry_run_does_not_invoke_jasper(monkeypatch) -> None:
    cases = load_cases(Path("benchmarks/design2sva_cases.json"))[:1]

    def fail_run_jasper(*_args, **_kwargs):  # pragma: no cover - failure path only
        raise AssertionError("dry-run must not invoke JasperGold")

    monkeypatch.setattr(
        "evaluation.run_design2sva_native_oracle.legacy_run_jasper",
        fail_run_jasper,
    )

    payload = build_payload(
        cases,
        cases_path=Path("benchmarks/design2sva_cases.json"),
        variant="correct",
        dry_run=True,
    )

    assert payload["summary"]["native_proof_status_counts"] == {"not_run": 1}
    assert payload["results"][0]["native_reference_proves"] is None
