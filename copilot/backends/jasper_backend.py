"""JasperGold backend facade.

This module normalizes existing Jasper scripts and parsers behind typed backend
results. Existing CLI tools keep their legacy return shapes.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.models.agent import (
    BackendError,
    BackendResult,
    BackendStatus,
    CheckResult,
    CheckStatus,
)
from copilot.backends.base import FormalBackend
from tools.check_generated_sva import (
    ROOT,
    check_generated_sva as legacy_check_generated_sva,
    resolve_repo_path,
    select_log_lines,
)
from tools.parse_jg_report import parse_report, summarize_properties
from tools.parse_jg_trace import parse_trace
from tools.run_jasper import run_jasper as legacy_run_jasper


class JasperBackend(FormalBackend):
    """Typed facade for JasperGold execution and report parsing."""

    name = "jaspergold"

    def check_generated_sva(
        self,
        case: dict[str, Any],
        prediction: dict[str, Any],
        system: str,
        out_root: Path | None = None,
        dry_run: bool = False,
    ) -> BackendResult:
        started = time.monotonic()
        report_dir = generated_sva_report_dir(case, system, out_root)
        property_id = str(prediction.get("property_id") or case.get("property_id") or "")
        try:
            legacy = legacy_check_generated_sva(
                case=case,
                prediction=prediction,
                system=system,
                out_root=out_root,
                dry_run=dry_run,
            )
            result = self.parse_report_dir(
                Path(str(legacy.get("report_dir") or report_dir)),
                property_id=property_id,
                returncode=legacy.get("jasper_returncode")
                if isinstance(legacy.get("jasper_returncode"), int)
                else None,
                dry_run=dry_run,
            )
            result.feedback = str(legacy.get("feedback") or result.feedback)
            result.elapsed_ms = elapsed_ms(started)
            legacy_metadata = {}
            if isinstance(legacy.get("artifact_paths"), dict):
                legacy_metadata["artifact_paths"] = legacy["artifact_paths"]
            if isinstance(legacy.get("embedding_audit"), dict):
                legacy_metadata["embedding_audit"] = legacy["embedding_audit"]
            if legacy_metadata:
                result.metadata = {**result.metadata, **legacy_metadata}
            return result
        except RuntimeError as exc:
            return blocked_result(report_dir, property_id, str(exc), elapsed_ms(started))

    def run_benchmark(
        self,
        design: str,
        variant: str = "correct",
        mode: str = "prove",
        dry_run: bool = False,
    ) -> BackendResult:
        started = time.monotonic()
        report_dir = ROOT / "jasper" / "reports" / f"{design}_{variant}_{mode}"
        try:
            report_dir = legacy_run_jasper(design, variant, mode, dry_run=dry_run)
            return self.parse_report_dir(
                report_dir,
                property_id=None,
                returncode=None,
                dry_run=dry_run,
            ).model_copy(update={"elapsed_ms": elapsed_ms(started)})
        except RuntimeError as exc:
            return blocked_result(report_dir, None, str(exc), elapsed_ms(started))

    def parse_report_dir(
        self,
        report_dir: Path,
        property_id: str | None = None,
        returncode: int | None = None,
        dry_run: bool = False,
    ) -> BackendResult:
        report_dir = resolve_repo_path(report_dir)
        properties_path = report_dir / "properties.rpt"
        cover_path = report_dir / "cover.rpt"
        vacuity_path = report_dir / "vacuity.rpt"
        log_path = report_dir / "jg.log"
        proof_path = properties_path if properties_path.exists() else cover_path

        proof_properties = (
            [] if dry_run else parse_report(proof_path) if proof_path.exists() else []
        )
        vacuity_properties = (
            [] if dry_run else parse_report(vacuity_path) if vacuity_path.exists() else []
        )
        proof_summary = summarize_properties(proof_properties)
        vacuity_summary = summarize_properties(vacuity_properties)
        focused_proof = focus_property(proof_properties, property_id)
        focused_vacuity = focus_property(vacuity_properties, property_id)

        syntax_status = syntax_check_status(
            dry_run=dry_run,
            returncode=returncode,
            proof_path_exists=proof_path.exists(),
        )
        proof_status = status_from_property(focused_proof, proof_properties)
        vacuity_status = vacuity_check_status(focused_vacuity, vacuity_properties, proof_status)
        status = overall_status(syntax_status, proof_status, vacuity_status, dry_run)

        errors = structured_errors(report_dir, syntax_status, returncode, log_path)
        traces = trace_paths(report_dir)
        parsed_traces = parse_traces(traces, property_id)
        feedback = backend_feedback(report_dir, proof_properties, vacuity_properties, syntax_status)

        return BackendResult(
            status=status,
            syntax_result=CheckResult(
                status=syntax_status,
                report_path=str(proof_path) if proof_path.exists() else None,
            ),
            proof_result=CheckResult(
                status=proof_status,
                properties=proof_properties,
                summary=proof_summary,
                report_path=str(proof_path) if proof_path.exists() else None,
            ),
            vacuity_result=CheckResult(
                status=vacuity_status,
                properties=vacuity_properties,
                summary=vacuity_summary,
                report_path=str(vacuity_path) if vacuity_path.exists() else None,
            ),
            counterexample_paths=[str(path) for path in traces],
            parsed_counterexamples=parsed_traces,
            raw_log_paths=[str(log_path)] if log_path.exists() else [],
            report_dir=str(report_dir),
            raw_report_paths={
                "properties": str(properties_path) if properties_path.exists() else None,
                "cover": str(cover_path) if cover_path.exists() else None,
                "vacuity": str(vacuity_path) if vacuity_path.exists() else None,
            },
            returncode=returncode,
            structured_errors=errors,
            feedback=feedback,
            metadata={"focus_property": property_id},
        )


def generated_sva_report_dir(case: dict[str, Any], system: str, out_root: Path | None) -> Path:
    out_root = out_root or ROOT / "jasper" / "reports" / "sva_generation"
    root = resolve_repo_path(out_root)
    return root / system / str(case.get("case_id", "unknown_case"))


def elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def focus_property(
    properties: list[dict[str, Any]],
    property_id: str | None,
) -> dict[str, Any] | None:
    if not properties:
        return None
    if not property_id:
        return properties[0] if len(properties) == 1 else None
    for row in properties:
        name = str(row.get("property_id", ""))
        if name == property_id or name.endswith("." + property_id) or property_id in name:
            return row
    return properties[0] if len(properties) == 1 else None


def syntax_check_status(
    dry_run: bool,
    returncode: int | None,
    proof_path_exists: bool,
) -> CheckStatus:
    if dry_run:
        return CheckStatus.NOT_RUN
    if returncode not in {None, 0} and not proof_path_exists:
        return CheckStatus.SYNTAX_ERROR
    if proof_path_exists:
        return CheckStatus.PASSED
    return CheckStatus.NOT_RUN


def status_from_property(
    focused: dict[str, Any] | None,
    properties: list[dict[str, Any]],
) -> CheckStatus:
    source = focused or (properties[0] if len(properties) == 1 else None)
    if not source:
        return CheckStatus.NOT_RUN
    status = str(source.get("status", "")).lower()
    mapping = {
        "proven": CheckStatus.PROVEN,
        "falsified": CheckStatus.FALSIFIED,
        "covered": CheckStatus.COVERED,
        "uncovered": CheckStatus.UNCOVERED,
        "unreachable": CheckStatus.UNREACHABLE,
        "vacuous": CheckStatus.VACUOUS,
        "undetermined": CheckStatus.UNDETERMINED,
        "syntax_error": CheckStatus.SYNTAX_ERROR,
    }
    return mapping.get(status, CheckStatus.ERROR)


def vacuity_check_status(
    focused: dict[str, Any] | None,
    vacuity_properties: list[dict[str, Any]],
    proof_status: CheckStatus,
) -> CheckStatus:
    if focused or vacuity_properties:
        return status_from_property(focused, vacuity_properties)
    if proof_status in {CheckStatus.PROVEN, CheckStatus.COVERED, CheckStatus.FALSIFIED}:
        return CheckStatus.NOT_FLAGGED_VACUOUS
    return CheckStatus.NOT_RUN


def overall_status(
    syntax_status: CheckStatus,
    proof_status: CheckStatus,
    vacuity_status: CheckStatus,
    dry_run: bool,
) -> BackendStatus:
    if dry_run:
        return BackendStatus.DRY_RUN
    if syntax_status == CheckStatus.SYNTAX_ERROR:
        return BackendStatus.SYNTAX_FAILED
    if syntax_status == CheckStatus.ERROR:
        return BackendStatus.ERROR
    if vacuity_status == CheckStatus.VACUOUS:
        return BackendStatus.VACUOUS
    if proof_status in {CheckStatus.FALSIFIED, CheckStatus.UNCOVERED, CheckStatus.UNREACHABLE}:
        return BackendStatus.FAILED
    if proof_status in {CheckStatus.PROVEN, CheckStatus.COVERED}:
        return BackendStatus.PASSED
    if proof_status in {CheckStatus.UNDETERMINED, CheckStatus.NOT_RUN}:
        return BackendStatus.UNKNOWN
    return BackendStatus.ERROR


def structured_errors(
    report_dir: Path,
    syntax_status: CheckStatus,
    returncode: int | None,
    log_path: Path,
) -> list[BackendError]:
    if syntax_status != CheckStatus.SYNTAX_ERROR:
        return []
    message = "JasperGold did not produce a parseable property report."
    if log_path.exists():
        selected = select_log_lines(log_path.read_text(errors="ignore").splitlines(), limit=8)
        if selected:
            message = "\n".join(selected)
    return [
        BackendError(
            kind="syntax_error",
            message=message,
            retryable=True,
            source=str(log_path if log_path.exists() else report_dir),
            details={"returncode": returncode},
        )
    ]


def trace_paths(report_dir: Path) -> list[Path]:
    trace_dir = report_dir / "traces"
    if not trace_dir.exists():
        return []
    return sorted([*trace_dir.glob("*.vcd"), *trace_dir.glob("*.vcd.gz")])


def parse_traces(paths: list[Path], property_id: str | None) -> list[dict[str, Any]]:
    ordered = sorted(
        paths,
        key=lambda path: (
            0 if property_id and property_id in path.name else 1,
            path.name,
        ),
    )
    parsed: list[dict[str, Any]] = []
    for path in ordered[:3]:
        try:
            parsed.append(parse_trace(path))
        except Exception as exc:  # noqa: BLE001 - parser errors are reported structurally.
            parsed.append({"trace_file": str(path), "parser_errors": [str(exc)]})
    return parsed


def backend_feedback(
    report_dir: Path,
    properties: list[dict[str, Any]],
    vacuity: list[dict[str, Any]],
    syntax_status: CheckStatus,
) -> str:
    if syntax_status == CheckStatus.SYNTAX_ERROR:
        log_path = report_dir / "jg.log"
        if log_path.exists():
            return "\n".join(select_log_lines(log_path.read_text(errors="ignore").splitlines()))
        return "JasperGold failed before producing a property report."
    vacuous = [
        f"{item.get('property_id')}: {item.get('status')}"
        for item in vacuity
        if str(item.get("status", "")).lower() == "vacuous"
    ]
    if vacuous:
        return "Vacuity results: " + "; ".join(vacuous[:8])
    rendered = [
        f"{item.get('property_id')}: {item.get('status')}"
        for item in properties
        if item.get("property_id")
    ]
    if rendered:
        return "Property results: " + "; ".join(rendered[:8])
    return "No JasperGold status lines were parsed."


def blocked_result(
    report_dir: Path,
    property_id: str | None,
    message: str,
    elapsed: int,
) -> BackendResult:
    return BackendResult(
        status=BackendStatus.BLOCKED,
        syntax_result=CheckResult(status=CheckStatus.ERROR),
        proof_result=CheckResult(status=CheckStatus.NOT_RUN),
        vacuity_result=CheckResult(status=CheckStatus.NOT_RUN),
        report_dir=str(report_dir),
        elapsed_ms=elapsed,
        structured_errors=[
            BackendError(
                kind="tool_not_found" if "Cannot find JasperGold" in message else "backend_blocked",
                message=message,
                retryable=True,
                source=str(report_dir),
            )
        ],
        feedback=message,
        metadata={"focus_property": property_id},
    )
