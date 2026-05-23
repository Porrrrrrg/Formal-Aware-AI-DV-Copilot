#!/usr/bin/env python3
"""Repository secret scanner used by CI.

The scanner intentionally reports only rule id, path, and line number. It never
prints the matched value, so CI logs do not leak the same string that caused a
finding.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Pattern

PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b")),
    ("openai-api-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*"
            r"['\"][A-Za-z0-9_./+=-]{24,}['\"]"
        ),
    ),
)

SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "artifacts",
    "dist",
}

SCANNED_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".sv",
    ".tcl",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

MAX_FILE_BYTES = 1_000_000


def repo_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_scannable_file(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    relative_parts = path.relative_to(root).parts
    if any(part in SKIP_PARTS for part in relative_parts):
        return False
    if path.suffix.lower() not in SCANNED_SUFFIXES:
        return False
    return path.stat().st_size <= MAX_FILE_BYTES


def scan_repository(root: Path) -> list[dict[str, object]]:
    root = root.resolve()
    findings: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not is_scannable_file(path, root):
            continue
        text = path.read_text(errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for rule_id, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "path": repo_relative(path, root),
                            "line": line_no,
                            "message": f"Potential {rule_id} in repository text",
                        }
                    )
    return findings


def build_sarif(findings: list[dict[str, object]]) -> dict[str, object]:
    rule_ids = sorted({str(finding["rule_id"]) for finding in findings} or {"no-findings"})
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "jasperloop-secret-scan",
                        "informationUri": "https://docs.github.com/code-security/secret-scanning",
                        "rules": [
                            {
                                "id": rule_id,
                                "shortDescription": {"text": rule_id},
                                "help": {
                                    "text": (
                                        "Remove hard-coded secrets and rotate exposed "
                                        "credentials."
                                    )
                                },
                            }
                            for rule_id in rule_ids
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": finding["rule_id"],
                        "level": "error",
                        "message": {"text": finding["message"]},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": finding["path"]},
                                    "region": {"startLine": finding["line"]},
                                }
                            }
                        ],
                    }
                    for finding in findings
                ],
            }
        ],
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repository text for hard-coded secrets.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("artifacts/security/secret-scan.json"),
    )
    parser.add_argument(
        "--sarif-out",
        type=Path,
        default=Path("artifacts/security/secret-scan.sarif"),
    )
    args = parser.parse_args(argv)

    findings = scan_repository(args.root)
    write_json(args.json_out, findings)
    write_json(args.sarif_out, build_sarif(findings))

    if findings:
        for finding in findings:
            print(
                (
                    f"{finding['path']}:{finding['line']}: "
                    f"{finding['message']} ({finding['rule_id']})"
                ),
                file=sys.stderr,
            )
        return 1

    print("No high-confidence secret patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
