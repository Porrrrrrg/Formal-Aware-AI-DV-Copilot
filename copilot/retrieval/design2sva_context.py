"""Bounded RTL context builder for Design2SVA tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copilot.retrieval.rtl_index import (
    build_rtl_index,
    get_clock_reset_candidates,
    get_hierarchy,
    get_module_interface,
    get_signal_logic,
)

SCHEMA_VERSION = "design2sva-context-v1"
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_$]*\b")


@dataclass(frozen=True)
class Design2SVAContextOptions:
    module_name: str | None = None
    focus_signals: tuple[str, ...] = ()
    property_intent: str = ""
    visible_signal_budget: int = 24
    max_assigns: int = 12
    max_always_blocks: int = 8
    max_logic_entries_per_signal: int = 4
    include_source_text: bool = True
    max_block_chars: int = 1200


def build_design2sva_context(
    rtl_paths: list[Path | str],
    options: Design2SVAContextOptions | None = None,
) -> dict[str, Any]:
    """Return structured, budgeted RTL context for SVA generation prompts."""

    options = options or Design2SVAContextOptions()
    index = build_rtl_index([Path(path) for path in rtl_paths])
    module = select_module(index, options.module_name)
    module_name = str(module["name"])
    clock_reset = get_clock_reset_candidates(index)
    limitations = parser_limitations(index)

    visible_signals, visible_budget = rank_visible_signals(module, clock_reset, options)
    if visible_budget["truncated"]:
        limitations.append(
            "Visible signal set was truncated by the Design2SVA context budget."
        )

    assigns = bounded_records(
        [
            assign
            for assign in module.get("assigns", [])
            if record_intersects(assign, visible_signals)
        ],
        options.max_assigns,
    )
    always_blocks = bounded_records(
        [
            trim_source_text(block, options)
            for block in module.get("always_blocks", [])
            if block_intersects(block, visible_signals)
        ],
        options.max_always_blocks,
    )
    if len(assigns["records"]) < len(
        [
            assign
            for assign in module.get("assigns", [])
            if record_intersects(assign, visible_signals)
        ]
    ):
        limitations.append("Assign context was truncated by max_assigns.")
    if len(always_blocks["records"]) < len(
        [
            block
            for block in module.get("always_blocks", [])
            if block_intersects(block, visible_signals)
        ]
    ):
        limitations.append("Always-block context was truncated by max_always_blocks.")

    signal_logic = {
        signal: bounded_signal_logic(
            get_signal_logic(index, signal, module_name=module_name),
            options,
            limitations,
        )
        for signal in visible_signals
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "module": module_name,
        "source_files": [str(path) for path in rtl_paths],
        "interface": get_module_interface(index, module_name),
        "clock_reset_candidates": clock_reset,
        "hierarchy": {module_name: get_hierarchy(index).get(module_name, [])},
        "visible_signals": visible_signals,
        "signal_budget": visible_budget,
        "assigns": assigns["records"],
        "always_blocks": always_blocks["records"],
        "signal_logic": signal_logic,
        "limitations": sorted(set(limitations)),
    }


def select_module(index: dict[str, Any], requested: str | None) -> dict[str, Any]:
    modules = index.get("modules", {})
    if requested:
        if requested not in modules:
            raise ValueError(f"Requested module {requested!r} was not found in RTL index")
        return modules[requested]
    if len(modules) == 1:
        return next(iter(modules.values()))
    if not modules:
        raise ValueError("No modules were parsed from RTL paths")
    choices = ", ".join(sorted(modules))
    raise ValueError(f"Multiple modules parsed; pass module_name. Choices: {choices}")


def parser_limitations(index: dict[str, Any]) -> list[str]:
    limitations = []
    parsers = {str(file.get("parser")) for file in index.get("files", [])}
    if "regex_fallback" in parsers:
        limitations.append(
            "RTL context was extracted by the lightweight regex fallback parser."
        )
    return limitations


def rank_visible_signals(
    module: dict[str, Any],
    clock_reset: dict[str, list[str]],
    options: Design2SVAContextOptions,
) -> tuple[list[str], dict[str, Any]]:
    known = module_signal_names(module)
    ranked: list[str] = []
    add_ranked(ranked, options.focus_signals, known)
    add_ranked(ranked, clock_reset.get("clocks", []), known)
    add_ranked(ranked, clock_reset.get("resets", []), known)
    add_ranked(ranked, intent_tokens(options.property_intent), known)
    add_ranked(ranked, [port["name"] for port in module.get("ports", [])], known)
    for assign in module.get("assigns", []):
        add_ranked(ranked, [assign.get("lhs", "")], known)
        add_ranked(ranked, assign.get("dependencies", []), known)
    for block in module.get("always_blocks", []):
        add_ranked(ranked, block.get("assigned_signals", []), known)
        add_ranked(ranked, block.get("dependencies", []), known)

    limit = max(1, options.visible_signal_budget)
    selected = ranked[:limit]
    return selected, {"limit": limit, "used": len(selected), "truncated": len(ranked) > limit}


def module_signal_names(module: dict[str, Any]) -> set[str]:
    names = {str(port.get("name")) for port in module.get("ports", []) if port.get("name")}
    names.update(
        str(signal.get("name")) for signal in module.get("signals", []) if signal.get("name")
    )
    return names


def add_ranked(target: list[str], candidates: Any, known: set[str]) -> None:
    for candidate in candidates if isinstance(candidates, list | tuple | set) else []:
        name = str(candidate)
        if name in known and name not in target:
            target.append(name)


def intent_tokens(intent: str) -> list[str]:
    return IDENT_RE.findall(intent)


def record_intersects(record: dict[str, Any], visible: list[str]) -> bool:
    visible_set = set(visible)
    lhs = str(record.get("lhs", ""))
    deps = {str(dep) for dep in record.get("dependencies", [])}
    return bool(visible_set & ({lhs} | deps))


def block_intersects(block: dict[str, Any], visible: list[str]) -> bool:
    visible_set = set(visible)
    assigned = {str(item) for item in block.get("assigned_signals", [])}
    deps = {str(dep) for dep in block.get("dependencies", [])}
    return bool(visible_set & (assigned | deps))


def trim_source_text(record: dict[str, Any], options: Design2SVAContextOptions) -> dict[str, Any]:
    trimmed = dict(record)
    text = str(trimmed.get("text", ""))
    if not options.include_source_text:
        trimmed.pop("text", None)
        return trimmed
    if len(text) > options.max_block_chars:
        trimmed["text"] = text[: options.max_block_chars] + "\n/* truncated */"
        trimmed["truncated"] = True
    return trimmed


def bounded_records(records: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    limit = max(0, limit)
    return {"records": records[:limit], "truncated": len(records) > limit}


def bounded_signal_logic(
    logic: dict[str, Any],
    options: Design2SVAContextOptions,
    limitations: list[str],
) -> dict[str, Any]:
    signal = str(logic.get("signal", ""))
    drivers = [
        trim_source_text(record, options)
        for record in logic.get("drivers", [])[: options.max_logic_entries_per_signal]
    ]
    uses = [
        trim_source_text(record, options)
        for record in logic.get("uses", [])[: options.max_logic_entries_per_signal]
    ]
    if len(logic.get("drivers", [])) > len(drivers) or len(logic.get("uses", [])) > len(uses):
        limitations.append(f"Signal logic for {signal} was truncated by context budget.")
    for driver in drivers:
        text = str(driver.get("text", ""))
        if signal and f"{signal} ==" in text:
            limitations.append(
                f"Driver extraction for {signal} may include equality-expression matches."
            )
    return {"signal": signal, "drivers": drivers, "uses": uses}
