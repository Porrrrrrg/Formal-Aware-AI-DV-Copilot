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
        key = (property_id, status)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "property_id": property_id,
                "status": status,
                "engine": "jaspergold",
                "bound": int(bound_match.group("bound")) if bound_match else None,
                "result_file": str(path),
                "line": line_no,
                "raw_line": line.strip(),
            }
        )

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = {"properties": parse_report(args.report)}
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
