#!/usr/bin/env python3
"""Adapter that lets `JASPERLOOP_LLM_CMD` call Codex non-interactively.

The adapter reads a JasperLoop prompt from stdin, asks Codex to return only a
JSON object, and writes the final Codex message to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
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
    parser.add_argument("--diagnose", action="store_true", help="Inspect the Codex executable and exit.")
    parser.add_argument("--print-command", action="store_true", help="Print the Codex command without sending a prompt.")
    parser.add_argument("--shell", action="store_true", help="Run Codex through the shell. Disabled by default.")
    args = parser.parse_args()

    if args.diagnose:
        print(json.dumps(diagnose_codex_executable(args.timeout), indent=2))
        return 0

    output_path = make_output_path()
    cmd = build_codex_command(args, output_path)
    if args.print_command:
        print(subprocess.list2cmdline(cmd))
        return 0

    prompt = sys.stdin.read()
    wrapped = (
        "Return only one valid JSON object. Do not include Markdown fences, prose, or file edits.\n\n"
        + prompt
    )

    run_command: list[str] | str = subprocess.list2cmdline(cmd) if args.shell else cmd
    try:
        completed = subprocess.run(
            run_command,
            input=wrapped,
            text=True,
            capture_output=True,
            check=False,
            timeout=args.timeout,
            shell=args.shell,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"command_timeout: Codex CLI invocation timed out after {args.timeout} seconds.\n")
        return 124
    except PermissionError as exc:
        sys.stderr.write(permission_error_message(exc))
        return 127
    except FileNotFoundError as exc:
        sys.stderr.write(f"missing_executable: {exc}\n")
        return 127
    except OSError as exc:
        if getattr(exc, "winerror", None) == 5:
            sys.stderr.write(permission_error_message(exc))
        else:
            sys.stderr.write(f"unknown_error: Codex CLI invocation failed: {exc}\n")
        return 127
    if completed.returncode != 0:
        sys.stderr.write(sanitize_error(completed.stderr))
        return completed.returncode

    text = output_path.read_text().strip()
    if not text:
        sys.stderr.write("empty_stdout: Codex CLI did not write a final JSON message.\n")
        return 1
    sys.stdout.write(text)
    return 0


def build_codex_command(args: argparse.Namespace, output_path: Path) -> list[str]:
    cmd = [
        resolve_codex_executable(),
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
    return cmd


def make_output_path() -> Path:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as output_file:
        return Path(output_file.name)


def resolve_codex_executable() -> str:
    override = os.environ.get("CODEX_BIN")
    if override:
        return override
    if sys.platform == "win32":
        return shutil.which("codex.exe") or shutil.which("codex") or "codex.exe"
    return shutil.which("codex") or "codex"


def diagnose_codex_executable(timeout_s: int = 5) -> dict[str, object]:
    executable = resolve_codex_executable()
    path = Path(executable)
    report: dict[str, object] = {
        "CODEX_BIN": os.environ.get("CODEX_BIN", ""),
        "resolved_executable": executable,
        "exists": path.exists(),
        "is_file": path.is_file(),
        "executable_access": os.access(path, os.X_OK) if path.exists() else False,
    }
    if not path.exists() or not path.is_file():
        report["status"] = "missing_executable"
        return report
    try:
        completed = subprocess.run(
            [executable, "--version"],
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        report["status"] = "command_timeout"
        return report
    except PermissionError as exc:
        report["status"] = "permission_denied"
        report["error"] = str(exc)
        return report
    except OSError as exc:
        report["status"] = "permission_denied" if getattr(exc, "winerror", None) == 5 else "unknown_error"
        report["error"] = str(exc)
        return report
    report["returncode"] = completed.returncode
    report["stdout_preview"] = completed.stdout.strip()[:1000]
    report["stderr_preview"] = completed.stderr.strip()[:1000]
    if completed.returncode != 0:
        stderr = completed.stderr.lower()
        report["status"] = "permission_denied" if "access is denied" in stderr else "nonzero_exit"
    else:
        report["status"] = "ok"
    return report


def permission_error_message(exc: BaseException) -> str:
    subject = "CODEX_BIN" if os.environ.get("CODEX_BIN") else "Codex executable"
    return f"permission_denied: cannot execute {subject} from subprocess: {exc}\n"


def sanitize_error(stderr: str, max_lines: int = 24, max_chars: int = 4000) -> str:
    """Keep actionable Codex CLI errors without embedding long HTML challenge pages."""
    lower_stderr = stderr.lower()
    if "access is denied" in lower_stderr or "permission denied" in lower_stderr:
        return "permission_denied: cannot execute Codex executable from subprocess.\n"
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
