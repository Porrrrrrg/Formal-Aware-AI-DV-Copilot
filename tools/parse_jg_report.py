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
    "uncovered": "uncovered",
    "not covered": "uncovered",
    "cover failed": "uncovered",
    "unhit": "uncovered",
    "unreachable": "unreachable",
    "vacuous": "vacuous",
    "syntax error": "syntax_error",
    "syntax-error": "syntax_error",
    "parse error": "syntax_error",
    "elaboration error": "syntax_error",
}

PROPERTY_TOKEN_RE = re.compile(r"\b(?P<name>(?:p_|a_|cov_|assert_)[A-Za-z0-9_$.\[\]:-]+)\b")
STATUS_RE = re.compile(
    r"\b(?P<status>"
    r"syntax\s*[- ]\s*error|parse\s+error|elaboration\s+error|"
    r"not\s+covered|cover\s+failed|uncovered|unhit|"
    r"falsified|failed|fail|cex|"
    r"undetermined|inconclusive|unknown|"
    r"vacuous|unreachable|covered|proven|passed|pass"
    r")\b",
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


def normalize_status(raw_status: str) -> str:
    key = re.sub(r"\s+", " ", raw_status.strip().lower().replace("-", " "))
    if key == "syntax error":
        return "syntax_error"
    return STATUS_MAP.get(key, STATUS_MAP.get(raw_status.lower(), "undetermined"))


def parse_report(path: Path) -> list[dict[str, object]]:
    results_by_property: dict[str, dict[str, object]] = {}

    for line_no, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        parsed = parse_status_line(line, line_no, path)
        if parsed is None:
            continue
        results_by_property[str(parsed["property_id"])] = parsed

    return list(results_by_property.values())


def parse_report_payload(path: Path) -> dict[str, object]:
    """Parse a report and include parser errors for callers that need provenance."""

    try:
        properties = parse_report(path)
    except OSError as exc:
        return {
            "summary": summarize_properties([]),
            "properties": [],
            "parser_errors": [
                {
                    "kind": "report_read_error",
                    "message": str(exc),
                    "result_file": str(path),
                }
            ],
        }
    return {
        "summary": summarize_properties(properties),
        "properties": properties,
        "parser_errors": parser_warnings(path, properties),
    }


def parse_status_line(line: str, line_no: int, path: Path) -> dict[str, object] | None:
    property_match = PROPERTY_TOKEN_RE.search(line)
    status_match = STATUS_RE.search(line)
    if not property_match or not status_match:
        return None

    raw_status = status_match.group("status")
    status = normalize_status(raw_status)
    bound_match = BOUND_RE.search(line)
    proof_engine, table_bound = parse_table_metadata(line, raw_status)
    return {
        "property_id": property_match.group("name"),
        "status": status,
        "engine": "jaspergold",
        "proof_engine": proof_engine,
        "bound": int(bound_match.group("bound")) if bound_match else table_bound,
        "result_file": str(path),
        "line": line_no,
        "raw_line": line.strip(),
    }


def parser_warnings(path: Path, properties: list[dict[str, object]]) -> list[dict[str, object]]:
    if properties:
        return []
    text = path.read_text(errors="ignore") if path.exists() else ""
    suspicious = [
        line.strip()
        for line in text.splitlines()
        if any(token in line.lower() for token in ["error", "failed", "vacuous", "uncovered"])
    ]
    if not suspicious:
        return []
    return [
        {
            "kind": "unparsed_status_lines",
            "message": "Report contained status-like text but no property rows were parsed.",
            "result_file": str(path),
            "examples": suspicious[:5],
        }
    ]


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
        "uncovered_properties": by_status.get("uncovered", []),
        "unreachable_properties": by_status.get("unreachable", []),
        "undetermined_properties": by_status.get("undetermined", []),
        "vacuous_properties": by_status.get("vacuous", []),
        "syntax_error_properties": by_status.get("syntax_error", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = parse_report_payload(args.report)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
