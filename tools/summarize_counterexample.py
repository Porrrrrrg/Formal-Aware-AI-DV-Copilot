#!/usr/bin/env python3
"""Summarize parsed counterexample traces for evidence packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(
    trace: dict[str, object],
    property_id: str | None = None,
    signal_roles: dict[str, str] | None = None,
) -> dict[str, object]:
    signal_roles = signal_roles or {}
    events = trace.get("events", [])
    if not isinstance(events, list):
        events = []

    changed_signals: set[str] = set()
    observed_values: dict[str, set[str]] = {}
    previous: dict[str, str] = {}
    rendered: list[str] = []
    semantic_rendered: list[str] = []
    snapshots: list[dict[str, str]] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        cycle = event.get("cycle")
        signals = event.get("signals", {})
        if not isinstance(signals, dict):
            continue
        snapshot = {str(signal): str(value) for signal, value in signals.items()}
        snapshots.append(snapshot)
        changes = []
        semantic_changes = []
        for signal, value in sorted(signals.items()):
            signal = str(signal)
            value = str(value)
            if previous.get(signal) != value:
                changed_signals.add(signal)
                observed_values.setdefault(signal, set()).add(value)
                changes.append(f"{signal}={value}")
                role = signal_roles.get(signal)
                if role:
                    semantic_changes.append(f"{signal} ({role})={value}")
                else:
                    semantic_changes.append(f"{signal}={value}")
            previous[signal] = value
        if changes:
            rendered.append(f"cycle {cycle}: " + ", ".join(changes))
            semantic_rendered.append(f"cycle {cycle}: " + ", ".join(semantic_changes))

    fail_cycle = events[-1].get("cycle") if events and isinstance(events[-1], dict) else None
    suspicious = infer_suspicious_observation(snapshots, signal_roles, property_id)

    return {
        "fail_cycle": fail_cycle,
        "events": rendered[:20],
        "semantic_events": semantic_rendered[:20],
        "first_suspicious_observation": suspicious,
        "changed_signals": sorted(changed_signals),
        "observed_signal_roles": build_observed_signal_roles(observed_values, signal_roles),
    }


def build_observed_signal_roles(
    observed_values: dict[str, set[str]],
    signal_roles: dict[str, str],
) -> list[dict[str, object]]:
    rows = []
    for signal in sorted(observed_values):
        role = signal_roles.get(signal)
        if not role:
            continue
        rows.append(
            {
                "signal": signal,
                "role": role,
                "observed_values": sorted(observed_values[signal]),
            }
        )
    return rows


def infer_suspicious_observation(
    snapshots: list[dict[str, str]],
    signal_roles: dict[str, str],
    property_id: str | None,
) -> str:
    for snapshot in snapshots:
        if reset_is_active(snapshot):
            continue
        high_requests = high_signals_with_role(snapshot, signal_roles, "request")
        high_grants = high_signals_with_role(snapshot, signal_roles, "grant")
        if len(high_requests) >= 2 and len(high_grants) >= 2:
            return (
                "Multiple grant outputs are asserted while multiple requests are active: "
                + ", ".join([f"{name}=1" for name in high_requests + high_grants])
                + "."
            )

    if property_id:
        return f"Trace reaches the failing condition for {property_id}; inspect semantic_events for the signal-role sequence."
    return "Trace reaches a failing property condition; inspect semantic_events for the signal-role sequence."


def high_signals_with_role(
    snapshot: dict[str, str],
    signal_roles: dict[str, str],
    role_keyword: str,
) -> list[str]:
    matches = []
    for signal, role in signal_roles.items():
        if role_keyword not in role.lower():
            continue
        if is_truthy(snapshot.get(signal)):
            matches.append(signal)
    return sorted(matches)


def is_truthy(value: object) -> bool:
    if value is None:
        return False
    return str(value).lower() in {"1", "1'b1", "true"}


def reset_is_active(snapshot: dict[str, str]) -> bool:
    if "rst" in snapshot and is_truthy(snapshot.get("rst")):
        return True
    if "presetn" in snapshot and not is_truthy(snapshot.get("presetn")):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("parsed_trace", type=Path)
    parser.add_argument("--property-id")
    parser.add_argument("--signal-role-map", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        from tools.manifest_utils import load_signal_role_map
    except ModuleNotFoundError:
        from manifest_utils import load_signal_role_map

    trace = json.loads(args.parsed_trace.read_text())
    payload = summarize(trace, args.property_id, load_signal_role_map(args.signal_role_map))
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
