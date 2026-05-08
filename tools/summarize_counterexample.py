#!/usr/bin/env python3
"""Summarize parsed counterexample traces for evidence packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(trace: dict[str, object], property_id: str | None = None) -> dict[str, object]:
    events = trace.get("events", [])
    if not isinstance(events, list):
        events = []

    changed_signals: set[str] = set()
    previous: dict[str, str] = {}
    rendered: list[str] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        cycle = event.get("cycle")
        signals = event.get("signals", {})
        if not isinstance(signals, dict):
            continue
        changes = []
        for signal, value in sorted(signals.items()):
            value = str(value)
            if previous.get(signal) != value:
                changed_signals.add(signal)
                changes.append(f"{signal}={value}")
            previous[signal] = value
        if changes:
            rendered.append(f"cycle {cycle}: " + ", ".join(changes))

    fail_cycle = events[-1].get("cycle") if events and isinstance(events[-1], dict) else None
    suspicious = "Last trace cycle reaches the failing property condition."
    if property_id:
        suspicious = f"Last trace cycle reaches the failing condition for {property_id}."

    return {
        "fail_cycle": fail_cycle,
        "events": rendered[:20],
        "first_suspicious_observation": suspicious,
        "changed_signals": sorted(changed_signals),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("parsed_trace", type=Path)
    parser.add_argument("--property-id")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    trace = json.loads(args.parsed_trace.read_text())
    payload = summarize(trace, args.property_id)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
