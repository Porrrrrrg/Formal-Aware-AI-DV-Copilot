#!/usr/bin/env python3
"""Direct RTL-plus-intent SVA baseline.

The direct baseline receives only design id, clock/reset names, property intent,
and signal names. It does not receive reference SVA or structured formal
evidence. A command-based LLM backend can be plugged in with `JASPERLOOP_LLM_CMD`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from copilot.llm_client import call_llm_json, llm_configured
from copilot.sva_library import SVA_TEMPLATES


def generate_direct(
    case: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(build_prompt(case), llm_command)
            return normalize_output(case, response.json_object)
        except Exception as exc:  # noqa: BLE001 - fallback is intentional.
            fallback = direct_fallback(case)
            fallback["llm_error"] = str(exc)
            return fallback
    return direct_fallback(case)


def direct_fallback(case: dict[str, object]) -> dict[str, object]:
    property_id = str(case.get("property_id", "generated_property"))
    intent = str(case.get("intent", "")).lower()
    clock = str(case.get("clock", "clk"))
    reset = str(case.get("reset", "rst"))

    if "never grant both" in intent:
        sva = SVA_TEMPLATES["p_mutex"]
    elif "stored output data" in intent and "stalled" in intent:
        sva = SVA_TEMPLATES["p_data_stable_while_stalled"]
    elif "invalid apb addresses" in intent:
        sva = SVA_TEMPLATES["p_invalid_address_behavior"]
    elif "zero-wait-state" in intent or "pready" in intent:
        sva = SVA_TEMPLATES["p_pready_response_valid"]
    elif "reset" in intent and "clear" in intent and "register" in intent:
        sva = SVA_TEMPLATES["p_reset_clears_registers"]
    elif "input handshake" in intent:
        sva = SVA_TEMPLATES["p_capture_on_input_fire"]
    else:
        reset_expr = f"disable iff ({reset})"
        if reset.endswith("n"):
            reset_expr = f"disable iff (!{reset})"
        sva = f"{property_id}: assert property (@(posedge {clock}) {reset_expr} 1'b1);"

    return {
        "property_id": property_id,
        "sva": sva,
        "explanation": "Direct baseline generated from property intent only.",
    }


def build_prompt(case: dict[str, object]) -> str:
    payload = {
        "design_id": case.get("design_id"),
        "clock": case.get("clock"),
        "reset": case.get("reset"),
        "signals": case.get("signals", []),
        "intent": case.get("intent"),
    }
    return (
        "Generate one SystemVerilog assertion from RTL signal names and natural-language intent. "
        "Return JSON with property_id, sva, and explanation. Do not invent signals.\n\n"
        + json.dumps(payload, indent=2)
    )


def normalize_output(case: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    return {
        "property_id": str(output.get("property_id") or case.get("property_id", "generated_property")),
        "sva": str(output.get("sva", "")).strip() or direct_fallback(case)["sva"],
        "explanation": str(output.get("explanation", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    args = parser.parse_args()
    data = json.loads(args.case.read_text())
    if isinstance(data, list):
        if not data:
            raise ValueError("case list is empty")
        case = data[0]
    elif isinstance(data, dict):
        case = data
    else:
        raise ValueError("case must be a JSON object or non-empty array")
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(case) + "\n")
    print(json.dumps(generate_direct(case, use_llm=args.llm, llm_command=args.llm_command), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
