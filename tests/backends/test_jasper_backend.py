from __future__ import annotations

from pathlib import Path

from app.models.agent import BackendStatus
from copilot.backends.jasper_backend import JasperBackend


def test_parse_report_dir_proven_nonvacuous(tmp_path: Path) -> None:
    report_dir = tmp_path / "run"
    report_dir.mkdir()
    (report_dir / "properties.rpt").write_text("p_ok proven bound=2\n")

    result = JasperBackend().parse_report_dir(report_dir, property_id="p_ok")

    assert result.status == BackendStatus.PASSED
    assert result.proof_result.properties[0]["status"] == "proven"
    assert result.vacuity_result.status.value == "not_flagged_vacuous"


def test_parse_report_dir_vacuous_overrides_pass(tmp_path: Path) -> None:
    report_dir = tmp_path / "run"
    report_dir.mkdir()
    (report_dir / "properties.rpt").write_text("p_ok proven\n")
    (report_dir / "vacuity.rpt").write_text("p_ok vacuous\n")

    result = JasperBackend().parse_report_dir(report_dir, property_id="p_ok")

    assert result.status == BackendStatus.VACUOUS
    assert result.to_legacy_check_dict()["vacuity_status"] == "vacuous"


def test_parse_report_dir_syntax_error_selects_log(tmp_path: Path) -> None:
    report_dir = tmp_path / "run"
    report_dir.mkdir()
    (report_dir / "jg.log").write_text("Info\nERROR syntax error near property p_bad\n")

    result = JasperBackend().parse_report_dir(report_dir, property_id="p_bad", returncode=1)

    assert result.status == BackendStatus.SYNTAX_FAILED
    assert result.structured_errors
    assert "syntax" in result.feedback.lower()


def test_parse_report_dir_collects_counterexample_paths(tmp_path: Path) -> None:
    report_dir = tmp_path / "run"
    trace_dir = report_dir / "traces"
    trace_dir.mkdir(parents=True)
    (report_dir / "properties.rpt").write_text("p_bad falsified bound=4\n")
    (trace_dir / "demo.properties_i.p_bad.vcd").write_text("$enddefinitions $end\n#0\n")

    result = JasperBackend().parse_report_dir(report_dir, property_id="p_bad")

    assert result.status == BackendStatus.FAILED
    assert result.counterexample_paths
