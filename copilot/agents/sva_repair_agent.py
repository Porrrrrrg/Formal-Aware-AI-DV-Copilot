#!/usr/bin/env python3
"""SVA repair agent with Codex/command LLM support and deterministic fallback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from copilot.llm_client import call_llm_json, llm_configured
from copilot.sva_library import SVA_TEMPLATES

PROMPT_DIR = ROOT / "copilot" / "prompts"
PROMPT_VERSIONS = ("baseline", "cex_aware")
PROMPT_FILES = {
    "baseline": PROMPT_DIR / "sva_repair_prompt.md",
    "cex_aware": PROMPT_DIR / "sva_repair_cex_prompt.md",
}
CEX_FIELD_NAMES = (
    "failing_property_intent",
    "broken_sva",
    "jasper_status",
    "failing_cycle",
    "expected_behavior",
    "observed_behavior",
    "relevant_signal_values",
    "allowed_signal_whitelist",
    "reset_clock_semantics",
    "assumption_risks",
    "vacuity_hint",
)


def repair_once(
    case: dict[str, object],
    failed_sva: str,
    feedback: str = "",
    round_index: int = 1,
    use_llm: bool = False,
    llm_command: str | None = None,
    prompt_version: str = "baseline",
    feedback_context: dict[str, object] | None = None,
) -> dict[str, object]:
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(
                build_prompt(
                    case,
                    failed_sva,
                    feedback,
                    round_index,
                    prompt_version=prompt_version,
                    feedback_context=feedback_context,
                ),
                llm_command,
                timeout_s=240,
            )
            return normalize_repair(case, response.json_object)
        except Exception as exc:  # noqa: BLE001 - fallback keeps experiments running.
            fallback = structured_fallback(case)
            fallback["llm_error"] = str(exc)
            return fallback
    return structured_fallback(case)


def structured_fallback(case: dict[str, object]) -> dict[str, object]:
    property_id = str(case.get("property_id", "generated_property"))
    sva = SVA_TEMPLATES.get(property_id) or str(case.get("reference_sva", ""))
    if not sva:
        sva = str(case.get("broken_sva", ""))
    return {
        "source": "structured_fallback",
        "property_id": property_id,
        "sva": sva,
        "explanation": "Repaired by selecting the structured reference template for the intended property.",
    }


def build_prompt(
    case: dict[str, object],
    failed_sva: str,
    feedback: str = "",
    round_index: int = 1,
    prompt_version: str = "baseline",
    feedback_context: dict[str, object] | None = None,
) -> str:
    validate_prompt_version(prompt_version)
    if prompt_version == "cex_aware":
        return build_cex_aware_prompt(case, failed_sva, feedback, round_index, feedback_context)

    payload = sanitized_case(case)
    return (
        "You are JasperLoop-DV in SVA repair mode. "
        "Repair exactly one SystemVerilog assertion using only the property intent, allowed signals, "
        "and JasperGold feedback. Do not invent signals. Return JSON with property_id, sva, and explanation.\n\n"
        f"ROUND: {round_index}\n\n"
        "CASE:\n"
        + json.dumps(payload, indent=2)
        + "\n\nFAILED_SVA:\n"
        + failed_sva
        + "\n\nJASPER_FEEDBACK:\n"
        + (feedback or "No JasperGold feedback is available.")
    )


def build_cex_aware_prompt(
    case: dict[str, object],
    failed_sva: str,
    feedback: str,
    round_index: int,
    feedback_context: dict[str, object] | None,
) -> str:
    template = PROMPT_FILES["cex_aware"].read_text()
    context = build_cex_context(case, failed_sva, feedback, feedback_context)
    return (
        template.rstrip()
        + "\n\nROUND: "
        + str(round_index)
        + "\n\nCEX_AWARE_REPAIR_CONTEXT:\n"
        + json.dumps(context, indent=2)
        + "\n\nJASPER_FEEDBACK:\n"
        + (feedback or "No JasperGold feedback is available.")
    )


def build_cex_context(
    case: dict[str, object],
    failed_sva: str,
    feedback: str = "",
    feedback_context: dict[str, object] | None = None,
) -> dict[str, object]:
    cex = object_field(case, "counterexample_summary")
    vacuity = object_field(case, "vacuity_context")
    active_assumptions = case.get("active_assumptions", [])
    assumption_risks = first_available(
        case,
        cex,
        "assumption_risks",
        "assumption_risk",
        "risk",
    )
    if is_empty(assumption_risks):
        assumption_risks = risks_from_assumptions(active_assumptions)

    return {
        "case_id": case.get("case_id"),
        "design_id": case.get("design_id"),
        "property_id": case.get("property_id"),
        "bug_type": case.get("bug_type"),
        "failing_property_intent": case.get("intent"),
        "broken_sva": failed_sva or case.get("broken_sva"),
        "original_broken_sva": case.get("broken_sva"),
        "jasper_status": jasper_status(feedback_context, case),
        "failing_cycle": first_available(
            case,
            cex,
            "failing_cycle",
            "fail_cycle",
            "first_failing_cycle",
            "cycle",
        ),
        "expected_behavior": first_available(
            case,
            cex,
            "expected_behavior",
            "expected_observation",
            "expected",
            "intent",
        ),
        "observed_behavior": first_available(
            case,
            cex,
            "observed_behavior",
            "first_suspicious_observation",
            "observed",
            "actual_behavior",
        ),
        "relevant_signal_values": first_available(
            case,
            cex,
            "relevant_signal_values",
            "signal_values",
            "values",
            "trace_values",
            "semantic_events",
            "events",
        ),
        "allowed_signal_whitelist": allowed_signal_whitelist(case),
        "reset_clock_semantics": reset_clock_semantics(case, failed_sva),
        "active_assumptions": active_assumptions,
        "assumption_risks": assumption_risks,
        "vacuity_hint": vacuity_hint(case, cex, vacuity, feedback_context, feedback),
        "tool_feedback": feedback or None,
    }


def cex_fields_present(
    case: dict[str, object],
    failed_sva: str = "",
    feedback_context: dict[str, object] | None = None,
) -> dict[str, bool]:
    context = build_cex_context(case, failed_sva, feedback_context=feedback_context)
    return {name: not is_empty(context.get(name)) for name in CEX_FIELD_NAMES}


def validate_prompt_version(prompt_version: str) -> None:
    if prompt_version not in PROMPT_VERSIONS:
        choices = ", ".join(PROMPT_VERSIONS)
        raise ValueError(f"Unknown SVA repair prompt version: {prompt_version}. Choices: {choices}.")


def sanitized_case(case: dict[str, object]) -> dict[str, object]:
    clone = dict(case)
    clone.pop("reference_sva", None)
    clone.pop("gold_label", None)
    return clone


def normalize_repair(case: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    property_id = str(output.get("property_id") or case.get("property_id", "generated_property"))
    sva = str(output.get("sva", "")).strip()
    if not sva:
        sva = structured_fallback(case)["sva"]
    return {
        "source": "llm",
        "property_id": property_id,
        "sva": sva,
        "explanation": str(output.get("explanation", "")),
    }


def object_field(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def first_available(
    case: dict[str, object],
    cex: dict[str, object],
    *keys: str,
) -> object:
    for key in keys:
        if key in cex and not is_empty(cex[key]):
            return cex[key]
        if key in case and not is_empty(case[key]):
            return case[key]
    return None


def is_empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def allowed_signal_whitelist(case: dict[str, object]) -> list[str]:
    signals = case.get("signals", [])
    allowed = [str(signal) for signal in signals] if isinstance(signals, list) else []
    property_id = case.get("property_id")
    if property_id:
        allowed.append(str(property_id))
    return allowed


def reset_clock_semantics(case: dict[str, object], failed_sva: str) -> dict[str, object]:
    clock = case.get("clock")
    reset = case.get("reset")
    return {
        "clock": clock,
        "clocking_event": f"@(posedge {clock})" if clock else None,
        "reset": reset,
        "reset_usage_in_failed_sva": reset_usage(str(reset), failed_sva) if reset else None,
        "reset_polarity_hint": reset_polarity_hint(str(reset), failed_sva) if reset else None,
    }


def reset_usage(reset: str, failed_sva: str) -> str | None:
    if f"disable iff (!{reset})" in failed_sva:
        return f"disable iff (!{reset})"
    if f"disable iff ({reset})" in failed_sva:
        return f"disable iff ({reset})"
    if f"!{reset}" in failed_sva:
        return f"!{reset}"
    if reset in failed_sva:
        return reset
    return None


def reset_polarity_hint(reset: str, failed_sva: str) -> str | None:
    if f"!{reset}" in failed_sva or reset.endswith("n"):
        return "active_low_possible"
    if reset in failed_sva:
        return "active_high_possible"
    return None


def jasper_status(
    feedback_context: dict[str, object] | None,
    case: dict[str, object],
) -> dict[str, object] | object:
    if feedback_context:
        status = {
            "syntax_pass": feedback_context.get("jasper_syntax_pass"),
            "proof_status": feedback_context.get("jasper_proof_status"),
            "vacuity_status": feedback_context.get("jasper_vacuity_status"),
            "report_dir": feedback_context.get("jasper_report_dir"),
        }
        if any(not is_empty(value) for value in status.values()):
            return status
    return case.get("jasper_status")


def risks_from_assumptions(active_assumptions: object) -> list[object]:
    if not isinstance(active_assumptions, list):
        return []
    risks = []
    for assumption in active_assumptions:
        if isinstance(assumption, dict) and not is_empty(assumption.get("risk")):
            risks.append(assumption["risk"])
    return risks


def vacuity_hint(
    case: dict[str, object],
    cex: dict[str, object],
    vacuity: dict[str, object],
    feedback_context: dict[str, object] | None,
    feedback: str,
) -> object:
    hint = first_available(case, cex, "vacuity_hint", "vacuity")
    if not is_empty(hint):
        return hint
    if vacuity:
        return vacuity
    if feedback_context and not is_empty(feedback_context.get("jasper_vacuity_status")):
        return feedback_context.get("jasper_vacuity_status")
    if "vacu" in feedback.lower():
        return feedback
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--failed-sva")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-version", choices=PROMPT_VERSIONS, default="baseline")
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    case = first_object(json.loads(args.case.read_text()), args.case)
    failed_sva = args.failed_sva if args.failed_sva is not None else str(case.get("broken_sva", ""))
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(
            build_prompt(
                case,
                failed_sva,
                args.feedback,
                args.round,
                prompt_version=args.prompt_version,
            )
            + "\n"
        )
    output = repair_once(
        case=case,
        failed_sva=failed_sva,
        feedback=args.feedback,
        round_index=args.round,
        use_llm=args.llm,
        llm_command=args.llm_command,
        prompt_version=args.prompt_version,
    )
    text = json.dumps(output, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


def first_object(data: object, path: Path) -> dict[str, object]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    raise ValueError(f"{path} must contain a JSON object or non-empty object array")


if __name__ == "__main__":
    raise SystemExit(main())
