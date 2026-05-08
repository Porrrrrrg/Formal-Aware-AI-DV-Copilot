#!/usr/bin/env python3
"""Parse a simple JasperGold counterexample trace into cycle-indexed events."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CYCLE_RE = re.compile(r"\b(?:cycle|time|step)\s*(?P<cycle>\d+)\b", re.IGNORECASE)
ASSIGN_RE = re.compile(r"\b(?P<signal>[A-Za-z_][A-Za-z0-9_$]*)\s*=\s*(?P<value>[A-Za-z0-9_'bxzBXZ]+)")


def parse_trace(path: Path) -> dict[str, object]:
    cycles: dict[int, dict[str, str]] = {}
    raw_events: list[str] = []
    current_cycle: int | None = None

    for line in path.read_text(errors="ignore").splitlines():
        cycle_match = CYCLE_RE.search(line)
        if cycle_match:
            current_cycle = int(cycle_match.group("cycle"))
            cycles.setdefault(current_cycle, {})

        assigns = ASSIGN_RE.findall(line)
        if assigns and current_cycle is not None:
            cycles.setdefault(current_cycle, {})
            for signal, value in assigns:
                cycles[current_cycle][signal] = value
            raw_events.append(line.strip())

    events = [
        {
            "cycle": cycle,
            "signals": signals,
        }
        for cycle, signals in sorted(cycles.items())
    ]

    return {
        "trace_file": str(path),
        "events": events,
        "raw_events": raw_events[:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = parse_trace(args.trace)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
