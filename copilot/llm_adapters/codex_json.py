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
        "--ask-for-approval",
        "never",
        "--sandbox",
        "read-only",
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
        sys.stderr.write(completed.stderr)
        return completed.returncode

    sys.stdout.write(output_path.read_text().strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
