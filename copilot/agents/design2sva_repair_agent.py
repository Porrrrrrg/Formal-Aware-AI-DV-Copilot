#!/usr/bin/env python3
"""Debug-backed Design2SVA SVA repair agent."""

from __future__ import annotations

import argparse
import json
import re
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

from copilot.agents.design2sva_agent import allowed_signal_set  # noqa: E402
from copilot.llm_client import call_llm_json, llm_configured  # noqa: E402
from copilot.sva_library import extract_identifiers, normalize_sva  # noqa: E402

PROMPT_PATH = ROOT / "copilot" / "prompts" / "design2sva_repair_prompt.md"
SCHEMA_PATH = ROOT / "copilot" / "schemas" / "design2sva_repair_candidate.schema.json"
PROMPT_OMIT_KEYS = {"reference_sva", "expected_proof_status", "gold_label"}


def repair_design2sva_candidate(
    *,
    task: dict[str, Any],
    context: dict[str, Any],
    current_candidate: dict[str, Any],
    metrics: dict[str, Any],
    formal_debug_bundle: dict[str, Any] | None = None,
    jasper_feedback: str = "",
    active_assumptions: list[Any] | None = None,
    round_index: int = 1,
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, Any]:
    prompt = build_prompt(
        task=task,
        context=context,
        current_candidate=current_candidate,
        metrics=metrics,
        formal_debug_bundle=formal_debug_bundle,
        jasper_feedback=jasper_feedback,
        active_assumptions=active_assumptions,
        round_index=round_index,
    )
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(prompt, llm_command, timeout_s=240)
            return normalize_repair_output(
                task=task,
                context=context,
                current_candidate=current_candidate,
                metrics=metrics,
                output=response.json_object,
                source="llm_design2sva_repair",
                round_index=round_index,
            )
        except Exception as exc:  # noqa: BLE001 - deterministic fallback preserves local runs.
            fallback = structured_repair_output(task, context, current_candidate, metrics, round_index)
            fallback["llm_error"] = str(exc)
            return fallback
    return structured_repair_output(task, context, current_candidate, metrics, round_index)


def build_prompt(
    *,
    task: dict[str, Any],
    context: dict[str, Any],
    current_candidate: dict[str, Any],
    metrics: dict[str, Any],
    formal_debug_bundle: dict[str, Any] | None = None,
    jasper_feedback: str = "",
    active_assumptions: list[Any] | None = None,
    round_index: int = 1,
) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    payload = {
        "round": round_index,
        "task": sanitize_payload(task),
        "retrieved_context": sanitize_payload(context),
        "current_candidate": sanitize_payload(current_candidate),
        "allowed_signals": sorted(allowed_signal_set(task, context)),
        "clock_reset_contract": clock_reset_contract(task, context),
        "formal_debug_bundle": formal_debug_bundle or formal_debug_bundle_from_metrics(
            task,
            current_candidate,
            metrics,
        ),
        "jasper_feedback": jasper_feedback or failure_feedback(metrics),
        "embedding_audit_issue_flags": embedding_issue_flags(metrics),
        "antecedent_reachability": {
            "antecedent_metadata": metrics.get("antecedent_metadata", {}),
            "antecedent_reachable": metrics.get("antecedent_reachable"),
            "cover_reachable": metrics.get("cover_reachable"),
        },
        "active_assumptions": active_assumptions or task.get("active_assumptions", []),
        "output_contract": {
            "required_json_fields": [
                "property_id",
                "sva",
                "helper_code",
                "referenced_signals",
                "intent_summary",
                "repair_metadata",
                "source",
            ],
            "strict_json_only": True,
        },
    }
    return template.rstrip() + "\n\nREPAIR_CONTEXT:\n" + json.dumps(payload, indent=2)


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): sanitize_payload(item)
            for key, item in value.items()
            if str(key) not in PROMPT_OMIT_KEYS
        }
    if isinstance(value, list | tuple):
        return [sanitize_payload(item) for item in value]
    return value


def clock_reset_contract(task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    clock_reset = task.get("clock_reset") if isinstance(task.get("clock_reset"), dict) else {}
    return {
        "clock": clock_reset.get("clock"),
        "clock_edge": clock_reset.get("clock_edge", "posedge"),
        "reset": clock_reset.get("reset"),
        "reset_polarity": clock_reset.get("reset_polarity", "unknown"),
        "context_candidates": context.get("clock_reset_candidates", {}),
    }


def formal_debug_bundle_from_metrics(
    task: dict[str, Any],
    current_candidate: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    proof = metrics.get("proof_metadata") if isinstance(metrics.get("proof_metadata"), dict) else {}
    artifact_paths = proof.get("artifact_paths") if isinstance(proof.get("artifact_paths"), dict) else {}
    return {
        "schema_version": "formal_debug_bundle_inline_v1",
        "case_id": str(task.get("case_id") or metrics.get("case_id") or ""),
        "design_id": str(task.get("design_id") or metrics.get("design_id") or ""),
        "property_id": str(current_candidate.get("property_id") or task.get("property_id") or ""),
        "candidate_sva": str(current_candidate.get("sva") or ""),
        "status": {
            "syntax_status": str(proof.get("syntax_status") or "not_run"),
            "proof_status": proof.get("proof_status"),
            "vacuity_status": proof.get("vacuity_status"),
        },
        "debug_artifacts": artifact_paths,
        "root_cause_signals": {
            "embedding_issues": embedding_issues(metrics),
            "clock_reset_mismatch": bool(metrics.get("reset_clock_mismatch")),
            "unknown_signals": list(metrics.get("hallucinated_identifiers") or []),
            "wrapper_parity_pass": metrics.get("wrapper_parity_pass"),
            "antecedent_reachable": metrics.get("antecedent_reachable"),
        },
        "repair_recommendation": {
            "next_owner": "sva",
            "reason": failure_feedback(metrics),
        },
    }


def embedding_issue_flags(metrics: dict[str, Any]) -> dict[str, Any]:
    audit = metrics.get("embedding_audit")
    if not isinstance(audit, dict):
        return {}
    backend_audit = audit.get("backend_audit")
    if isinstance(backend_audit, dict) and isinstance(backend_audit.get("issue_flags"), dict):
        return dict(backend_audit["issue_flags"])
    checks = audit.get("checks")
    if isinstance(checks, dict):
        return {
            str(key): bool(value.get("has_issue")) if isinstance(value, dict) else bool(value)
            for key, value in checks.items()
        }
    return {}


def embedding_issues(metrics: dict[str, Any]) -> list[str]:
    flags = embedding_issue_flags(metrics)
    return sorted(str(name) for name, flagged in flags.items() if flagged)


def failure_feedback(metrics: dict[str, Any]) -> str:
    feedback = metrics.get("failure_feedback") or metrics.get("feedback")
    if feedback:
        return str(feedback)
    category = str(metrics.get("failure_category") or "not_run")
    if category == "unknown_signal":
        unknown = ", ".join(str(item) for item in metrics.get("hallucinated_identifiers", []))
        return f"Candidate references unknown signals: {unknown}"
    if category == "reset_clock_mismatch":
        return "Candidate clock/reset event does not match the task clock/reset contract."
    if category == "weak_vacuous_assertion":
        return "Candidate is vacuous or too weak; repair toward a reachable, non-vacuous trigger."
    if category == "unreachable_antecedent":
        return "Candidate antecedent is unreachable; repair the trigger before considering RTL."
    if category == "syntax_error":
        return "Candidate failed SVA syntax checks."
    return "No JasperGold feedback is available."


def structured_repair_output(
    task: dict[str, Any],
    context: dict[str, Any],
    current_candidate: dict[str, Any],
    metrics: dict[str, Any],
    round_index: int,
) -> dict[str, Any]:
    allowed = sorted(allowed_signal_set(task, context))
    unknown = [str(item) for item in metrics.get("hallucinated_identifiers", [])]
    if unknown:
        signal = choose_repair_signal(task, allowed)
        sva = synthesize_signal_sva(task, current_candidate, signal)
    else:
        sva = str(current_candidate.get("sva") or "")
    output = {
        "property_id": str(current_candidate.get("property_id") or task.get("property_id") or "generated_property"),
        "sva": sva,
        "helper_code": "",
        "referenced_signals": referenced_signals(sva, allowed),
        "intent_summary": str(current_candidate.get("intent_summary") or task.get("intent") or ""),
        "repair_metadata": {
            "round": round_index,
            "failure_category": str(metrics.get("failure_category") or "not_run"),
            "feedback": failure_feedback(metrics),
            "changed_by_repair": normalize_sva(sva) != normalize_sva(str(current_candidate.get("sva") or "")),
        },
        "source": "structured_debug_repair",
    }
    validate_repair_candidate(output)
    return output


def choose_repair_signal(task: dict[str, Any], allowed: list[str]) -> str:
    clock_reset = task.get("clock_reset") if isinstance(task.get("clock_reset"), dict) else {}
    excluded = {
        str(task.get("property_id") or ""),
        str(clock_reset.get("clock") or ""),
        str(clock_reset.get("reset") or ""),
    }
    for signal in reversed(allowed):
        if signal and signal not in excluded:
            return signal
    return "1'b1"


def synthesize_signal_sva(
    task: dict[str, Any],
    current_candidate: dict[str, Any],
    signal: str,
) -> str:
    property_id = str(current_candidate.get("property_id") or task.get("property_id") or "generated_property")
    clock_reset = task.get("clock_reset") if isinstance(task.get("clock_reset"), dict) else {}
    clock = str(clock_reset.get("clock") or "clk")
    reset = str(clock_reset.get("reset") or "")
    polarity = str(clock_reset.get("reset_polarity") or "unknown")
    disable = ""
    if reset:
        reset_condition = f"!{reset}" if polarity == "active_low" else reset
        disable = f" disable iff ({reset_condition})"
    return f"{property_id}: assert property (@(posedge {clock}){disable} {signal});"


def normalize_repair_output(
    *,
    task: dict[str, Any],
    context: dict[str, Any],
    current_candidate: dict[str, Any],
    metrics: dict[str, Any],
    output: dict[str, Any],
    source: str,
    round_index: int,
) -> dict[str, Any]:
    sva = str(output.get("sva") or current_candidate.get("sva") or "")
    allowed = sorted(allowed_signal_set(task, context))
    repaired = {
        "property_id": str(output.get("property_id") or current_candidate.get("property_id") or task.get("property_id") or ""),
        "sva": sva,
        "helper_code": str(output.get("helper_code") or ""),
        "referenced_signals": referenced_signals(sva, allowed),
        "intent_summary": str(output.get("intent_summary") or current_candidate.get("intent_summary") or task.get("intent") or ""),
        "repair_metadata": {
            "round": round_index,
            "failure_category": str(metrics.get("failure_category") or "not_run"),
            "feedback": failure_feedback(metrics),
            "changed_by_repair": normalize_sva(sva) != normalize_sva(str(current_candidate.get("sva") or "")),
        },
        "source": str(output.get("source") or source),
    }
    validate_repair_candidate(repaired)
    return repaired


def referenced_signals(sva: str, allowed: list[str]) -> list[str]:
    allowed_set = set(allowed)
    return sorted(identifier for identifier in extract_identifiers(sva) if identifier in allowed_set)


def validate_repair_candidate(candidate: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(candidate)


def first_object(data: object, path: Path) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    raise ValueError(f"{path} must contain a JSON object or non-empty object array")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--formal-debug-bundle", type=Path)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    task = first_object(json.loads(args.task.read_text(encoding="utf-8")), args.task)
    context = load_optional_json(args.context)
    candidate = first_object(json.loads(args.candidate.read_text(encoding="utf-8")), args.candidate)
    metrics = first_object(json.loads(args.metrics.read_text(encoding="utf-8")), args.metrics)
    bundle = load_optional_json(args.formal_debug_bundle)
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(
            build_prompt(
                task=task,
                context=context,
                current_candidate=candidate,
                metrics=metrics,
                formal_debug_bundle=bundle,
                round_index=args.round,
            )
            + "\n",
            encoding="utf-8",
        )
    repaired = repair_design2sva_candidate(
        task=task,
        context=context,
        current_candidate=candidate,
        metrics=metrics,
        formal_debug_bundle=bundle,
        round_index=args.round,
        use_llm=args.llm,
        llm_command=args.llm_command,
    )
    text = json.dumps(repaired, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def load_optional_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
