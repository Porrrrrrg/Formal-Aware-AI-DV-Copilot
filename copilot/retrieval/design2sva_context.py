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
ASSIGNMENT_RE = re.compile(
    r"\b(?P<lhs>[A-Za-z_][A-Za-z0-9_.$]*(?:\[[^\]]+\])?)\s*"
    r"(?P<op><=|(?<![=!<>])=(?!=))\s*(?P<rhs>.*?);",
    re.DOTALL,
)
IF_BEGIN_RE = re.compile(r"\b(?:if|else\s+if)\s*\((?P<condition>.*?)\)\s*begin", re.DOTALL)
CASE_BLOCK_RE = re.compile(
    r"\b(?:unique\s+|priority\s+)?case\s*\((?P<selector>.*?)\)"
    r"(?P<body>.*?)\bendcase\b",
    re.DOTALL,
)
CASE_ITEM_RE = re.compile(
    r"(?P<label>(?:\d+'[bhd][0-9A-Fa-f_xXzZ?]+)|default)\s*:",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Design2SVAContextOptions:
    module_name: str | None = None
    focus_signals: tuple[str, ...] = ()
    property_intent: str = ""
    visible_signal_budget: int = 24
    max_assigns: int = 12
    max_always_blocks: int = 8
    max_logic_entries_per_signal: int = 4
    max_derived_conditions: int = 16
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
    reset_behavior = derive_reset_behavior(module, clock_reset, options, limitations)
    handshake_fire_conditions = derive_handshake_fire_conditions(
        module,
        visible_signals,
        options,
        limitations,
    )
    state_update_conditions = derive_state_update_conditions(
        module,
        reset_behavior,
        visible_signals,
        options,
        limitations,
    )

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
        "reset_behavior": reset_behavior,
        "handshake_fire_conditions": handshake_fire_conditions,
        "state_update_conditions": state_update_conditions,
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


def derive_reset_behavior(
    module: dict[str, Any],
    clock_reset: dict[str, list[str]],
    options: Design2SVAContextOptions,
    limitations: list[str],
) -> dict[str, Any]:
    resets = sorted({str(name) for name in clock_reset.get("resets", []) if name})
    known = module_signal_names(module)
    branches = []
    for block in module.get("always_blocks", []):
        text = str(block.get("text", ""))
        if not text:
            continue
        for reset in resets:
            for branch in find_reset_branches(text, reset):
                assignments = assignment_values(
                    branch["body"],
                    known,
                    options.max_derived_conditions,
                )
                branches.append(
                    {
                        "reset": reset,
                        "active_condition": branch["condition"],
                        "polarity": reset_polarity(reset, branch["condition"]),
                        "always_block": str(block.get("id", "")),
                        "assigned_values": assignments,
                        "affected_signals": sorted({item["signal"] for item in assignments}),
                        "source_range": block.get("source_range"),
                    }
                )
    if len(branches) > options.max_derived_conditions:
        limitations.append("Reset behavior context was truncated by max_derived_conditions.")
    return {
        "reset_candidates": resets,
        "observed_reset_branches": branches[: options.max_derived_conditions],
    }


def find_reset_branches(text: str, reset: str) -> list[dict[str, str]]:
    pattern = re.compile(
        rf"\bif\s*\(\s*(?P<condition>[^)]*\b{re.escape(reset)}\b[^)]*)\)\s*begin"
        rf"(?P<body>.*?)(?=\n\s*end\s+else|\n\s*end\s*$)",
        re.DOTALL | re.MULTILINE,
    )
    return [
        {
            "condition": normalize_expr(match.group("condition")),
            "body": match.group("body"),
        }
        for match in pattern.finditer(text)
    ]


def reset_polarity(reset: str, condition: str) -> str:
    compact = condition.replace(" ", "")
    if (
        compact.startswith(f"!{reset}")
        or f"{reset}==1'b0" in compact
        or f"1'b0=={reset}" in compact
    ):
        return "active_low"
    if compact == reset or f"{reset}==1'b1" in compact or f"1'b1=={reset}" in compact:
        return "active_high"
    return "unknown"


def derive_handshake_fire_conditions(
    module: dict[str, Any],
    visible_signals: list[str],
    options: Design2SVAContextOptions,
    limitations: list[str],
) -> list[dict[str, Any]]:
    records = []
    for assign in module.get("assigns", []):
        lhs = str(assign.get("lhs", ""))
        rhs = normalize_expr(assign.get("rhs", ""))
        deps = sorted(str(dep) for dep in assign.get("dependencies", []))
        if is_handshake_condition(lhs, rhs, deps):
            records.append(
                {
                    "name": lhs,
                    "condition": rhs,
                    "dependencies": deps,
                    "source": "assign",
                    "source_range": assign.get("source_range"),
                }
            )
    records.extend(interface_valid_ready_conditions(module, visible_signals))
    records = dedupe_records(records, ("condition",))
    if len(records) > options.max_derived_conditions:
        limitations.append(
            "Handshake fire condition context was truncated by max_derived_conditions."
        )
    return records[: options.max_derived_conditions]


def is_handshake_condition(lhs: str, rhs: str, deps: list[str]) -> bool:
    names = [lhs, *deps]
    lowered = {name.lower() for name in names}
    if any("fire" in name.lower() or "handshake" in name.lower() for name in names):
        return "&&" in rhs or len(deps) >= 2
    if lhs.lower() in {"access", "transfer", "xfer"} and len(deps) >= 2:
        return True
    return {"psel", "penable"} <= lowered


def interface_valid_ready_conditions(
    module: dict[str, Any],
    visible_signals: list[str],
) -> list[dict[str, Any]]:
    known = module_signal_names(module)
    visible = set(visible_signals)
    records = []
    for valid in sorted(name for name in known if name.endswith("_valid")):
        prefix = valid[: -len("_valid")]
        ready = f"{prefix}_ready"
        if ready not in known:
            continue
        fire_signal = f"{prefix}_fire" if f"{prefix}_fire" in known else None
        records.append(
            {
                "name": fire_signal or f"interface_{prefix}_valid_ready",
                "condition": f"{valid} && {ready}",
                "dependencies": [valid, ready],
                "source": "interface_valid_ready_pair",
                "visible": valid in visible and ready in visible,
            }
        )
    return records


def derive_state_update_conditions(
    module: dict[str, Any],
    reset_behavior: dict[str, Any],
    visible_signals: list[str],
    options: Design2SVAContextOptions,
    limitations: list[str],
) -> list[dict[str, Any]]:
    known = module_signal_names(module)
    visible = set(visible_signals)
    reset_conditions = reset_conditions_by_block(reset_behavior)
    reset_values = reset_values_by_block(reset_behavior)
    records = []
    for block in module.get("always_blocks", []):
        if not is_sequential_block(block):
            continue
        block_id = str(block.get("id", ""))
        assigned = sorted(
            assigned_signals_from_text(str(block.get("text", "")), known),
            key=lambda signal: (signal not in visible, signal),
        )
        if not assigned:
            continue
        conditions = non_reset_conditions(
            str(block.get("text", "")),
            reset_conditions.get(block_id, set()),
        )
        values = reset_values.get(block_id, {})
        records.append(
            {
                "always_block": block_id,
                "assigned_signals": assigned,
                "conditions": conditions,
                "reset_values": {
                    signal: values[signal]
                    for signal in assigned
                    if signal in values
                },
                "source_range": block.get("source_range"),
                "precision": "block_level_conservative",
            }
        )
    if len(records) > options.max_derived_conditions:
        limitations.append(
            "State-update condition context was truncated by max_derived_conditions."
        )
    return records[: options.max_derived_conditions]


def reset_conditions_by_block(reset_behavior: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for branch in reset_behavior.get("observed_reset_branches", []):
        if not isinstance(branch, dict):
            continue
        block_id = str(branch.get("always_block", ""))
        condition = str(branch.get("active_condition", ""))
        result.setdefault(block_id, set()).add(condition)
    return result


def reset_values_by_block(reset_behavior: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for branch in reset_behavior.get("observed_reset_branches", []):
        if not isinstance(branch, dict):
            continue
        block_id = str(branch.get("always_block", ""))
        values = result.setdefault(block_id, {})
        for assignment in branch.get("assigned_values", []):
            if isinstance(assignment, dict):
                values[str(assignment.get("signal", ""))] = str(assignment.get("value", ""))
    return result


def is_sequential_block(block: dict[str, Any]) -> bool:
    text = str(block.get("text", ""))
    kind = str(block.get("kind", ""))
    return kind == "always_ff" or "@(posedge" in text or "@(negedge" in text


def non_reset_conditions(text: str, reset_conditions: set[str]) -> list[str]:
    conditions = []
    for match in IF_BEGIN_RE.finditer(text):
        condition = normalize_expr(match.group("condition"))
        if condition in reset_conditions:
            continue
        conditions.append(condition)
    conditions.extend(case_update_conditions(text))
    return dedupe_list(conditions)


def case_update_conditions(text: str) -> list[str]:
    conditions = []
    for match in CASE_BLOCK_RE.finditer(text):
        selector = normalize_expr(match.group("selector"))
        for item in CASE_ITEM_RE.finditer(match.group("body")):
            label = normalize_expr(item.group("label"))
            if label == "default":
                conditions.append(f"{selector} default")
            else:
                conditions.append(f"{selector} == {label}")
    return conditions


def assignment_values(
    text: str,
    known_signals: set[str],
    limit: int,
) -> list[dict[str, str]]:
    records = []
    for match in ASSIGNMENT_RE.finditer(text):
        signal = normalize_signal_name(match.group("lhs"))
        if signal not in known_signals:
            continue
        records.append({"signal": signal, "value": normalize_expr(match.group("rhs"))})
    return records[: max(0, limit)]


def assigned_signals_from_text(text: str, known_signals: set[str]) -> set[str]:
    return {
        signal
        for signal in (
            normalize_signal_name(match.group("lhs"))
            for match in ASSIGNMENT_RE.finditer(text)
        )
        if signal in known_signals
    }


def normalize_signal_name(signal: str) -> str:
    return str(signal).split("[", 1)[0].rsplit(".", 1)[-1]


def normalize_expr(value: Any) -> str:
    return " ".join(str(value).strip().split())


def dedupe_list(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def dedupe_records(
    records: list[dict[str, Any]],
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for record in records:
        key = tuple(str(record.get(field, "")) for field in key_fields)
        if key in seen:
            continue
        result.append(record)
        seen.add(key)
    return result


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
