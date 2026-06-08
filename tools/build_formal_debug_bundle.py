#!/usr/bin/env python3
"""Normalize generated-SVA check artifacts into a FormalDebugBundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OWNER_VALUES = {"sva", "harness", "assumption", "rtl", "unknown"}


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_formal_debug_bundle(
    *,
    check_result: dict[str, Any] | None = None,
    embedding_audit: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
    path_overrides: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    check_result = check_result or {}
    artifact_paths = check_result.get("artifact_paths")
    artifact_paths = artifact_paths if isinstance(artifact_paths, dict) else {}
    path_overrides = path_overrides or {}
    embedding_audit = embedding_audit or load_json(optional_path(path_overrides, artifact_paths, "embedding_audit_json"))
    candidate = candidate or load_json(optional_path(path_overrides, artifact_paths, "candidate_json"))

    case_id = first_string(
        embedding_audit.get("case_id"),
        check_result.get("case_id"),
        candidate.get("case_id"),
    )
    design_id = first_string(
        embedding_audit.get("design_id"),
        check_result.get("design_id"),
        candidate.get("design_id"),
    )
    property_id = first_string(
        embedding_audit.get("property_id"),
        candidate.get("property_id"),
        check_result.get("property_id"),
    )
    candidate_sva = first_string(candidate.get("sva"), embedded_candidate_sva(embedding_audit))
    root_cause = root_cause_signals(check_result, embedding_audit)
    recommendation = repair_recommendation(check_result, embedding_audit, root_cause)

    return {
        "schema_version": "formal_debug_bundle_v1",
        "case_id": case_id,
        "design_id": design_id,
        "property_id": property_id,
        "candidate_sva": candidate_sva,
        "status": {
            "syntax_status": syntax_status(check_result),
            "proof_status": status_string(check_result.get("proof_status")),
            "vacuity_status": status_string(check_result.get("vacuity_status")),
        },
        "debug_artifacts": debug_artifacts(artifact_paths, path_overrides, check_result),
        "root_cause_signals": root_cause,
        "repair_recommendation": recommendation,
    }


def optional_path(
    overrides: dict[str, str | None],
    artifact_paths: dict[str, Any],
    key: str,
) -> Path | None:
    value = overrides.get(key)
    if value is None:
        value = artifact_paths.get(key)
    if not value:
        return None
    return Path(str(value))


def first_string(*values: object) -> str:
    for value in values:
        if value is not None:
            text = str(value)
            if text:
                return text
    return ""


def embedded_candidate_sva(embedding_audit: dict[str, Any]) -> str:
    comparison = embedding_audit.get("comparison")
    if isinstance(comparison, dict):
        return first_string(comparison.get("embedded_candidate_sva"))
    return ""


def syntax_status(check_result: dict[str, Any]) -> str:
    if "syntax_status" in check_result:
        return status_string(check_result.get("syntax_status"))
    syntax_pass = check_result.get("syntax_pass")
    if syntax_pass is True:
        return "ok"
    if syntax_pass is False:
        return "failed"
    return "not_run"


def status_string(value: object) -> str:
    if value is None:
        return "not_run"
    text = str(value).strip()
    return text or "not_run"


def debug_artifacts(
    artifact_paths: dict[str, Any],
    overrides: dict[str, str | None],
    check_result: dict[str, Any],
) -> dict[str, str | None]:
    keys = [
        "report_dir",
        "embedding_audit_json",
        "embedding_audit_markdown",
        "generated_properties",
        "generated_harness",
        "run_command",
        "log",
        "properties_report",
        "cover_report",
        "vacuity_report",
        "candidate_json",
        "rtl_project_manifest",
    ]
    result: dict[str, str | None] = {}
    for key in keys:
        value = overrides.get(key)
        if value is None:
            value = artifact_paths.get(key)
        if value is None:
            value = check_result.get(key)
        result[key] = str(value) if value else None
    return result


def root_cause_signals(
    check_result: dict[str, Any],
    embedding_audit: dict[str, Any],
) -> dict[str, Any]:
    issue_flags = issue_flags_from_audit(embedding_audit)
    issues = sorted(
        {
            *[str(issue) for issue in list_value(embedding_audit.get("issues"))],
            *[name for name, flagged in issue_flags.items() if flagged],
        }
    )
    return {
        "embedding_issues": issues,
        "clock_reset_mismatch": bool(
            issue_flags.get("clock_reset_mismatch") or issue_flags.get("disable_iff_mismatch")
        ),
        "unknown_signals": unknown_signals(check_result, embedding_audit),
        "wrapper_parity_pass": wrapper_parity_pass(embedding_audit),
        "antecedent_reachable": antecedent_reachable(check_result, embedding_audit),
    }


def issue_flags_from_audit(embedding_audit: dict[str, Any]) -> dict[str, bool]:
    flags = embedding_audit.get("issue_flags")
    if isinstance(flags, dict):
        return {str(key): bool(value) for key, value in flags.items()}
    checks = embedding_audit.get("checks")
    if isinstance(checks, dict):
        return {
            str(key): bool(value.get("has_issue"))
            for key, value in checks.items()
            if isinstance(value, dict)
        }
    return {}


def unknown_signals(
    check_result: dict[str, Any],
    embedding_audit: dict[str, Any],
) -> list[str]:
    values: list[str] = []
    values.extend(str(item) for item in list_value(check_result.get("unknown_signals")))
    checks = embedding_audit.get("checks")
    if isinstance(checks, dict):
        unknown = checks.get("unknown_signal") or checks.get("unknown_signals")
        if isinstance(unknown, dict):
            values.extend(str(item) for item in list_value(unknown.get("signals")))
            values.extend(str(item) for item in list_value(unknown.get("unknown_signals")))
    return sorted(set(item for item in values if item))


def wrapper_parity_pass(embedding_audit: dict[str, Any]) -> bool | None:
    parity = embedding_audit.get("wrapper_parity")
    if isinstance(parity, dict) and "parity_pass" in parity:
        return bool(parity.get("parity_pass"))
    return None


def antecedent_reachable(
    check_result: dict[str, Any],
    embedding_audit: dict[str, Any],
) -> bool | None:
    for source in (check_result, embedding_audit):
        for key in ("antecedent_reachable", "cover_reachable"):
            if key in source:
                value = source.get(key)
                return bool(value) if value is not None else None
    metadata = check_result.get("proof_metadata")
    if isinstance(metadata, dict) and "antecedent_reachable" in metadata:
        value = metadata.get("antecedent_reachable")
        return bool(value) if value is not None else None
    return None


def repair_recommendation(
    check_result: dict[str, Any],
    embedding_audit: dict[str, Any],
    root_cause: dict[str, Any],
) -> dict[str, str]:
    flags = issue_flags_from_audit(embedding_audit)
    issues = set(root_cause.get("embedding_issues", []))
    proof_status = status_string(check_result.get("proof_status")).lower()
    vacuity_status = status_string(check_result.get("vacuity_status")).lower()
    feedback = str(check_result.get("feedback") or "").lower()

    if has_any(flags, issues, {"syntax_error", "unknown_signal", "unknown_signals", "helper_code_placement"}):
        return owner("sva", "Syntax, unknown-signal, or helper-code evidence points to the SVA candidate.")
    if has_any(flags, issues, {"clock_reset_mismatch", "disable_iff_mismatch"}):
        return owner("sva", "Clock/reset or disable-iff evidence points to the SVA candidate.")
    if has_any(flags, issues, {"wrong_top_module", "missing_bind_or_instantiation", "wrong_include_or_path_metadata"}):
        return owner("harness", "Harness, binding, or path metadata evidence must be fixed before RTL repair.")
    if is_vacuous(vacuity_status) or "vacuous assertion" in feedback or "unreachable_antecedent" in issues:
        if assumption_risk(embedding_audit, issues):
            return owner("assumption", "Vacuity or reachability evidence includes active-assumption risk.")
        return owner("sva", "Vacuity or unreachable antecedent should be repaired in the SVA/intent first.")
    if is_falsified(proof_status) and not issues and root_cause.get("antecedent_reachable") is True:
        return owner("rtl", "Falsified reachable property has no embedding, harness, or assumption blocker.")
    return owner("unknown", "Evidence is insufficient to safely assign repair ownership.")


def owner(next_owner: str, reason: str) -> dict[str, str]:
    if next_owner not in OWNER_VALUES:
        next_owner = "unknown"
    return {"next_owner": next_owner, "reason": reason}


def has_any(flags: dict[str, bool], issues: set[object], names: set[str]) -> bool:
    return any(flags.get(name) or name in issues for name in names)


def assumption_risk(embedding_audit: dict[str, Any], issues: set[object]) -> bool:
    if "assumption_risk" in issues or "active_assumption_risk" in issues:
        return True
    for key in ("assumption_risk", "active_assumption_risk"):
        if bool(embedding_audit.get(key)):
            return True
    return False


def is_falsified(status: str) -> bool:
    return status in {"cex", "falsified", "failed", "fail"}


def is_vacuous(status: str) -> bool:
    return status in {"vacuous", "weak_vacuous_assertion"}


def list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-result", type=Path)
    parser.add_argument("--embedding-audit", type=Path)
    parser.add_argument("--candidate-json", type=Path)
    parser.add_argument("--generated-properties")
    parser.add_argument("--generated-harness")
    parser.add_argument("--run-command")
    parser.add_argument("--log")
    parser.add_argument("--properties-report")
    parser.add_argument("--cover-report")
    parser.add_argument("--vacuity-report")
    parser.add_argument("--rtl-project-manifest")
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    check_result = load_json(args.check_result)
    overrides = {
        "embedding_audit_json": str(args.embedding_audit) if args.embedding_audit else None,
        "candidate_json": str(args.candidate_json) if args.candidate_json else None,
        "generated_properties": args.generated_properties,
        "generated_harness": args.generated_harness,
        "run_command": args.run_command,
        "log": args.log,
        "properties_report": args.properties_report,
        "cover_report": args.cover_report,
        "vacuity_report": args.vacuity_report,
        "rtl_project_manifest": args.rtl_project_manifest,
    }
    bundle = build_formal_debug_bundle(
        check_result=check_result,
        embedding_audit=load_json(args.embedding_audit),
        candidate=load_json(args.candidate_json),
        path_overrides=overrides,
    )
    text = json.dumps(bundle, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
