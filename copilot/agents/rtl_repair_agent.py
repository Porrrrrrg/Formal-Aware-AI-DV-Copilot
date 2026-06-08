#!/usr/bin/env python3
"""RTL repair proposal agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - dependency-minimal local smoke runs.

    class Draft202012Validator:  # type: ignore[no-redef]
        def __init__(self, _schema: dict[str, Any]) -> None:
            pass

        def validate(self, _instance: dict[str, Any]) -> None:
            return None


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copilot.llm_client import call_llm_json, llm_configured  # noqa: E402

PROMPT_PATH = ROOT / "copilot" / "prompts" / "rtl_repair_prompt.md"
SCHEMA_PATH = ROOT / "copilot" / "schemas" / "rtl_repair_candidate.schema.json"
ISSUE_TYPES = {
    "rtl_design_bug",
    "assertion_property_bug",
    "assumption_constraint_bug",
    "harness_bug",
    "unknown",
}


def propose_rtl_repair(
    *,
    rtl_project_manifest: dict[str, Any],
    formal_debug_bundle: dict[str, Any],
    stable_sva: dict[str, Any],
    counterexample_summary: dict[str, Any] | None = None,
    triage: dict[str, Any] | None = None,
    suspect_signals: list[str] | None = None,
    suspect_rtl_slices: list[dict[str, Any]] | None = None,
    active_assumptions: list[Any] | None = None,
    prior_proven_properties: list[Any] | None = None,
    allowed_patch_files: list[str] | None = None,
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, Any]:
    prompt = build_prompt(
        rtl_project_manifest=rtl_project_manifest,
        formal_debug_bundle=formal_debug_bundle,
        stable_sva=stable_sva,
        counterexample_summary=counterexample_summary or {},
        triage=triage or {},
        suspect_signals=suspect_signals or [],
        suspect_rtl_slices=suspect_rtl_slices or [],
        active_assumptions=active_assumptions or [],
        prior_proven_properties=prior_proven_properties or [],
        allowed_patch_files=allowed_patch_files or [],
    )
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(prompt, llm_command, timeout_s=240)
            return normalize_candidate(response.json_object, fallback_issue_type=triage_issue_type(triage))
        except Exception as exc:  # noqa: BLE001 - deterministic fallback preserves local runs.
            candidate = deterministic_candidate(
                triage=triage or {},
                suspect_signals=suspect_signals or [],
                allowed_patch_files=allowed_patch_files or [],
            )
            candidate["risk_notes"].append(f"LLM repair failed: {exc}")
            validate_candidate(candidate)
            return candidate
    return deterministic_candidate(
        triage=triage or {},
        suspect_signals=suspect_signals or [],
        allowed_patch_files=allowed_patch_files or [],
    )


def build_prompt(
    *,
    rtl_project_manifest: dict[str, Any],
    formal_debug_bundle: dict[str, Any],
    stable_sva: dict[str, Any],
    counterexample_summary: dict[str, Any],
    triage: dict[str, Any],
    suspect_signals: list[str],
    suspect_rtl_slices: list[dict[str, Any]],
    active_assumptions: list[Any],
    prior_proven_properties: list[Any],
    allowed_patch_files: list[str],
) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    payload = {
        "rtl_project_manifest": rtl_project_manifest,
        "formal_debug_bundle": formal_debug_bundle,
        "stable_sva": stable_sva,
        "counterexample_summary": counterexample_summary,
        "triage": triage,
        "suspect_signals": suspect_signals,
        "suspect_rtl_slices": suspect_rtl_slices,
        "active_assumptions": active_assumptions,
        "prior_proven_properties": prior_proven_properties,
        "allowed_patch_files": allowed_patch_files,
        "output_contract": {
            "schema_version": "rtl_repair_candidate_v1",
            "issue_type_enum": sorted(ISSUE_TYPES),
            "requires_recheck_for_non_empty_patch": True,
        },
    }
    return template.rstrip() + "\n\nRTL_REPAIR_CONTEXT:\n" + json.dumps(payload, indent=2)


def deterministic_candidate(
    *,
    triage: dict[str, Any],
    suspect_signals: list[str],
    allowed_patch_files: list[str],
) -> dict[str, Any]:
    issue_type = triage_issue_type(triage)
    if issue_type != "rtl_design_bug":
        candidate = {
            "schema_version": "rtl_repair_candidate_v1",
            "issue_type": issue_type,
            "target_files": [],
            "unified_diff": "",
            "suspect_signals": suspect_signals,
            "rationale": "Formal debug evidence does not assign ownership to RTL repair.",
            "expected_effect": "No RTL patch proposed.",
            "risk_notes": ["Repair owner is not rtl_design_bug."],
            "requires_recheck": False,
        }
    else:
        candidate = {
            "schema_version": "rtl_repair_candidate_v1",
            "issue_type": "rtl_design_bug",
            "target_files": allowed_patch_files,
            "unified_diff": "",
            "suspect_signals": suspect_signals,
            "rationale": "RTL design bug evidence is present, but no deterministic RTL patch is available.",
            "expected_effect": "No source change until an LLM or engineer supplies a minimal diff.",
            "risk_notes": ["Patch generation requires external repair proposal."],
            "requires_recheck": True,
        }
    validate_candidate(candidate)
    return candidate


def triage_issue_type(triage: dict[str, Any] | None) -> str:
    triage = triage or {}
    issue_type = str(
        triage.get("predicted_issue_type")
        or triage.get("issue_type")
        or triage.get("next_owner")
        or "unknown"
    )
    if issue_type == "rtl":
        issue_type = "rtl_design_bug"
    return issue_type if issue_type in ISSUE_TYPES else "unknown"


def normalize_candidate(output: dict[str, Any], fallback_issue_type: str = "unknown") -> dict[str, Any]:
    candidate = {
        "schema_version": "rtl_repair_candidate_v1",
        "issue_type": str(output.get("issue_type") or fallback_issue_type),
        "target_files": [str(item) for item in list_value(output.get("target_files"))],
        "unified_diff": str(output.get("unified_diff") or ""),
        "suspect_signals": [str(item) for item in list_value(output.get("suspect_signals"))],
        "rationale": str(output.get("rationale") or ""),
        "expected_effect": str(output.get("expected_effect") or ""),
        "risk_notes": [str(item) for item in list_value(output.get("risk_notes"))],
        "requires_recheck": bool(output.get("requires_recheck")),
    }
    if candidate["issue_type"] not in ISSUE_TYPES:
        candidate["issue_type"] = "unknown"
    if candidate["unified_diff"].strip():
        candidate["requires_recheck"] = True
    validate_candidate(candidate)
    return candidate


def list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def validate_candidate(candidate: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(candidate)


def load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rtl-project-manifest", required=True, type=Path)
    parser.add_argument("--formal-debug-bundle", required=True, type=Path)
    parser.add_argument("--stable-sva", required=True, type=Path)
    parser.add_argument("--counterexample-summary", type=Path)
    parser.add_argument("--triage", type=Path)
    parser.add_argument("--allowed-patch-file", action="append", default=[])
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest = load_json(args.rtl_project_manifest)
    bundle = load_json(args.formal_debug_bundle)
    stable_sva = load_json(args.stable_sva)
    counterexample = load_json(args.counterexample_summary)
    triage = load_json(args.triage)
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(
            build_prompt(
                rtl_project_manifest=manifest,
                formal_debug_bundle=bundle,
                stable_sva=stable_sva,
                counterexample_summary=counterexample,
                triage=triage,
                suspect_signals=[],
                suspect_rtl_slices=[],
                active_assumptions=[],
                prior_proven_properties=[],
                allowed_patch_files=args.allowed_patch_file,
            )
            + "\n",
            encoding="utf-8",
        )
    candidate = propose_rtl_repair(
        rtl_project_manifest=manifest,
        formal_debug_bundle=bundle,
        stable_sva=stable_sva,
        counterexample_summary=counterexample,
        triage=triage,
        allowed_patch_files=args.allowed_patch_file,
        use_llm=args.llm,
        llm_command=args.llm_command,
    )
    text = json.dumps(candidate, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
