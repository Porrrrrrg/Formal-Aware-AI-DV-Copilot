#!/usr/bin/env python3
"""Adapter that lets `JASPERLOOP_LLM_CMD` call Codex non-interactively.

The adapter reads a JasperLoop prompt from stdin, asks Codex to return only a
JSON object, and writes the final Codex message to stdout.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--cd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    prompt = sys.stdin.read()
    wrapped = (
        "Return only one valid JSON object. Do not include Markdown fences, prose, or file edits.\n\n"
        + prompt
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as output_file:
        output_path = Path(output_file.name)

    cmd = [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--cd",
        str(args.cd),
        "--output-last-message",
        str(output_path),
    ]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.schema:
        cmd.extend(["--output-schema", str(args.schema)])
    cmd.append("-")

    completed = subprocess.run(
        cmd,
        input=wrapped,
        text=True,
        capture_output=True,
        check=False,
        timeout=args.timeout,
    )
    if completed.returncode != 0:
        sys.stderr.write(sanitize_error(completed.stderr))
        return completed.returncode

    sys.stdout.write(output_path.read_text().strip())
    return 0


def sanitize_error(stderr: str, max_lines: int = 24, max_chars: int = 4000) -> str:
    """Keep actionable Codex CLI errors without embedding long HTML challenge pages."""
    lines = []
    skipping_html = False
    omitted_html = False
    for raw_line in stderr.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if "<html" in lower or "<!doctype html" in lower:
            skipping_html = True
            omitted_html = True
            continue
        if skipping_html:
            if "</html>" in lower:
                skipping_html = False
            continue
        if not line:
            continue
        if any(
            token in lower
            for token in (
                "error",
                "warn",
                "usage limit",
                "auth",
                "forbidden",
                "codex",
                "openai",
            )
        ):
            lines.append(line)
    if omitted_html:
        lines.insert(0, "[omitted HTML response from Codex CLI stderr]")
    if not lines:
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    usage_lines = unique_lines([line for line in lines if "usage limit" in line.lower()])
    if usage_lines:
        lines = usage_lines
    text = "\n".join(lines[-max_lines:])
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text + ("\n" if text else "")


def unique_lines(lines: list[str]) -> list[str]:
    seen = set()
    unique = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


if __name__ == "__main__":
    raise SystemExit(main())
