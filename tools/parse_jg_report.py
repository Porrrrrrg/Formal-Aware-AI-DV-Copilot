#!/usr/bin/env python3
"""Parse JasperGold-style property status reports into JSON.

The parser is intentionally conservative and text-based because report formats vary
between JasperGold versions and local TCL flows. It recognizes common status words
and property names from lines such as:

    p_mutex : falsified bound=3
    Property p_reset_empty Proven
    assert_p_data_stable inconclusive
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STATUS_MAP = {
    "proven": "proven",
    "pass": "proven",
    "passed": "proven",
    "cex": "falsified",
    "fail": "falsified",
    "failed": "falsified",
    "falsified": "falsified",
    "undetermined": "undetermined",
    "inconclusive": "undetermined",
    "unknown": "undetermined",
    "covered": "covered",
    "unreachable": "unreachable",
    "vacuous": "vacuous",
}

PROPERTY_RE = re.compile(
    r"(?P<name>\b(?:p_|a_|cov_|assert_)[A-Za-z0-9_$.\[\]:-]+)\b.*?"
    r"(?P<status>proven|passed|pass|falsified|failed|fail|cex|undetermined|"
    r"inconclusive|unknown|covered|unreachable|vacuous)\b",
    re.IGNORECASE,
)
BOUND_RE = re.compile(r"\b(?:bound|depth|cycle)\s*[=:]\s*(?P<bound>\d+)\b", re.IGNORECASE)


def parse_table_metadata(line: str, status: str) -> tuple[str | None, int | None]:
    """Extract proof engine and bound from JasperGold table rows."""
    after_status = line.split(status, 1)[-1].split()
    if len(after_status) < 2:
        return None, None
    proof_engine = after_status[0]
    bound_token = after_status[1]
    bound = int(bound_token) if bound_token.isdigit() else None
    return proof_engine, bound


def parse_report(path: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for line_no, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        match = PROPERTY_RE.search(line)
        if not match:
            continue
        property_id = match.group("name")
        raw_status = match.group("status").lower()
        status = STATUS_MAP[raw_status]
        bound_match = BOUND_RE.search(line)
        proof_engine, table_bound = parse_table_metadata(line, match.group("status"))
        key = (property_id, status)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "property_id": property_id,
                "status": status,
                "engine": "jaspergold",
                "proof_engine": proof_engine,
                "bound": int(bound_match.group("bound")) if bound_match else table_bound,
                "result_file": str(path),
                "line": line_no,
                "raw_line": line.strip(),
            }
        )

    return results


def summarize_properties(results: list[dict[str, object]]) -> dict[str, object]:
    counts: dict[str, int] = {}
    by_status: dict[str, list[str]] = {}
    for result in results:
        status = str(result.get("status", "unknown"))
        property_id = str(result.get("property_id", "unknown"))
        counts[status] = counts.get(status, 0) + 1
        by_status.setdefault(status, []).append(property_id)
    return {
        "counts_by_status": counts,
        "falsified_properties": by_status.get("falsified", []),
        "proven_properties": by_status.get("proven", []),
        "covered_properties": by_status.get("covered", []),
        "unreachable_properties": by_status.get("unreachable", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    properties = parse_report(args.report)
    payload = {"summary": summarize_properties(properties), "properties": properties}
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
