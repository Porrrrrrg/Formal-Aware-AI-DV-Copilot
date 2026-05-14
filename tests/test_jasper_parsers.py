from __future__ import annotations

from pathlib import Path

from tools.coverage_utils import build_coverage_evidence
from tools.parse_jg_report import parse_report, parse_report_payload, summarize_properties
from tools.parse_jg_trace import parse_trace

ROOT = Path(__file__).resolve().parents[1]


def test_report_parser_canonical_statuses() -> None:
    report = ROOT / "tests/fixtures/jasper/status_matrix.txt"

    rows = parse_report(report)
    summary = summarize_properties(rows)

    assert {row["property_id"]: row["status"] for row in rows}["p_syntax"] == "syntax_error"
    assert "cov_miss" in summary["uncovered_properties"]
    assert "cov_dead" in summary["unreachable_properties"]
    assert parse_report_payload(report)["parser_errors"] == []


def test_text_trace_parser_accepts_hierarchy_and_values() -> None:
    trace = ROOT / "tests/fixtures/jasper/cov_miss_trace.txt"

    payload = parse_trace(trace)

    assert payload["property_id"] == "cov_miss"
    assert payload["events"][0]["signals"]["pready"] == "1"
    assert payload["events"][1]["signals"]["valid"] == "true"


def test_coverage_evidence_prefers_observed_status_and_witness() -> None:
    evidence = build_coverage_evidence(
        {"coverage_goal": "cov_miss", "expected_reachable": True, "expected_cover_status": "reachable"},
        [{"property_id": "cov_miss", "witness_events": ["cycle 3: full=1"]}],
        [{"property_id": "cov_miss", "status": "uncovered", "result_file": "cover.rpt", "line": 7}],
        {},
    )

    assert evidence["observed_cover_status"] == "uncovered"
    assert evidence["closure_class"] == "reachable_coverage_gap"
    assert evidence["witness_events"] == ["cycle 3: full=1"]
