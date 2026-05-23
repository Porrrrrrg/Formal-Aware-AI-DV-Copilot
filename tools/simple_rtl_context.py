#!/usr/bin/env python3
"""Extract lightweight RTL context for evidence packets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from copilot.retrieval.rtl_index import build_rtl_index
except ModuleNotFoundError:
    build_rtl_index = None

MODULE_RE = re.compile(r"\bmodule\s+(?P<name>[A-Za-z_][A-Za-z0-9_$]*)\s*(?P<header>.*?)\);", re.S)
PORT_RE = re.compile(
    r"\b(?P<dir>input|output|inout)\b\s*(?P<type>logic|wire|reg)?\s*"
    r"(?P<range>\[[^\]]+\])?\s*(?P<names>[A-Za-z0-9_$,\s]+)",
    re.S,
)


def extract_context(paths: list[Path], max_lines: int = 120) -> dict[str, object]:
    files = []
    modules = []
    ports = []

    for path in paths:
        text = path.read_text(errors="ignore")
        lines = text.splitlines()
        files.append(
            {
                "path": str(path),
                "excerpt": "\n".join(lines[:max_lines]),
            }
        )
        for module_match in MODULE_RE.finditer(text):
            modules.append(module_match.group("name"))
            header = module_match.group("header")
            for port_match in PORT_RE.finditer(header):
                names = [
                    name.strip()
                    for name in port_match.group("names").replace("\n", " ").split(",")
                    if name.strip()
                ]
                for name in names:
                    ports.append(
                        {
                            "name": name,
                            "direction": port_match.group("dir"),
                            "range": port_match.group("range"),
                            "file": str(path),
                        }
                    )

    context = {
        "files": files,
        "modules": sorted(set(modules)),
        "ports": ports,
    }
    if build_rtl_index is not None:
        context["rtl_index"] = build_rtl_index(paths)
    return context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rtl", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = extract_context(args.rtl)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
