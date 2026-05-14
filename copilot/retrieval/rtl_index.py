"""Lightweight RTL index for retrieval-assisted formal agents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "rtl-index-v1"
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_$]*\b")
MODULE_RE = re.compile(
    r"\bmodule\s+(?P<name>[A-Za-z_][A-Za-z0-9_$]*)\s*"
    r"(?:#\s*\((?P<params>.*?)\)\s*)?"
    r"\((?P<ports>.*?)\)\s*;\s*(?P<body>.*?)\bendmodule\b",
    re.DOTALL,
)
PORT_RE = re.compile(
    r"\b(?P<direction>input|output|inout)\b\s+"
    r"(?P<type>(?:logic|wire|reg|signed|unsigned|\s|\[[^\]]+\])*)\s*"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_$]*)",
    re.MULTILINE,
)
DECL_RE = re.compile(
    r"\b(?P<kind>logic|wire|reg)\b\s+"
    r"(?P<type>(?:signed|unsigned|\s|\[[^\]]+\])*)\s*"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_$]*)\s*(?:=|;|,)",
    re.MULTILINE,
)
ASSIGN_RE = re.compile(
    r"\bassign\s+(?P<lhs>[A-Za-z_][A-Za-z0-9_.$]*(?:\[[^\]]+\])?)\s*=\s*(?P<rhs>.*?);",
    re.DOTALL,
)
ALWAYS_RE = re.compile(r"\balways(?:_ff|_comb|_latch)?\b.*?(?=\n\s*always|\n\s*assign|\n\s*endmodule|\Z)", re.DOTALL)
INSTANCE_RE = re.compile(
    r"^\s*(?P<module>[A-Za-z_][A-Za-z0-9_$]*)\s*(?:#\s*\(.*?\)\s*)?"
    r"(?P<instance>[A-Za-z_][A-Za-z0-9_$]*)\s*\(",
    re.MULTILINE | re.DOTALL,
)
NON_INSTANCE_HEADS = {
    "if",
    "for",
    "while",
    "case",
    "module",
    "assign",
    "always",
    "input",
    "output",
    "logic",
    "wire",
    "reg",
}
SV_KEYWORDS = {
    "always",
    "always_comb",
    "always_ff",
    "always_latch",
    "assign",
    "begin",
    "case",
    "default",
    "else",
    "end",
    "endcase",
    "endmodule",
    "if",
    "input",
    "logic",
    "module",
    "negedge",
    "or",
    "output",
    "parameter",
    "posedge",
    "reg",
    "wire",
}


def build_rtl_index(paths: list[Path] | list[str], out_path: Path | None = None) -> dict[str, Any]:
    """Build a JSON-serializable RTL index.

    `pyslang`/`slang` can be integrated later; the default parser is pure Python
    and intentionally conservative so local CI never requires commercial tools.
    """

    index: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "files": [], "modules": {}}
    for path_like in paths:
        path = Path(path_like)
        if not path.exists():
            continue
        parsed = parse_rtl_file(path)
        index["files"].append({"path": str(path), "parser": parsed["parser"]})
        for module in parsed["modules"]:
            index["modules"][module["name"]] = module
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(index, indent=2) + "\n")
    return index


def parse_rtl_file(path: Path) -> dict[str, Any]:
    text = path.read_text(errors="ignore")
    stripped = strip_comments(text)
    modules = []
    for match in MODULE_RE.finditer(stripped):
        body = match.group("body")
        module_text = match.group(0)
        start_line = line_number(stripped, match.start())
        modules.append(
            {
                "name": match.group("name"),
                "path": str(path),
                "source_range": {"path": str(path), "start_line": start_line, "end_line": line_number(stripped, match.end())},
                "ports": extract_ports(match.group("ports"), body),
                "signals": extract_signals(body),
                "assigns": extract_assigns(body, path, start_line),
                "always_blocks": extract_always_blocks(module_text, path, start_line),
                "instances": extract_instances(body, path, start_line),
            }
        )
    return {"parser": "regex_fallback", "modules": modules}


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def extract_ports(header: str, body: str) -> list[dict[str, Any]]:
    ports: dict[str, dict[str, Any]] = {}
    for source in [header, body]:
        for match in PORT_RE.finditer(source):
            ports[match.group("name")] = {
                "name": match.group("name"),
                "direction": match.group("direction"),
                "type": " ".join(match.group("type").split()),
            }
    if not ports:
        for name in [item.strip().split()[-1] for item in header.split(",") if item.strip()]:
            ports[name] = {"name": name, "direction": "unknown", "type": ""}
    return sorted(ports.values(), key=lambda item: item["name"])


def extract_signals(body: str) -> list[dict[str, Any]]:
    signals = {}
    for match in DECL_RE.finditer(body):
        signals[match.group("name")] = {
            "name": match.group("name"),
            "kind": match.group("kind"),
            "type": " ".join(match.group("type").split()),
        }
    return sorted(signals.values(), key=lambda item: item["name"])


def extract_assigns(body: str, path: Path, module_start_line: int) -> list[dict[str, Any]]:
    assigns = []
    for match in ASSIGN_RE.finditer(body):
        lhs = normalize_signal(match.group("lhs"))
        rhs = " ".join(match.group("rhs").split())
        assigns.append(
            {
                "lhs": lhs,
                "rhs": rhs,
                "dependencies": sorted(dependencies(rhs)),
                "source_range": source_range(path, body, match.start(), match.end(), module_start_line),
            }
        )
    return assigns


def extract_always_blocks(module_text: str, path: Path, module_start_line: int) -> list[dict[str, Any]]:
    blocks = []
    for index, match in enumerate(ALWAYS_RE.finditer(module_text)):
        text = match.group(0).strip()
        assigned = sorted({normalize_signal(item) for item in re.findall(r"\b([A-Za-z_][A-Za-z0-9_$]*)\s*(?:<=|=)", text)})
        blocks.append(
            {
                "id": f"always_{index}",
                "kind": first_word(text),
                "assigned_signals": assigned,
                "dependencies": sorted(dependencies(text) - set(assigned)),
                "text": text,
                "source_range": source_range(path, module_text, match.start(), match.end(), module_start_line),
            }
        )
    return blocks


def extract_instances(body: str, path: Path, module_start_line: int) -> list[dict[str, Any]]:
    instances = []
    for match in INSTANCE_RE.finditer(body):
        module = match.group("module")
        if module in NON_INSTANCE_HEADS:
            continue
        instances.append(
            {
                "module": module,
                "instance": match.group("instance"),
                "source_range": source_range(path, body, match.start(), match.end(), module_start_line),
            }
        )
    return instances


def source_range(path: Path, text: str, start: int, end: int, base_line: int) -> dict[str, Any]:
    return {
        "path": str(path),
        "start_line": base_line + line_number(text, start) - 1,
        "end_line": base_line + line_number(text, end) - 1,
    }


def first_word(text: str) -> str:
    match = IDENT_RE.search(text)
    return match.group(0) if match else "always"


def normalize_signal(signal: str) -> str:
    return signal.split("[", 1)[0].rsplit(".", 1)[-1]


def dependencies(text: str) -> set[str]:
    return {token for token in IDENT_RE.findall(text) if token not in SV_KEYWORDS and not token.isdigit()}


def search_signal(index: dict[str, Any], signal: str) -> list[dict[str, Any]]:
    matches = []
    for module in index.get("modules", {}).values():
        module_name = module.get("name")
        for port in module.get("ports", []):
            if port.get("name") == signal:
                matches.append({"module": module_name, "kind": "port", **port})
        for declared in module.get("signals", []):
            if declared.get("name") == signal:
                matches.append({"module": module_name, "kind": "signal", **declared})
        logic = get_signal_logic(index, signal, module_name=module_name)
        if logic.get("drivers"):
            matches.append({"module": module_name, "kind": "logic", **logic})
    return matches


def get_module_interface(index: dict[str, Any], module_name: str) -> dict[str, Any]:
    module = index.get("modules", {}).get(module_name, {})
    return {
        "module": module_name,
        "ports": module.get("ports", []),
        "source_range": module.get("source_range"),
    }


def get_signal_logic(
    index: dict[str, Any],
    signal: str,
    module_name: str | None = None,
) -> dict[str, Any]:
    modules = index.get("modules", {})
    selected = [modules[module_name]] if module_name and module_name in modules else modules.values()
    drivers = []
    uses = []
    for module in selected:
        for assign in module.get("assigns", []):
            if assign.get("lhs") == signal:
                drivers.append({"kind": "assign", "module": module.get("name"), **assign})
            if signal in assign.get("dependencies", []):
                uses.append({"kind": "assign", "module": module.get("name"), **assign})
        for block in module.get("always_blocks", []):
            if signal in block.get("assigned_signals", []):
                drivers.append({"kind": block.get("kind", "always"), "module": module.get("name"), **block})
            if signal in block.get("dependencies", []):
                uses.append({"kind": block.get("kind", "always"), "module": module.get("name"), **block})
    return {"signal": signal, "drivers": drivers, "uses": uses}


def get_hierarchy(index: dict[str, Any]) -> dict[str, Any]:
    return {
        module_name: module.get("instances", [])
        for module_name, module in sorted(index.get("modules", {}).items())
    }


def get_clock_reset_candidates(index: dict[str, Any]) -> dict[str, list[str]]:
    names = set()
    for module in index.get("modules", {}).values():
        names.update(port.get("name") for port in module.get("ports", []))
        names.update(signal.get("name") for signal in module.get("signals", []))
    strings = sorted(str(name) for name in names if name)
    return {
        "clocks": [name for name in strings if name.lower() in {"clk", "clock"} or "clk" in name.lower()],
        "resets": [
            name
            for name in strings
            if name.lower() in {"rst", "reset", "reset_"} or "rst" in name.lower() or "reset" in name.lower()
        ],
    }
