#!/usr/bin/env python3
"""SVA generation agent with pluggable LLM backend and deterministic fallback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from copilot.llm_client import call_llm_json, llm_configured
from copilot.sva_library import SVA_TEMPLATES


def generate(
    context: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(build_prompt(context), llm_command)
            return normalize_output(context, response.json_object)
        except Exception as exc:  # noqa: BLE001 - fallback is intentional for demos.
            fallback = structured_fallback(context)
            fallback["llm_error"] = str(exc)
            return fallback
    return structured_fallback(context)


def structured_fallback(context: dict[str, object]) -> dict[str, object]:
    property_id = get_property_id(context)
    sva = SVA_TEMPLATES.get(property_id) or synthesize_simple_sva(context)
    return {
        "property_id": property_id or "generated_property",
        "sva": sva,
        "explanation": "Generated from structured property intent and known local signal context.",
    }


def synthesize_simple_sva(context: dict[str, object]) -> str:
    property_id = get_property_id(context) or "generated_property"
    clock = str(context.get("clock", "clk"))
    reset = str(context.get("reset", "rst"))
    signals = context.get("signals", [])
    if not isinstance(signals, list):
        signals = []
    signal = str(signals[-1]) if signals else "condition"
    reset_expr = f"disable iff ({reset})"
    if reset.endswith("n"):
        reset_expr = f"disable iff (!{reset})"
    return f"{property_id}: assert property (@(posedge {clock}) {reset_expr} {signal});"


def build_prompt(context: dict[str, object]) -> str:
    payload = sanitized_context(context)
    return (
        "You are JasperLoop-DV in SVA generation mode. "
        "Generate one SystemVerilog assertion from the property intent and structured RTL context. "
        "Return JSON with property_id, sva, and explanation. Do not invent signals.\n\n"
        + json.dumps(payload, indent=2)
    )


def sanitized_context(context: dict[str, object]) -> dict[str, object]:
    clone = dict(context)
    clone.pop("reference_sva", None)
    clone.pop("gold_label", None)
    return clone


def normalize_output(context: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    property_id = str(output.get("property_id") or get_property_id(context) or "generated_property")
    sva = str(output.get("sva", "")).strip()
    if not sva:
        sva = structured_fallback(context)["sva"]
    return {
        "property_id": property_id,
        "sva": sva,
        "explanation": str(output.get("explanation", "")),
    }


def get_property_id(context: dict[str, object]) -> str:
    if context.get("property_id"):
        return str(context["property_id"])
    failing_property = context.get("failing_property")
    if isinstance(failing_property, dict) and failing_property.get("property_id"):
        return str(failing_property["property_id"])
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("context", type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    data = json.loads(args.context.read_text())
    if isinstance(data, list):
        if not data:
            raise ValueError("context list is empty")
        context = data[0]
    elif isinstance(data, dict):
        context = data
    else:
        raise ValueError("context must be a JSON object or non-empty array")

    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(context) + "\n")
    output = generate(context, use_llm=args.llm, llm_command=args.llm_command)
    text = json.dumps(output, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
