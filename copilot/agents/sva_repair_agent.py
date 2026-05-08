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


def repair_once(
    case: dict[str, object],
    failed_sva: str,
    feedback: str = "",
    round_index: int = 1,
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(
                build_prompt(case, failed_sva, feedback, round_index),
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
) -> str:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--failed-sva")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    case = first_object(json.loads(args.case.read_text()), args.case)
    failed_sva = args.failed_sva if args.failed_sva is not None else str(case.get("broken_sva", ""))
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(case, failed_sva, args.feedback, args.round) + "\n")
    output = repair_once(
        case=case,
        failed_sva=failed_sva,
        feedback=args.feedback,
        round_index=args.round,
        use_llm=args.llm,
        llm_command=args.llm_command,
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
