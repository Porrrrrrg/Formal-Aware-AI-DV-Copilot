#!/usr/bin/env python3
"""Design2SVA candidate generator with replay and deterministic scaffold modes."""

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
sys.path.insert(0, str(ROOT))

from copilot.llm_client import call_llm_json  # noqa: E402
from copilot.sva_library import SVA_TEMPLATES, extract_identifiers  # noqa: E402

SCHEMA_PATH = ROOT / "copilot" / "schemas" / "design2sva_candidate.schema.json"
DEFAULT_REPLAY_PATH = ROOT / "evaluation" / "fixtures" / "design2sva_replay_outputs.jsonl"
PROMPT_OMIT_KEYS = {"reference_sva", "expected_proof_status"}

REACHABILITY_GUIDANCE = [
    (
        "Choose an antecedent or trigger condition that should be reachable under "
        "the RTL and harness context after legal reset release."
    ),
    (
        "Do not guard the property with contradictory or impossible state "
        "combinations, reset-only states, or handshakes that the context shows "
        "cannot fire."
    ),
    (
        "Prefer the simplest interface-level safety property that satisfies the "
        "intent before using deeper implementation state."
    ),
    (
        "Use reset_behavior, handshake_fire_conditions, and state_update_conditions "
        "as evidence for legal triggers and temporal boundaries."
    ),
    (
        "When the assertion has an antecedent, make intent_summary explain why "
        "that antecedent should be reachable."
    ),
]


def build_prompt(task: dict[str, Any], context: dict[str, Any]) -> str:
    payload = {
        "task": sanitized_task(task),
        "retrieved_context": sanitized_context(context),
        "generation_guidance": {
            "reachability_requirements": REACHABILITY_GUIDANCE,
            "field_semantics": {
                "intent_summary": (
                    "Summarize the intent and, when the SVA uses an antecedent, "
                    "briefly explain why the selected trigger should be reachable."
                ),
                "sva": (
                    "Use only task.visible_signals and retrieved_context.visible_signals "
                    "for signal references; other retrieved fields are supporting evidence."
                ),
            },
        },
        "output_contract": {
            "required_json_fields": [
                "property_id",
                "sva",
                "helper_code",
                "referenced_signals",
                "intent_summary",
                "source",
                "repair_metadata",
                "proof_metadata",
            ],
            "helper_code_policy": task.get("helper_code_policy", {}),
        },
    }
    return (
        "You are JasperLoop-DV in Design2SVA mode. Generate one useful, "
        "non-vacuous "
        "SystemVerilog assertion from the natural-language intent and bounded "
        "RTL/harness context. Reachability is part of correctness: require "
        "reachable trigger conditions, avoid impossible states, and prefer "
        "simple interface-level safety properties before implementation-specific "
        "properties. Use only visible or retrieved signals. Do not include "
        "helper code unless the helper-code policy allows it. The benchmark "
        "answer assertion is intentionally omitted; do not request or rely on "
        "evaluation-only answers. Return strict JSON matching the output "
        "contract.\n\n"
        + json.dumps(payload, indent=2)
    )


def sanitized_task(task: dict[str, Any]) -> dict[str, Any]:
    clone = sanitize_prompt_payload(task)
    if not isinstance(clone, dict):
        return {}
    metadata = dict(clone.get("evaluation_metadata", {}))
    clone["evaluation_metadata"] = metadata
    return clone


def sanitized_context(context: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_prompt_payload(context)
    return sanitized if isinstance(sanitized, dict) else {}


def sanitize_prompt_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_prompt_payload(item)
            for key, item in value.items()
            if str(key) not in PROMPT_OMIT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_prompt_payload(item) for item in value]
    return value


def generate_candidates(
    task: dict[str, Any],
    context: dict[str, Any],
    k: int = 1,
    use_llm: bool = False,
    llm_command: str | None = None,
    replay_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    candidates = []
    for index in range(max(1, k)):
        source = "structured_fallback"
        raw: dict[str, Any]
        if replay_records is not None:
            raw = replay_candidate(task, replay_records, index)
            source = "replay"
        elif use_llm:
            try:
                response = call_llm_json(build_prompt(task, context), llm_command, timeout_s=240)
                raw = response.json_object
                source = "llm"
            except Exception as exc:  # noqa: BLE001 - fallback keeps local runs reproducible.
                raw = structured_candidate(task)
                raw["llm_error"] = str(exc)
                source = "structured_fallback"
        else:
            raw = structured_candidate(task)
        candidates.append(normalize_candidate(task, context, raw, source=source, round_index=0))
    return candidates


def structured_candidate(task: dict[str, Any]) -> dict[str, Any]:
    property_id = str(task.get("property_id") or "generated_property")
    metadata = task.get("evaluation_metadata", {})
    reference = metadata.get("reference_sva") if isinstance(metadata, dict) else None
    sva = SVA_TEMPLATES.get(property_id) or str(reference or "")
    if not sva:
        sva = synthesize_simple_sva(task)
    return {
        "property_id": property_id,
        "sva": sva,
        "helper_code": "",
        "intent_summary": str(task.get("intent", "")),
        "source": "structured_fallback",
    }


def synthesize_simple_sva(task: dict[str, Any]) -> str:
    property_id = str(task.get("property_id") or "generated_property")
    clock_reset = task.get("clock_reset", {})
    clock = str(clock_reset.get("clock") or "clk") if isinstance(clock_reset, dict) else "clk"
    reset = str(clock_reset.get("reset") or "") if isinstance(clock_reset, dict) else ""
    reset_polarity = (
        str(clock_reset.get("reset_polarity") or "unknown")
        if isinstance(clock_reset, dict)
        else "unknown"
    )
    visible = task.get("visible_signals", [])
    signal = next(
        (str(item) for item in reversed(visible) if str(item) not in {clock, reset}),
        "1'b1",
    )
    reset_expr = ""
    if reset:
        reset_condition = f"!{reset}" if reset_polarity == "active_low" else reset
        reset_expr = f" disable iff ({reset_condition})"
    return f"{property_id}: assert property (@(posedge {clock}){reset_expr} {signal});"


def replay_candidate(
    task: dict[str, Any],
    records: list[dict[str, Any]],
    index: int,
    round_index: int = 0,
) -> dict[str, Any]:
    case_id = str(task.get("case_id") or "")
    property_id = str(task.get("property_id") or "")
    matches = [
        record
        for record in records
        if str(record.get("case_id", "")) == case_id
        and str(record.get("property_id", property_id)) == property_id
        and int(record.get("round", 0)) == round_index
        and isinstance(record.get("response"), dict)
    ]
    if not matches:
        return structured_candidate(task)
    selected = matches[min(index, len(matches) - 1)]
    response = selected.get("response")
    return response if isinstance(response, dict) else selected


def normalize_candidate(
    task: dict[str, Any],
    context: dict[str, Any],
    output: dict[str, Any],
    source: str,
    round_index: int,
) -> dict[str, Any]:
    property_id = str(output.get("property_id") or task.get("property_id") or "generated_property")
    sva = str(output.get("sva", "")).strip() or structured_candidate(task)["sva"]
    helper_code = str(output.get("helper_code", ""))
    repair_metadata = output.get("repair_metadata", {})
    if not isinstance(repair_metadata, dict):
        repair_metadata = {}
    candidate = {
        "property_id": property_id,
        "sva": sva,
        "helper_code": helper_code,
        "referenced_signals": candidate_referenced_signals(task, context, sva),
        "intent_summary": str(output.get("intent_summary") or task.get("intent", "")),
        "source": str(output.get("source") or source),
        "repair_metadata": {
            "round": round_index,
            "failure_category": str(
                output.get("failure_category")
                or repair_metadata.get("failure_category")
                or "not_run"
            ),
            "feedback": str(output.get("feedback") or repair_metadata.get("feedback") or ""),
            "changed_by_repair": bool(
                output.get("changed_by_repair")
                or repair_metadata.get("changed_by_repair", False)
            ),
        },
        "proof_metadata": {
            "backend": "jaspergold",
            "status": "not_run",
            "syntax_status": "not_run",
            "proof_status": None,
            "vacuity_status": None,
            "report_dir": None,
        },
    }
    validate_candidate(candidate)
    return candidate


def candidate_referenced_signals(
    task: dict[str, Any],
    context: dict[str, Any],
    sva: str,
) -> list[str]:
    allowed = allowed_signal_set(task, context)
    property_id = str(task.get("property_id") or "")
    return sorted(
        identifier
        for identifier in extract_identifiers(sva)
        if identifier in allowed and identifier != property_id
    )


def allowed_signal_set(task: dict[str, Any], context: dict[str, Any]) -> set[str]:
    allowed = {str(signal) for signal in task.get("visible_signals", [])}
    allowed.update(str(signal) for signal in context.get("visible_signals", []))
    interface = context.get("interface", {})
    if isinstance(interface, dict):
        allowed.update(
            str(port.get("name")) for port in interface.get("ports", []) if port.get("name")
        )
    clock_reset = context.get("clock_reset_candidates", {})
    if isinstance(clock_reset, dict):
        for names in clock_reset.values():
            if isinstance(names, list):
                allowed.update(str(name) for name in names)
    return allowed


def load_replay_records(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, dict) and isinstance(data.get("responses"), list):
        return [item for item in data["responses"] if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return replay_records_from_result_payload(data)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unsupported replay response format: {path}")


def replay_records_from_result_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract replay records from a committed Design2SVA result artifact."""

    records: list[dict[str, Any]] = []
    results = payload.get("results", [])
    if not isinstance(results, list):
        return records

    for result in results:
        if not isinstance(result, dict):
            continue
        result_case_id = str(result.get("case_id") or "")
        result_property_id = str(result.get("property_id") or "")
        paths = result.get("candidate_paths", [])
        if not isinstance(paths, list):
            continue
        for path in paths:
            if not isinstance(path, dict):
                continue
            path_candidate_index = safe_int(path.get("candidate_index"), default=0)
            rounds = path.get("rounds", [])
            if not isinstance(rounds, list):
                continue
            for round_record in rounds:
                if not isinstance(round_record, dict):
                    continue
                candidate = round_record.get("candidate")
                if not isinstance(candidate, dict):
                    continue
                metrics = round_record.get("metrics", {})
                if not isinstance(metrics, dict):
                    metrics = {}
                round_index = safe_int(
                    metrics.get("round"),
                    default=safe_int(
                        (candidate.get("repair_metadata") or {}).get("round")
                        if isinstance(candidate.get("repair_metadata"), dict)
                        else None,
                        default=0,
                    ),
                )
                candidate_index = safe_int(
                    metrics.get("candidate_index"),
                    default=path_candidate_index,
                )
                case_id = str(metrics.get("case_id") or result_case_id)
                property_id = str(metrics.get("property_id") or result_property_id)
                if not case_id or not property_id:
                    continue
                records.append(
                    {
                        "task": "design2sva",
                        "phase": "candidate" if round_index == 0 else "repair",
                        "case_id": case_id,
                        "property_id": property_id,
                        "candidate_index": candidate_index,
                        "round": round_index,
                        "response": dict(candidate),
                    }
                )
    return records


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_candidate(candidate: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(candidate)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--replay", nargs="?", const=DEFAULT_REPLAY_PATH, type=Path)
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    task = json.loads(args.task.read_text(encoding="utf-8"))
    if isinstance(task, list):
        task = task[0]
    if not isinstance(task, dict):
        raise ValueError("task must be a JSON object or non-empty JSON array")
    context = {}
    if args.context:
        context = json.loads(args.context.read_text(encoding="utf-8"))
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(task, context) + "\n", encoding="utf-8")
    replay_records = load_replay_records(args.replay)
    candidates = generate_candidates(
        task,
        context,
        k=args.k,
        use_llm=args.llm,
        llm_command=args.llm_command,
        replay_records=replay_records,
    )
    payload: dict[str, Any] = {"candidates": candidates}
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
